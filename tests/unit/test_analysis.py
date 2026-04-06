"""
tests/unit/test_analysis.py
---------------------------
Unit tests for core logic components in src/analysis (AIActClassifier, DataActChecker)
All Mistral connections are mocked.
"""

import pytest
from unittest.mock import MagicMock, patch
import json

import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from haystack import Document
from src.analysis.schemas import AIActAuditReport, RiskCategory
from src.analysis.ai_act_classifier import AIActClassifier, LLMReasoningError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

FAKE_API_KEY = "sk-fake-mistral"

def _make_mock_chat_response(content_dict: dict) -> MagicMock:
    """Creates a mock Mistral chat completion response holding a JSON string."""
    response = MagicMock()
    message = MagicMock()
    message.content = json.dumps(content_dict)
    
    choice = MagicMock()
    choice.message = message
    
    response.choices = [choice]
    return response

# ---------------------------------------------------------------------------
# AIActClassifier Tests
# ---------------------------------------------------------------------------

class TestAIActClassifierInit:
    def test_init_missing_api_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(ValueError, match="MISTRAL_API_KEY is not set"):
            AIActClassifier(api_key=None)

    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_init_success(self, mock_mistral_cls):
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        assert classifier.model == "mistral-large-latest"
        assert classifier.temperature == 0.1
        mock_mistral_cls.assert_called_once_with(api_key=FAKE_API_KEY)


class TestAIActClassifierGuards:
    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_empty_system_description_raises_error(self, _):
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        with pytest.raises(ValueError, match="system_description cannot be empty"):
            classifier.analyze_system(system_description="", context_docs=[])

    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_whitespace_description_raises_error(self, _):
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        with pytest.raises(ValueError, match="system_description cannot be empty"):
            classifier.analyze_system(system_description="   \n", context_docs=[])


class TestAIActClassifierReasoning:
    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_analyze_system_api_failure_raises_llm_error(self, mock_mistral_cls):
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API timeout")
        mock_mistral_cls.return_value = mock_client
        
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        with pytest.raises(LLMReasoningError, match="Mistral API failure"):
            classifier.analyze_system(system_description="Testing", context_docs=[])

    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_analyze_system_invalid_json_schema_raises_llm_error(self, mock_mistral_cls):
        # Create a mock response that does NOT match the AIActAuditReport schema
        mock_response = _make_mock_chat_response({"wrong_key": "bad data"})
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_mistral_cls.return_value = mock_client
        
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        with pytest.raises(LLMReasoningError, match="Mismatched schema from LLM"):
            classifier.analyze_system(system_description="Testing", context_docs=[])

    @patch("src.analysis.ai_act_classifier.Mistral")
    def test_analyze_system_success(self, mock_mistral_cls):
        # Build a valid schema response matching AIActAuditReport
        valid_response_data = {
            "system_name": "Social scoring app",
            "risk_level": "Prohibited",
            "summary": "This system utilizes social scoring which is banned.",
            "primary_articles": [
                {"article": "Article 5", "title": "Prohibited Practices", "description": "Social scoring forbidden"}
            ],
            "findings": [
                {
                    "criterion": "Do not do social scoring", 
                    "is_compliant": False, 
                    "evidence": "System scores users",
                    "reasoning": "Violates explicit ban in Article 5",
                    "gap_analysis": "System must be entirely scrapped"
                }
            ]
        }
        
        mock_response = _make_mock_chat_response(valid_response_data)
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_mistral_cls.return_value = mock_client
        
        doc1 = Document(content="Article 5 details.", meta={"article_number": "Article 5", "parent_section": "Chapter II"})
        
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        report = classifier.analyze_system(system_description="Social scoring app", context_docs=[doc1])
        
        # Verify LLM was called with correct config
        mock_client.chat.complete.assert_called_once()
        kwargs = mock_client.chat.complete.call_args[1]
        assert kwargs["temperature"] == 0.1
        assert kwargs["model"] == "mistral-large-latest"
        assert kwargs["response_format"] == {"type": "json_object"}
        assert len(kwargs["messages"]) == 2
        
        # Verify output is correctly structured as our Pydantic model
        assert isinstance(report, AIActAuditReport)
        assert report.risk_level == RiskCategory.PROHIBITED
        assert "social scoring" in report.summary 
        assert len(report.primary_articles) == 1
        assert report.primary_articles[0].article == "Article 5"

    def test_format_context(self):
        classifier = AIActClassifier(api_key=FAKE_API_KEY)
        
        docs = [
            Document(content="Some AI law text", meta={"article_number": "Article 1", "parent_section": "Chapter I"}),
            Document(content="Another part", meta={}) # Missing metadata handles gracefully
        ]
        
        formatted = classifier._format_context(docs)
        assert "Some AI law text" in formatted
        assert "Article 1" in formatted
        assert "Chapter I" in formatted
        
        assert "Another part" in formatted
        assert "Unknown Article" in formatted


# ---------------------------------------------------------------------------
# DataActChecker Tests
# ---------------------------------------------------------------------------

from src.analysis.data_act_checker import DataActChecker

class TestDataActChecker:
    def test_init_missing_api_key_raises_value_error(self, monkeypatch):
        monkeypatch.delenv("MISTRAL_API_KEY", raising=False)
        with pytest.raises(ValueError, match="MISTRAL_API_KEY is not set"):
            DataActChecker(api_key=None)

    @patch("src.analysis.data_act_checker.DocumentRetrievalPipeline")
    @patch("src.analysis.data_act_checker.Mistral")
    def test_init_success(self, mock_mistral_cls, mock_pipeline_cls):
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline_cls())
        assert checker.model == "mistral-large-latest"
        mock_mistral_cls.assert_called_once_with(api_key=FAKE_API_KEY)

    @patch("src.analysis.data_act_checker.DocumentRetrievalPipeline")
    @patch("src.analysis.data_act_checker.Mistral")
    def test_empty_system_description_raises_error(self, mock_mistral_cls, mock_pipeline_cls):
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline_cls())
        with pytest.raises(ValueError, match="system_description cannot be empty"):
            checker.evaluate_data_obligations(system_description="")

    @patch("src.analysis.data_act_checker.Mistral")
    def test_api_failure_raises_llm_error(self, mock_mistral_cls):
        mock_client = MagicMock()
        mock_client.chat.complete.side_effect = Exception("API down")
        mock_mistral_cls.return_value = mock_client
        
        mock_pipeline = MagicMock()
        mock_pipeline.run_query.return_value = []
        
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline)
        
        with pytest.raises(LLMReasoningError, match="Mistral API failure"):
            checker.evaluate_data_obligations("Cloud IoT app")

    @patch("src.analysis.data_act_checker.Mistral")
    def test_malformed_json_raises_llm_error(self, mock_mistral_cls):
        # Mistral returning something that isn't JSON
        mock_response = MagicMock()
        mock_message = MagicMock()
        mock_message.content = "Internal Server Error"
        mock_choice = MagicMock()
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]
        
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_mistral_cls.return_value = mock_client
        
        mock_pipeline = MagicMock()
        mock_pipeline.run_query.return_value = []
        
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline)
        
        with pytest.raises(LLMReasoningError, match="Invalid JSON from Mistral"):
            checker.evaluate_data_obligations("Cloud IoT app")

    @patch("src.analysis.data_act_checker.Mistral")
    def test_missing_required_keys_raises_llm_error(self, mock_mistral_cls):
        # Valid JSON but missing required Schema keys
        mock_response = _make_mock_chat_response({"is_data_provider": True})
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_mistral_cls.return_value = mock_client
        
        mock_pipeline = MagicMock()
        mock_pipeline.run_query.return_value = []
        
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline)
        
        with pytest.raises(LLMReasoningError, match="Missing required Data Act keys"):
            checker.evaluate_data_obligations("Cloud IoT app")

    @patch("src.analysis.data_act_checker.Mistral")
    def test_evaluate_data_obligations_success(self, mock_mistral_cls):
        valid_response = {
            "is_data_provider": True,
            "data_sharing_compliant": False,
            "cloud_switching_compliant": True,
            "summary": "Must allow easy data sharing.",
            "missing_requirements": ["implement API for data out"]
        }
        
        mock_response = _make_mock_chat_response(valid_response)
        mock_client = MagicMock()
        mock_client.chat.complete.return_value = mock_response
        mock_mistral_cls.return_value = mock_client
        
        mock_pipeline = MagicMock()
        mock_pipeline.run_query.return_value = [Document(content="Data Act Article 6")]
        
        checker = DataActChecker(api_key=FAKE_API_KEY, pipeline=mock_pipeline)
        
        result = checker.evaluate_data_obligations("Smart IoT Device Hub")
        
        # Verify strict pipeline filtering was called
        mock_pipeline.run_query.assert_called_once_with(
            query="Smart IoT Device Hub",
            filters={"act_type": "DATA_ACT"},
            top_k=7
        )
        
        # Verify result output
        assert result["is_data_provider"] is True
        assert result["data_sharing_compliant"] is False
        assert "implement API for data out" in result["missing_requirements"]

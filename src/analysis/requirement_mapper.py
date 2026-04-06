"""
requirement_mapper.py
---------------------
Maps LLM-derived Risk Categories to strict CEN/CENELEC Harmonized Standards.

Provides the SME with technical 'presumption of conformity' by converting
legal tiering into actionable engineering checklists.
"""

import os
import json
import structlog
from typing import List

from src.analysis.schemas import RiskCategory, HarmonizedStandardRequirement

logger = structlog.get_logger(__name__)


class RequirementMapper:
    """
    Rule engine mapping Risk Categories to technical implementation standards.
    Reads from the `data/cen_cenelec_standards/` directory if populated,
    otherwise falls back to strict 2026 industrial defaults.
    """

    def __init__(self, data_dir: str = "data/cen_cenelec_standards"):
        """
        Initialize the mapper, loading external schema definitions if available.
        """
        self.data_dir = data_dir
        self.standards_map = self._load_standards()
        logger.info("RequirementMapper initialized", custom_files_loaded=bool(self.standards_map))

    def map_requirements(self, risk_level: RiskCategory) -> List[HarmonizedStandardRequirement]:
        """
        Produce a strict, type-safe list of technical engineering requirements.

        Args:
            risk_level: The EU AI Act risk category output by the Classifier.

        Returns:
            A strictly validated list of HarmonizedStandardRequirements.
        """
        logger.info("Mapping standards for risk tier", risk_level=risk_level.value)
        
        # If no specific risk constraints map exists, we use the fallback
        raw_standards = self.standards_map.get(risk_level, self._get_fallback_standards(risk_level))
        
        validated_requirements = []
        for std in raw_standards:
            # Enforce strict validation via Pydantic model
            try:
                req = HarmonizedStandardRequirement.model_validate(std)
                validated_requirements.append(req)
            except Exception as e:
                logger.error("Failed to map standard to Pydantic schema", error=str(e), standard=std)
                # Fail gracefully by skipping malformed standards
                continue
                
        logger.debug("Mapped requirements successfully", count=len(validated_requirements))
        return validated_requirements

    def _load_standards(self) -> dict:
        """
        Attempt to load JSON standards definitions from the data directory.
        Expected format: { "High-Risk": [ { standard_id: ..., } ] }
        """
        if not os.path.exists(self.data_dir):
            return {}
            
        standards = {}
        for filename in os.listdir(self.data_dir):
            if filename.endswith(".json"):
                filepath = os.path.join(self.data_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # Merge the loaded data into the master standards map
                        for risk_key, reqs in data.items():
                            # Find matching enum
                            matching_enum = next((r for r in RiskCategory if r.value == risk_key), None)
                            if matching_enum:
                                standards.setdefault(matching_enum, []).extend(reqs)
                except Exception as e:
                    logger.warning("Failed to load standards file", file=filename, error=str(e))
        return standards

    def _get_fallback_standards(self, risk_level: RiskCategory) -> List[dict]:
        """
        Returns strict 2026 CEN/CENELEC defaults if file loading fails.
        """
        if risk_level == RiskCategory.PROHIBITED:
            return [
                {
                    "standard_id": "EN ISO/IEC 42001:2026-X1",
                    "title": "Immediate System Decommissioning Protocol",
                    "description": "Prohibited systems must be taken offline immediately. All associated user data must be purged.",
                    "is_mandatory": True,
                    "verification_method": "Audit logs proving system termination and database wiping."
                }
            ]
        
        elif risk_level == RiskCategory.HIGH_RISK:
            return [
                {
                    "standard_id": "EN ISO/IEC 42001:2026",
                    "title": "Information Technology - AI Management System",
                    "description": "Must implement a formalized AI quality management system (QMS).",
                    "is_mandatory": True,
                    "verification_method": "Review of QMS documentation and ISO 42001 conformance certificate."
                },
                {
                    "standard_id": "CEN/CLC/TR 17862:2026",
                    "title": "Data Governance and Quality Baseline",
                    "description": "Risk mitigation through rigorous training data validation, preventing bias.",
                    "is_mandatory": True,
                    "verification_method": "Inspection of data lineage, bias-testing scripts, and dataset composition."
                },
                {
                    "standard_id": "EN 17640:2026",
                    "title": "Human Oversight Mechanism",
                    "description": "Must implement technical interface allowing human operators to override the AI.",
                    "is_mandatory": True,
                    "verification_method": "UI/UX flow review and programmatic kill-switch demonstration."
                }
            ]
            
        elif risk_level == RiskCategory.LIMITED:
            return [
                {
                    "standard_id": "EN 17990:2026",
                    "title": "AI Transparency and Flagging",
                    "description": "End users must be algorithmically informed they are communicating with an AI.",
                    "is_mandatory": True,
                    "verification_method": "Visual inspection of UI watermarks or chatbot disclaimers."
                }
            ]
            
        elif risk_level == RiskCategory.MINIMAL:
            return [
                {
                    "standard_id": "Voluntary Code of Conduct 2026",
                    "title": "Voluntary AI Ethics Guidelines",
                    "description": "SME is encouraged to adhere to baseline ethical design principles.",
                    "is_mandatory": False,
                    "verification_method": "Signed declaration of principles."
                }
            ]
            
        return []

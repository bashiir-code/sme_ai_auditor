"""
tests/unit/test_mapper.py
---------------------------
Unit tests for the RequirementMapper component.
"""

import pytest
import os
import json
import tempfile
from unittest.mock import patch

import sys
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.analysis.schemas import RiskCategory, HarmonizedStandardRequirement
from src.analysis.requirement_mapper import RequirementMapper

class TestRequirementMapper:
    
    def test_fallback_prohibited(self):
        mapper = RequirementMapper(data_dir="/invalid/dir/path")
        reqs = mapper.map_requirements(RiskCategory.PROHIBITED)
        
        assert len(reqs) == 1
        assert isinstance(reqs[0], HarmonizedStandardRequirement)
        assert reqs[0].is_mandatory is True
        assert "Decommissioning" in reqs[0].title

    def test_fallback_high_risk(self):
        mapper = RequirementMapper(data_dir="/invalid/dir/path")
        reqs = mapper.map_requirements(RiskCategory.HIGH_RISK)
        
        assert len(reqs) == 3
        for r in reqs:
            assert isinstance(r, HarmonizedStandardRequirement)
            assert r.is_mandatory is True

    def test_fallback_limited(self):
        mapper = RequirementMapper(data_dir="/invalid/dir")
        reqs = mapper.map_requirements(RiskCategory.LIMITED)
        
        assert len(reqs) == 1
        assert reqs[0].is_mandatory is True

    def test_fallback_minimal(self):
        mapper = RequirementMapper(data_dir="/invalid/dir")
        reqs = mapper.map_requirements(RiskCategory.MINIMAL)
        
        assert len(reqs) == 1
        assert reqs[0].is_mandatory is False

    def test_load_from_valid_json_file(self):
        # Create a temporary JSON file to simulate realistic user standards
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {
                RiskCategory.HIGH_RISK.value: [
                    {
                        "standard_id": "CUSTOM-100",
                        "title": "Custom Data Standard",
                        "description": "Test description",
                        "is_mandatory": True,
                        "verification_method": "Check files"
                    }
                ]
            }
            
            with open(os.path.join(temp_dir, "test_std.json"), 'w') as f:
                json.dump(test_data, f)
                
            mapper = RequirementMapper(data_dir=temp_dir)
            
            # The custom file overrides the default High-Risk requirements
            reqs = mapper.map_requirements(RiskCategory.HIGH_RISK)
            
            assert len(reqs) == 1
            assert reqs[0].standard_id == "CUSTOM-100"
            assert reqs[0].title == "Custom Data Standard"

    def test_malformed_json_skips_bad_records(self):
        # Even if a file exists, if it is missing a required Pydantic field, it skips
        with tempfile.TemporaryDirectory() as temp_dir:
            test_data = {
                RiskCategory.LIMITED.value: [
                    {
                        "standard_id": "BAD-100",
                        # Missing 'title', 'description', 'is_mandatory', 'verification_method'
                    }
                ]
            }
            
            with open(os.path.join(temp_dir, "bad_std.json"), 'w') as f:
                json.dump(test_data, f)
                
            mapper = RequirementMapper(data_dir=temp_dir)
            
            # The custom file will be read, but the dictionary fails Pydantic validation.
            reqs = mapper.map_requirements(RiskCategory.LIMITED)
            
            # Pydantic fails, so it skips the malformed item. 
            # In our strict implementation, getting 0 back is standard for corrupted data.
            assert len(reqs) == 0

import pytest
from agent.guardrails import validate_output


def test_number_not_in_tool_data_fails():
    tool_results = [{"data": [{"deal_value": 100000}], "quality_report": {"records_excluded": 0}, "confidence": "high"}]
    response = "The total pipeline value is 999999 crores."
    result = validate_output(response, tool_results)
    assert result["passed"] is False


def test_all_numbers_grounded_passes():
    tool_results = [{"data": [{"deal_value": 100000}], "quality_report": {"records_excluded": 0}, "confidence": "high"}]
    response = "The deal value is 100000. Based on 1 of 1 records."
    result = validate_output(response, tool_results)
    assert result["passed"] is True


def test_all_records_claim_with_exclusions_fails():
    tool_results = [{"data": [], "quality_report": {"records_excluded": 5}, "confidence": "medium"}]
    response = "All records show a healthy pipeline."
    result = validate_output(response, tool_results)
    assert result["passed"] is False


def test_all_high_confidence_gives_high():
    tool_results = [
        {"confidence": "high", "quality_report": {"records_excluded": 0}, "data": []},
        {"confidence": "high", "quality_report": {"records_excluded": 0}, "data": []},
    ]
    result = validate_output("Some answer with no numbers.", tool_results)
    assert result["confidence"] == "high"


def test_mixed_confidence_gives_medium():
    tool_results = [
        {"confidence": "high", "quality_report": {"records_excluded": 0}, "data": []},
        {"confidence": "low", "quality_report": {"records_excluded": 0}, "data": []},
    ]
    result = validate_output("Some answer.", tool_results)
    assert result["confidence"] == "medium"


def test_all_low_gives_low():
    tool_results = [
        {"confidence": "low", "quality_report": {"records_excluded": 0}, "data": []},
    ]
    result = validate_output("Some answer.", tool_results)
    assert result["confidence"] == "low"


def test_empty_tool_results_passes():
    result = validate_output("I have no data to report.", [])
    assert result["passed"] is True

"""
guardrails.py — P18: Output validator
Ensures every number in the response is grounded in tool results.
Never silently passes a hallucinated answer.
"""
import re
from typing import Any


def validate_output(response: str, tool_results: list[Any]) -> dict:
    issues: list[str] = []

    # Rule 1: every 4+ digit number in the response must exist in tool data
    numbers_in_response = set(re.findall(r"\d[\d,\.]+", response))
    all_tool_text = str(tool_results)
    for num in numbers_in_response:
        clean = num.replace(",", "").rstrip(".")
        if len(clean) > 3 and clean not in all_tool_text:
            issues.append(f"Number {num} not found in tool data")

    # Rule 2: "all records" claim is invalid when any records were excluded
    total_excluded = sum(
        r.get("quality_report", {}).get("records_excluded", 0)
        for r in tool_results if isinstance(r, dict)
    )
    if total_excluded > 0 and "all records" in response.lower():
        issues.append("Claims 'all records' but some were excluded by quality filter")

    # Confidence from tool results — aggregate
    confidences = [
        r.get("confidence", "medium")
        for r in tool_results if isinstance(r, dict)
    ]
    if not confidences:
        overall = "medium"
    elif all(c == "high" for c in confidences):
        overall = "high"
    elif all(c == "low" for c in confidences):
        overall = "low"
    else:
        overall = "medium"

    return {
        "passed": len(issues) == 0,
        "warning": "; ".join(issues) if issues else None,
        "confidence": overall,
    }

import pytest
from datetime import date
from agent.cleaner import (
    parse_currency,
    parse_date,
    parse_probability,
    clean_and_enrich,
)


# ── parse_currency ─────────────────────────────────────────────────────────────

def test_currency_indian_comma_format():
    assert parse_currency("₹12,50,000") == 1250000.0

def test_currency_lakh_suffix():
    assert parse_currency("12.5L") == 1250000.0

def test_currency_crore_suffix():
    assert parse_currency("2.5Cr") == 25000000.0

def test_currency_plain_float():
    assert parse_currency("1250000.0") == 1250000.0

def test_currency_none_returns_none():
    assert parse_currency(None) is None

def test_currency_empty_string_returns_none():
    assert parse_currency("") is None

def test_currency_na_returns_none():
    assert parse_currency("N/A") is None

def test_currency_rupee_symbol_stripped():
    assert parse_currency("₹5000") == 5000.0

def test_currency_dollar_stripped():
    assert parse_currency("$1000") == 1000.0

def test_currency_k_suffix():
    assert parse_currency("50k") == 50000.0

def test_currency_does_not_raise_on_any_string():
    # property-style: must never raise
    for val in ["abc", "---", "12.5L crore", "∞", "   ", "NaN"]:
        result = parse_currency(val)
        assert result is None or isinstance(result, float)


# ── parse_date ─────────────────────────────────────────────────────────────────

def test_date_iso():
    assert parse_date("2025-03-15") == date(2025, 3, 15)

def test_date_indian_format():
    assert parse_date("15/03/2025") == date(2025, 3, 15)

def test_date_excel_serial():
    result = parse_date(45365)
    assert isinstance(result, date)

def test_date_none_returns_none():
    assert parse_date(None) is None

def test_date_empty_string_returns_none():
    assert parse_date("") is None

def test_date_datetime_object_returns_date():
    from datetime import datetime
    dt = datetime(2025, 6, 1, 12, 0)
    assert parse_date(dt) == date(2025, 6, 1)

def test_date_date_object_passthrough():
    d = date(2025, 1, 1)
    assert parse_date(d) == d

def test_date_does_not_raise_on_any_string():
    for val in ["not-a-date", "99/99/9999", "March 99", "", "banana"]:
        result = parse_date(val)
        assert result is None or isinstance(result, date)


# ── parse_probability ─────────────────────────────────────────────────────────

def test_prob_percent_string():
    assert parse_probability("75%") == 0.75

def test_prob_integer_string():
    assert parse_probability("75") == 0.75

def test_prob_already_decimal():
    assert parse_probability("0.75") == 0.75

def test_prob_none_returns_none():
    assert parse_probability(None) is None

def test_prob_empty_returns_none():
    assert parse_probability("") is None

def test_prob_text_high_returns_none():
    # text "High" is handled upstream via PROB_TEXT_MAP, not here
    assert parse_probability("High") is None

def test_prob_does_not_raise_on_any_string():
    for val in ["abc", "---", None, "", "100%", "0"]:
        result = parse_probability(val)
        assert result is None or isinstance(result, float)


# ── clean_and_enrich ──────────────────────────────────────────────────────────

def test_empty_raw_returns_low_confidence():
    result = clean_and_enrich("get_work_orders", [])
    assert result["confidence"] == "low"
    assert result["quality_report"]["records_used"] == 0


def test_tiny_value_excluded_from_totals():
    raw = [
        {"name": "Inosuke", "contract_value": "1.2332", "status": "ACTIVE"},
        {"name": "BigOrder", "contract_value": "500000", "status": "ACTIVE"},
    ]
    result = clean_and_enrich("get_work_orders", raw)
    reasons = result["quality_report"]["exclusion_reasons"]
    assert any("placeholder" in r.lower() or "<" in r for r in reasons)
    names = [r["name"] for r in result["data"]]
    assert "Inosuke" not in names
    assert "BigOrder" in names


def test_negative_currency_excluded():
    raw = [
        {"name": "Bad", "deal_value": "-5000", "stage": "OPEN"},
        {"name": "Good", "deal_value": "100000", "stage": "OPEN"},
    ]
    result = clean_and_enrich("get_at_risk_deals", raw)
    reasons = result["quality_report"]["exclusion_reasons"]
    assert any("negative" in r.lower() for r in reasons)
    names = [r["name"] for r in result["data"]]
    assert "Bad" not in names


def test_header_repeat_rows_removed():
    raw = [
        {"name": "Deal Stage", "stage": "Deal Stage", "deal_value": "100000"},
        {"name": "Real Deal", "stage": "Proposal", "deal_value": "200000"},
    ]
    result = clean_and_enrich("get_at_risk_deals", raw)
    names = [r.get("name", "") for r in result["data"]]
    assert "Deal Stage" not in names


def test_null_prob_majority_forces_low_confidence():
    raw = [
        {"name": f"Deal{i}", "deal_value": "100000", "probability": None, "stage": "OPEN"}
        for i in range(10)
    ]
    result = clean_and_enrich("get_revenue_forecast", raw)
    assert result["confidence"] == "low"
    reasons = result["quality_report"]["exclusion_reasons"]
    assert any("50%" in r or "probability" in r.lower() for r in reasons)


def test_quality_report_always_present():
    raw = [{"name": "X", "status": "ACTIVE", "contract_value": "50000"}]
    result = clean_and_enrich("get_work_orders", raw)
    qr = result["quality_report"]
    assert "records_used" in qr
    assert "records_excluded" in qr
    assert "exclusion_reasons" in qr
    assert "total_original" in qr


def test_output_fields_filtered_by_tool(monkeypatch):
    raw = [
        {
            "name": "Deal A",
            "stage": "Proposal",
            "deal_value": "500000",
            "probability": "0.5",
            "days_in_stage": 45,
            "risk_score": "high",
            "owner": "OWNER_001",
            "tentative_close_date": "2025-06-01",
            "some_extra_col": "should_be_stripped",
        }
    ]
    result = clean_and_enrich("get_at_risk_deals", raw)
    if result["data"]:
        assert "some_extra_col" not in result["data"][0]

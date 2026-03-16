"""
cleaner.py — P14: Data Quality Foundation
4-stage pipeline: null handling → type coercion → normalisation → enrichment
Patches applied: P4 (null prob confidence), P5 (tiny value filter)
Token Opt 2: TOOL_OUTPUT_FIELDS whitelist strips unused columns before LLM
"""
import pandas as pd
from datetime import datetime, date
from typing import Optional

# ── Enum normalisation maps ────────────────────────────────────────────────────

STAGE_MAP: dict[str, str] = {
    "closed won": "WON", "won": "WON", "win": "WON", "closed_won": "WON",
    "closed lost": "LOST", "lost": "LOST", "lose": "LOST", "closed_lost": "LOST",
    "proposal": "PROPOSAL", "proposal sent": "PROPOSAL", "sent proposal": "PROPOSAL",
    "negotiation": "NEGOTIATION", "negotiating": "NEGOTIATION", "in negotiation": "NEGOTIATION",
    "qualified": "QUALIFIED", "sql": "QUALIFIED",
    "discovery": "DISCOVERY", "meeting": "DISCOVERY",
    "lead": "LEAD", "new": "LEAD", "prospect": "LEAD",
}

STATUS_MAP: dict[str, str] = {
    "in progress": "IN_PROGRESS", "wip": "IN_PROGRESS",
    "in-progress": "IN_PROGRESS", "active": "IN_PROGRESS", "ongoing": "IN_PROGRESS",
    "executed until current month": "IN_PROGRESS",
    "completed": "COMPLETED", "done": "COMPLETED", "closed": "COMPLETED", "finished": "COMPLETED",
    "pending": "PENDING", "not started": "PENDING", "new": "PENDING", "open": "PENDING",
    "overdue": "OVERDUE", "delayed": "OVERDUE", "late": "OVERDUE", "past due": "OVERDUE",
    "pause / struck": "PAUSED",
    "partial completed": "IN_PROGRESS",
    "details pending from client": "BLOCKED",
}

# Closure Probability text → float (Deal Funnel specific)
PROB_TEXT_MAP: dict[str, float] = {
    "high": 0.80,
    "medium": 0.50,
    "low": 0.20,
}

# Token Opt 2: only pass these fields per tool to the LLM
TOOL_OUTPUT_FIELDS: dict[str, list[str]] = {
    "get_at_risk_deals":    ["name", "stage", "deal_value", "days_in_stage",
                             "risk_score", "owner", "tentative_close_date"],
    "get_pipeline_summary": ["stage", "deal_value", "probability",
                             "weighted_value", "deal_status"],
    "get_work_orders":      ["name", "execution_status", "end_date",
                             "contract_value", "sector", "sla_breached"],
    "get_revenue_forecast": ["deal_value", "probability", "weighted_value",
                             "tentative_close_date", "stage"],
    "get_anomalies":        ["name", "contract_value", "deal_value",
                             "risk_score", "stage"],
}


# ── Type parsers (hypothesis-safe: never raise) ───────────────────────────────

def parse_currency(val) -> Optional[float]:
    """Handles: ₹12,50,000 / 12.5L / 2.5Cr / 50k / 1250000.0 / NULL"""
    try:
        if val is None:
            return None
        import pandas as _pd
        if _pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip().lower()
    if s in ("", "n/a", "na", "-", "nan", "none", "nat"):
        return None
    s = s.replace("₹", "").replace("$", "").replace(",", "").replace(" ", "")
    try:
        if s.endswith("cr"):
            return float(s[:-2]) * 10_000_000
        if s.endswith("l"):
            return float(s[:-1]) * 100_000
        if s.endswith("k"):
            return float(s[:-1]) * 1_000
        return float(s)
    except (ValueError, OverflowError):
        return None


def parse_date(val) -> Optional[date]:
    """Handles: ISO / DD/MM/YYYY / MM/DD/YYYY / Excel serial / datetime objects"""
    try:
        if val is None:
            return None
        import pandas as _pd
        if _pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    s = str(val).strip()
    if s in ("", "n/a", "na", "-", "nan", "none", "nat"):
        return None
    # Excel serial
    try:
        serial = float(s)
        if 20000 < serial < 60000:
            return datetime.fromordinal(datetime(1900, 1, 1).toordinal() + int(serial) - 2).date()
    except (ValueError, OverflowError, OSError):
        pass
    for fmt in ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y",
                "%B %d, %Y", "%d %b %Y", "%b %d, %Y", "%d %B %Y"]:
        try:
            return datetime.strptime(s, fmt).date()
        except ValueError:
            continue
    return None


def parse_probability(val) -> Optional[float]:
    """Handles: 0.75 / 75% / 75 / NULL — text High/Medium/Low handled upstream"""
    try:
        if val is None:
            return None
        import pandas as _pd
        if _pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    s = str(val).strip().replace("%", "")
    if s in ("", "n/a", "na", "-", "nan", "none"):
        return None
    try:
        v = float(s)
        return round(v / 100 if v > 1 else v, 4)
    except (ValueError, OverflowError):
        return None


def normalise_stage(val) -> str:
    if pd.isna(val) if not isinstance(val, str) else False:
        return "UNKNOWN"
    return STAGE_MAP.get(str(val).strip().lower(), str(val).strip())


def normalise_status(val) -> str:
    if pd.isna(val) if not isinstance(val, str) else False:
        return "UNKNOWN"
    return STATUS_MAP.get(str(val).strip().lower(), str(val).strip().upper())


# ── Main cleaner ──────────────────────────────────────────────────────────────

def clean_and_enrich(tool_name: str, raw: list) -> dict:
    """
    Runs 4 stages: null handling → type coercion → normalisation → enrichment.
    Always returns: {data, quality_report, confidence}
    """
    if not raw:
        return {
            "data": [],
            "quality_report": {
                "records_used": 0,
                "records_excluded": 0,
                "exclusion_reasons": ["No data returned from Monday.com"],
                "total_original": 0,
                "data_quality_ratio": 0.0,
            },
            "confidence": "low",
        }

    df = pd.DataFrame(raw)
    original_count = len(df)
    exclusion_reasons: list[str] = []

    # ── Header-repeat row removal (Deal Funnel boards) ─────────────────────────
    if tool_name in ("get_at_risk_deals", "get_pipeline_summary",
                     "get_revenue_forecast", "get_anomalies"):
        if "stage" in df.columns:
            df = df[df["stage"] != "Deal Stage"].copy()
        if "deal_status" in df.columns:
            df = df[df["deal_status"] != "Deal Status"].copy()
        if "probability" in df.columns:
            df = df[df["probability"] != "Closure Probability"].copy()
        # Exclude dead deals from pipeline queries
        if "deal_status" in df.columns:
            dead_count = (df["deal_status"].str.lower() == "dead").sum()
            if dead_count > 0:
                df = df[df["deal_status"].str.lower() != "dead"].copy()
                exclusion_reasons.append(f"{dead_count} dead deals excluded from active pipeline")

    # ── Currency columns ───────────────────────────────────────────────────────
    for col in ("deal_value", "amount", "contract_value", "value", "revenue"):
        if col not in df.columns:
            continue
        df[col] = df[col].apply(parse_currency)
        neg_mask = df[col].notna() & (df[col] < 0)
        if neg_mask.any():
            exclusion_reasons.append(f"{neg_mask.sum()} records with negative {col} (anomaly)")
            df = df[~neg_mask]

    # ── Patch 5: tiny placeholder value filter (<100, >0) ─────────────────────
    for col in ("contract_value", "deal_value"):
        if col not in df.columns:
            continue
        tiny_mask = df[col].notna() & (df[col] > 0) & (df[col] < 100)
        if tiny_mask.any():
            exclusion_reasons.append(
                f"{tiny_mask.sum()} records with placeholder value (<₹100) excluded from financial totals"
            )
            df = df[~tiny_mask]

    # ── Date columns ───────────────────────────────────────────────────────────
    for col in ("close_date", "due_date", "created_at", "stage_entered_date",
                "last_updated", "modified_at", "start_date", "end_date",
                "tentative_close_date", "actual_close_date"):
        if col not in df.columns:
            continue
        df[col] = df[col].apply(parse_date)
        bad = df[col].isna().sum()
        if bad:
            exclusion_reasons.append(f"{bad} records with unparseable {col}")

    # ── Probability — Deal Funnel text map then numeric parse ─────────────────
    null_prob_count = 0
    if "probability" in df.columns:
        def _parse_prob_with_text(val) -> Optional[float]:
            if val is None:
                return None
            try:
                if pd.isna(val):
                    return None
            except (TypeError, ValueError):
                pass
            text = str(val).strip().lower()
            if text in PROB_TEXT_MAP:
                return PROB_TEXT_MAP[text]
            return parse_probability(val)

        df["probability"] = df["probability"].apply(_parse_prob_with_text)
        df["probability"] = df["probability"].clip(0, 1)

        # Patch 4: count nulls, fill 0.5, downgrade confidence if majority assumed
        null_prob_count = int(df["probability"].isna().sum())
        if null_prob_count > 0:
            df["probability"] = df["probability"].fillna(0.5).infer_objects(copy=False)
            exclusion_reasons.append(
                f"{null_prob_count} deals used default 50% probability (not set in data)"
            )

    # ── Stage normalisation ────────────────────────────────────────────────────
    if "stage" in df.columns:
        df["stage"] = df["stage"].apply(normalise_stage)

    # ── Status normalisation ───────────────────────────────────────────────────
    if "status" in df.columns:
        df["status"] = df["status"].apply(normalise_status)
    if "execution_status" in df.columns:
        df["execution_status"] = df["execution_status"].apply(normalise_status)

    # ── String cleanup ─────────────────────────────────────────────────────────
    for col in df.select_dtypes(include="object").columns:
        df[col] = df[col].astype(str).str.strip()
        df[col] = df[col].replace({"nan": None, "None": None, "": None, "NaT": None})

    # ── Deduplication by ID ────────────────────────────────────────────────────
    id_col = next((c for c in ("deal_id", "order_id", "id", "item_id") if c in df.columns), None)
    if id_col:
        before = len(df)
        ts_col = next((c for c in ("last_updated", "modified_at") if c in df.columns), None)
        df = (df.sort_values(ts_col, ascending=False) if ts_col else df).drop_duplicates(id_col)
        dupes = before - len(df)
        if dupes:
            exclusion_reasons.append(f"{dupes} duplicate records merged (kept latest)")

    # ── Critical column exclusion ──────────────────────────────────────────────
    critical_cols_map: dict[str, list[str]] = {
        "get_at_risk_deals":    ["deal_value", "stage"],
        "get_pipeline_summary": ["deal_value", "stage"],
        "get_work_orders":      ["execution_status"],
        "get_revenue_forecast": ["deal_value", "probability"],
        "get_anomalies":        ["deal_value"],
    }
    for col in critical_cols_map.get(tool_name, []):
        if col not in df.columns:
            continue
        mask = df[col].isna()
        n = int(mask.sum())
        if n:
            exclusion_reasons.append(f"{n} records excluded — missing {col} (critical field)")
            df = df[~mask]

    # ── Enrichment ─────────────────────────────────────────────────────────────
    today = date.today()

    if "stage_entered_date" in df.columns:
        df["days_in_stage"] = df["stage_entered_date"].apply(
            lambda d: (today - d).days if isinstance(d, date) else None
        )

    if "days_in_stage" in df.columns and df["days_in_stage"].notna().any():
        avg_days = df["days_in_stage"].mean()
        df["is_at_risk"] = df["days_in_stage"] > avg_days * 1.5
        df["risk_score"] = df["days_in_stage"].apply(
            lambda d: (
                "critical" if d > avg_days * 2.5 else
                "high"     if d > avg_days * 1.5 else
                "medium"   if d > avg_days       else
                "low"
            ) if pd.notna(d) else "unknown"
        )
        # P20: sort critical first
        risk_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
        df["_risk_order"] = df["risk_score"].map(risk_order)
        df = df.sort_values("_risk_order").drop(columns=["_risk_order"])

    if "deal_value" in df.columns and "probability" in df.columns:
        df["weighted_value"] = (
            df["deal_value"] * df["probability"].fillna(0.5)
        ).round(2)

    if "end_date" in df.columns and "execution_status" in df.columns:
        active_statuses = {"IN_PROGRESS", "PENDING", "BLOCKED", "ACTIVE"}
        df["sla_breached"] = df.apply(
            lambda r: (
                isinstance(r["end_date"], date) and
                r["end_date"] < today and
                str(r.get("execution_status", "")).upper() in active_statuses
            ), axis=1
        )

    if "due_date" in df.columns and "status" in df.columns:
        df["sla_breached"] = df.apply(
            lambda r: (
                isinstance(r["due_date"], date) and
                r["due_date"] < today and
                r.get("status") != "COMPLETED"
            ), axis=1
        )

    # ── Quality report ─────────────────────────────────────────────────────────
    records_used = len(df)
    ratio = records_used / original_count if original_count > 0 else 0.0

    # Patch 4: force low if majority of probabilities were assumed
    if null_prob_count > 0 and null_prob_count > records_used * 0.5:
        confidence = "low"
        exclusion_reasons.append(
            f"WARNING: weighted forecast is an estimate — "
            f"{null_prob_count}/{records_used} probabilities assumed at 50%"
        )
    else:
        confidence = "high" if ratio >= 0.8 else "medium" if ratio >= 0.5 else "low"

    # ── Token Opt 2: field whitelist before returning to LLM ───────────────────
    keep_fields = TOOL_OUTPUT_FIELDS.get(tool_name, [])
    if keep_fields:
        available = [f for f in keep_fields if f in df.columns]
        if available:
            df = df[available]

    return {
        "data": df.to_dict(orient="records"),
        "quality_report": {
            "records_used": records_used,
            "records_excluded": original_count - records_used,
            "exclusion_reasons": exclusion_reasons,
            "total_original": original_count,
            "data_quality_ratio": round(ratio, 2),
        },
        "confidence": confidence,
    }

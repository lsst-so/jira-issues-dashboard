"""Priority-age diagnostic analytics for open tickets.

Computes correlations between priority severity and ticket age/inactivity,
with optional breakdown by hierarchy groups. These are descriptive triage
aids, not severity or performance metrics.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from jira_app.core.config import DEFAULT_TREND_PRIORITIES, PRIORITY_MAPPING, normalize_priority_name

PRIORITY_ORDER: tuple[str, ...] = tuple(DEFAULT_TREND_PRIORITIES) + ("Undefined",)


@dataclass
class CorrelationResult:
    """Result of a Spearman correlation calculation."""

    rho: float | None
    p_value: float | None
    n: int
    significant: bool | None

    @property
    def direction(self) -> str | None:
        if self.rho is None:
            return None
        if self.rho > 0:
            return "positive"
        if self.rho < 0:
            return "negative"
        return "none"


def _compute_spearman(
    priority_values: pd.Series,
    metric_values: pd.Series,
    alpha: float = 0.05,
) -> CorrelationResult:
    """Compute Spearman correlation between priority severity and a metric.

    Parameters
    ----------
    priority_values : pd.Series
        Numeric priority severity values (higher = more severe).
    metric_values : pd.Series
        Numeric metric values (e.g., days_open).
    alpha : float
        Significance level for determining if correlation is significant.

    Returns
    -------
    CorrelationResult
        Correlation result with rho, p-value, n, and significance flag.
    """
    valid_mask = priority_values.notna() & metric_values.notna()
    pv = priority_values[valid_mask]
    mv = metric_values[valid_mask]

    n = len(pv)
    if n < 3:
        return CorrelationResult(rho=None, p_value=None, n=n, significant=None)

    # Check for constant arrays (correlation undefined)
    if pv.nunique() < 2 or mv.nunique() < 2:
        return CorrelationResult(rho=None, p_value=None, n=n, significant=None)

    try:
        result = stats.spearmanr(pv, mv)
        rho = float(result.correlation) if not np.isnan(result.correlation) else None
        p_value = float(result.pvalue) if not np.isnan(result.pvalue) else None
        significant = p_value < alpha if p_value is not None else None
        return CorrelationResult(rho=rho, p_value=p_value, n=n, significant=significant)
    except Exception:
        return CorrelationResult(rho=None, p_value=None, n=n, significant=None)


def _normalize_priority_name(p: str | None) -> str:
    """Normalize priority string to canonical form using PRIORITY_MAPPING keys."""
    if p is None or pd.isna(p):
        return "Undefined"
    p_str = str(p).strip()
    if not p_str:
        return "Undefined"
    for canonical in PRIORITY_MAPPING:
        if p_str.lower().startswith(canonical.lower()):
            return canonical
    return "Undefined"


def _add_priority_severity(work: pd.DataFrame) -> pd.DataFrame:
    """Add __priority_severity column using priority_value or fallback to PRIORITY_MAPPING."""
    work["__priority_normalized"] = work["priority"].apply(_normalize_priority_name)
    fallback = work["__priority_normalized"].map(lambda p: PRIORITY_MAPPING.get(p, 0))

    if "priority_value" in work.columns:
        severity = pd.to_numeric(work["priority_value"], errors="coerce")
        invalid_mask = severity.isna() | (severity < 0)
        work["__priority_severity"] = severity.where(~invalid_mask, fallback).astype(float)
    else:
        work["__priority_severity"] = fallback.astype(float)

    return work


def filter_open_tickets(df: pd.DataFrame, terminal_statuses: frozenset[str] | None = None) -> pd.DataFrame:
    """Filter to open tickets only.

    Parameters
    ----------
    df : pd.DataFrame
        Issue dataframe.
    terminal_statuses : frozenset[str], optional
        Set of terminal status names. Defaults to common terminal statuses.

    Returns
    -------
    pd.DataFrame
        Filtered dataframe containing only open tickets.
    """
    if df.empty:
        return df

    if terminal_statuses is None:
        terminal_statuses = frozenset({"Done", "Cancelled", "Duplicate", "Transferred"})

    if "status" not in df.columns:
        return df

    status_lower = df["status"].fillna("").astype(str).str.lower()
    terminal_lower = {s.lower() for s in terminal_statuses}
    open_mask = ~status_lower.isin(terminal_lower)
    return df[open_mask].copy()


def priority_age_distribution(
    df: pd.DataFrame,
    metric_col: str = "days_open",
    exclude_undefined_from_corr: bool = True,
) -> tuple[pd.DataFrame, CorrelationResult]:
    """Compute priority vs age distribution data and correlation.

    Uses existing priority_value column from normalization, falling back to
    PRIORITY_MAPPING if needed.

    Parameters
    ----------
    df : pd.DataFrame
        Open tickets dataframe with 'priority' and metric column.
    metric_col : str
        Column name for the age/inactivity metric.
    exclude_undefined_from_corr : bool
        Whether to exclude 'Undefined' priority from correlation calculation.

    Returns
    -------
    tuple[pd.DataFrame, CorrelationResult]
        - DataFrame with columns: priority, metric value, priority_value, count per priority
        - Spearman correlation result
    """
    if df.empty or "priority" not in df.columns or metric_col not in df.columns:
        return pd.DataFrame(), CorrelationResult(rho=None, p_value=None, n=0, significant=None)

    work = df.copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = work.dropna(subset=[metric_col])

    if work.empty:
        return pd.DataFrame(), CorrelationResult(rho=None, p_value=None, n=0, significant=None)

    work = _add_priority_severity(work)

    counts = work.groupby("__priority_normalized").size().reset_index(name="count")

    dist_df = work[["__priority_normalized", metric_col, "__priority_severity"]].copy()
    dist_df = dist_df.rename(
        columns={"__priority_normalized": "priority", "__priority_severity": "priority_value"}
    )

    corr_df = work.copy()
    if exclude_undefined_from_corr:
        corr_df = corr_df[corr_df["__priority_normalized"] != "Undefined"]

    corr_result = _compute_spearman(corr_df["__priority_severity"], corr_df[metric_col])

    dist_df = dist_df.merge(
        counts.rename(columns={"__priority_normalized": "priority"}), on="priority", how="left"
    )

    return dist_df, corr_result


def priority_age_by_group(
    df: pd.DataFrame,
    group_col: str,
    metric_col: str = "days_open",
    min_group_size: int = 5,
    exclude_undefined_from_corr: bool = True,
) -> pd.DataFrame:
    """Compute priority-age correlations by hierarchy group.

    Parameters
    ----------
    df : pd.DataFrame
        Open tickets dataframe.
    group_col : str
        Column name for hierarchy grouping (e.g., 'obs_system').
    metric_col : str
        Column name for the age/inactivity metric.
    min_group_size : int
        Minimum tickets per group to include in results.
    exclude_undefined_from_corr : bool
        Whether to exclude 'Undefined' priority from correlation.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: group, rho, p_value, n, significant, direction.
        Includes an 'All groups' pooled row.
    """
    if (
        df.empty
        or group_col not in df.columns
        or "priority" not in df.columns
        or metric_col not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = _add_priority_severity(work)
    work = work.dropna(subset=[metric_col, "__priority_severity"])

    corr_work = work[work["__priority_normalized"] != "Undefined"] if exclude_undefined_from_corr else work

    if corr_work.empty:
        return pd.DataFrame()

    results = []

    pooled_corr = _compute_spearman(corr_work["__priority_severity"], corr_work[metric_col])
    results.append(
        {
            "group": "All groups",
            "rho": pooled_corr.rho,
            "p_value": pooled_corr.p_value,
            "n": pooled_corr.n,
            "significant": pooled_corr.significant,
            "direction": pooled_corr.direction,
            "is_pooled": True,
        }
    )

    corr_work = corr_work.copy()
    corr_work["__group"] = corr_work[group_col].fillna("(Unspecified)").astype(str)
    for group_name, group_df in corr_work.groupby("__group"):
        if len(group_df) < min_group_size:
            continue
        corr = _compute_spearman(group_df["__priority_severity"], group_df[metric_col])
        results.append(
            {
                "group": group_name,
                "rho": corr.rho,
                "p_value": corr.p_value,
                "n": corr.n,
                "significant": corr.significant,
                "direction": corr.direction,
                "is_pooled": False,
            }
        )

    return pd.DataFrame(results)


def median_age_heatmap(
    df: pd.DataFrame,
    group_col: str,
    metric_col: str = "days_open",
    top_n_groups: int = 15,
    attention_score_threshold: float | None = None,
) -> pd.DataFrame:
    """Compute median age by hierarchy group and priority for heatmap.

    Parameters
    ----------
    df : pd.DataFrame
        Open tickets dataframe.
    group_col : str
        Column name for hierarchy grouping.
    metric_col : str
        Column name for the age/inactivity metric.
    top_n_groups : int
        Maximum number of groups to include (by ticket count).
    attention_score_threshold : float, optional
        If provided, tickets with attention score (priority × days) exceeding
        this threshold are flagged for attention.

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: group, priority, median, count, max_days, tickets_info,
        attention_count (tickets exceeding score threshold).
    """
    if (
        df.empty
        or group_col not in df.columns
        or "priority" not in df.columns
        or metric_col not in df.columns
    ):
        return pd.DataFrame()

    work = df.copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = work.dropna(subset=[metric_col])

    if work.empty:
        return pd.DataFrame()

    work["__priority_normalized"] = work["priority"].apply(_normalize_priority_name)
    work["__group"] = work[group_col].fillna("(Unspecified)").astype(str)

    # Add priority severity for attention score calculation
    work = _add_priority_severity(work)

    group_counts = work.groupby("__group").size().sort_values(ascending=False)
    top_groups = group_counts.head(top_n_groups).index.tolist()
    work = work[work["__group"].isin(top_groups)]

    if work.empty:
        return pd.DataFrame()

    def _agg_with_tickets(group_df: pd.DataFrame) -> pd.Series:
        metric_values = group_df[metric_col]
        severity_values = group_df["__priority_severity"]
        keys = group_df["key"].astype(str) if "key" in group_df.columns else pd.Series([], dtype=str)
        summaries = (
            group_df["summary"].astype(str) if "summary" in group_df.columns else pd.Series([], dtype=str)
        )

        # Compute attention scores for each ticket
        ticket_scores = severity_values * metric_values

        sorted_idx = metric_values.sort_values(ascending=False).index
        top_tickets = []
        for idx in sorted_idx[:5]:
            key = keys.get(idx, "")
            summary = summaries.get(idx, "")
            days = metric_values.get(idx, 0)
            score = ticket_scores.get(idx, 0)
            if key:
                summary_short = summary[:40] + "..." if len(summary) > 40 else summary
                # Add ⚠️ prefix if ticket exceeds attention threshold
                if attention_score_threshold is not None and score > attention_score_threshold:
                    top_tickets.append(f"⚠️ {key}: {summary_short} ({days:.0f}d)")
                else:
                    top_tickets.append(f"• {key}: {summary_short} ({days:.0f}d)")

        attention_count = 0
        if attention_score_threshold is not None:
            attention_count = int((ticket_scores > attention_score_threshold).sum())

        return pd.Series(
            {
                "median": metric_values.median(),
                "count": len(group_df),
                "max_days": metric_values.max(),
                "tickets_info": "\n".join(top_tickets) if top_tickets else "",
                "attention_count": attention_count,
            }
        )

    agg = work.groupby(["__group", "__priority_normalized"]).apply(_agg_with_tickets, include_groups=False)
    agg = agg.reset_index()
    agg = agg.rename(columns={"__group": "group", "__priority_normalized": "priority"})

    return agg


def compute_attention_threshold(
    df: pd.DataFrame,
    percentile: float = 90.0,
    metric_col: str = "days_open",
) -> float:
    """Compute attention score threshold based on percentile.

    Parameters
    ----------
    df : pd.DataFrame
        Open tickets dataframe with priority and metric columns.
    percentile : float
        Percentile to use for threshold (e.g., 90 means top 10% flagged).
    metric_col : str
        Column name for the age/inactivity metric.

    Returns
    -------
    float
        Score threshold at the given percentile. Returns 0 if unable to compute.
    """
    if df.empty or "priority" not in df.columns or metric_col not in df.columns:
        return 0.0

    work = df.copy()
    work[metric_col] = pd.to_numeric(work[metric_col], errors="coerce")
    work = work.dropna(subset=[metric_col])

    if work.empty:
        return 0.0

    work = _add_priority_severity(work)
    scores = work["__priority_severity"] * work[metric_col]
    scores = scores.dropna()

    if scores.empty:
        return 0.0

    return float(np.percentile(scores, percentile))


def has_hierarchy_data(df: pd.DataFrame, hierarchy_col: str) -> bool:
    """Check if hierarchy column has meaningful data.

    Parameters
    ----------
    df : pd.DataFrame
        Issue dataframe.
    hierarchy_col : str
        Column name for hierarchy field.

    Returns
    -------
    bool
        True if column exists and has non-empty values.
    """
    if df.empty or hierarchy_col not in df.columns:
        return False

    non_empty = df[hierarchy_col].dropna().astype(str).str.strip()
    non_empty = non_empty[non_empty != ""]
    return len(non_empty) > 0


def compute_attention_scores(
    df: pd.DataFrame,
    top_n: int = 20,
    min_score: float | None = None,
) -> pd.DataFrame:
    """Compute attention scores for tickets based on priority × age.

    Attention score = priority_value × days_open (or days_since_update).
    Higher scores indicate tickets that may need attention.

    Parameters
    ----------
    df : pd.DataFrame
        Open tickets dataframe with priority, days_open, days_since_update columns.
    top_n : int
        Number of top tickets to return for each metric.
    min_score : float, optional
        If provided, only include tickets where at least one attention score
        exceeds this threshold (aligns with heatmap attention flags).

    Returns
    -------
    pd.DataFrame
        DataFrame with columns: key, summary, priority, priority_value,
        days_open, days_since_update, attention_score_age, attention_score_inactivity,
        obs_system (if available). Sorted by attention_score_age descending.
    """
    if df.empty:
        return pd.DataFrame()

    required_cols = ["priority", "days_open", "days_since_update"]
    if not all(col in df.columns for col in required_cols):
        return pd.DataFrame()

    work = df.copy()

    # Add priority severity using existing logic
    work = _add_priority_severity(work)

    # Compute attention scores
    days_open = pd.to_numeric(work["days_open"], errors="coerce").fillna(0)
    days_since_update = pd.to_numeric(work["days_since_update"], errors="coerce").fillna(0)
    severity = work["__priority_severity"].fillna(0)

    work["attention_score_age"] = severity * days_open
    work["attention_score_inactivity"] = severity * days_since_update

    # Normalize priority names (e.g., "Medium (migrated)" -> "Medium")
    work["priority"] = work["priority"].apply(normalize_priority_name)

    # Select output columns - include all standard ticket table columns
    output_cols = ["key", "summary", "priority", "days_open", "days_since_update"]

    # Add optional columns if present
    optional_cols = [
        "priority_value",
        "status",
        "assignee",
        "reporter",
        "time_lost",
        "obs_system",
        "obs_subsystem",
        "obs_component",
        "created",
        "updated",
    ]
    for col in optional_cols:
        if col in work.columns:
            output_cols.append(col)

    output_cols.extend(["attention_score_age", "attention_score_inactivity"])

    # Filter to columns that exist
    output_cols = [c for c in output_cols if c in work.columns]
    output_cols = list(dict.fromkeys(output_cols))  # Remove duplicates, preserve order

    result = work[output_cols].copy()

    # Filter by minimum score if provided
    if min_score is not None:
        # Keep tickets where either score exceeds threshold
        score_mask = (result["attention_score_age"] > min_score) | (
            result["attention_score_inactivity"] > min_score
        )
        result = result[score_mask]

    if result.empty:
        return result

    # Get top N by age score and top N by inactivity score, then deduplicate
    top_by_age = result.nlargest(top_n, "attention_score_age")
    top_by_inactivity = result.nlargest(top_n, "attention_score_inactivity")

    # Combine and deduplicate, keeping highest attention_score_age for duplicates
    combined = pd.concat([top_by_age, top_by_inactivity]).drop_duplicates(subset=["key"])
    combined = combined.sort_values("attention_score_age", ascending=False)

    return combined.reset_index(drop=True)

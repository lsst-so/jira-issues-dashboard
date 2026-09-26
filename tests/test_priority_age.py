"""Tests for priority-age diagnostic analytics."""

import pandas as pd

from jira_app.analytics.metrics.priority_age import (
    CorrelationResult,
    compute_attention_scores,
    compute_attention_threshold,
    filter_open_tickets,
    has_hierarchy_data,
    median_age_heatmap,
    priority_age_by_group,
    priority_age_distribution,
)


def _sample_open_df() -> pd.DataFrame:
    """Create sample dataframe with open tickets of varying priority and age."""
    return pd.DataFrame(
        {
            "key": ["OBS-1", "OBS-2", "OBS-3", "OBS-4", "OBS-5", "OBS-6", "OBS-7", "OBS-8"],
            "priority": ["Blocker", "Critical", "High", "Medium", "Low", "Low", "Medium", "Undefined"],
            "priority_value": [5, 4, 3, 2, 1, 1, 2, 0],
            "status": [
                "In Progress",
                "Reported",
                "Testing",
                "To Do",
                "Tracking",
                "In Progress",
                "Reported",
                "To Do",
            ],
            "days_open": [5, 10, 30, 60, 90, 120, 45, 15],
            "days_since_update": [1, 3, 7, 14, 30, 45, 10, 5],
            "obs_system": ["TCS", "TCS", "M1M3", "M1M3", "Dome", "Dome", "TCS", None],
        }
    )


def _sample_mixed_df() -> pd.DataFrame:
    """Create sample dataframe with mix of open and closed tickets."""
    return pd.DataFrame(
        {
            "key": ["OBS-1", "OBS-2", "OBS-3", "OBS-4"],
            "priority": ["Blocker", "Critical", "High", "Medium"],
            "priority_value": [5, 4, 3, 2],
            "status": ["In Progress", "Done", "Cancelled", "To Do"],
            "days_open": [5, 10, 30, 60],
            "days_since_update": [1, 3, 7, 14],
        }
    )


class TestFilterOpenTickets:
    def test_filters_terminal_statuses(self):
        df = _sample_mixed_df()
        result = filter_open_tickets(df)
        assert len(result) == 2
        assert set(result["key"]) == {"OBS-1", "OBS-4"}

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = filter_open_tickets(df)
        assert result.empty

    def test_no_status_column(self):
        df = pd.DataFrame({"key": ["OBS-1"], "priority": ["High"]})
        result = filter_open_tickets(df)
        assert len(result) == 1

    def test_custom_terminal_statuses(self):
        df = _sample_mixed_df()
        result = filter_open_tickets(df, terminal_statuses=frozenset({"Done"}))
        assert len(result) == 3


class TestPriorityAgeDistribution:
    def test_basic_distribution(self):
        df = _sample_open_df()
        dist_df, corr = priority_age_distribution(df, metric_col="days_open")

        assert not dist_df.empty
        assert "priority" in dist_df.columns
        assert "days_open" in dist_df.columns
        assert "count" in dist_df.columns
        assert isinstance(corr, CorrelationResult)
        assert corr.n > 0

    def test_correlation_excludes_undefined(self):
        df = _sample_open_df()
        _, corr_exclude = priority_age_distribution(df, exclude_undefined_from_corr=True)
        _, corr_include = priority_age_distribution(df, exclude_undefined_from_corr=False)

        assert corr_exclude.n == 7
        assert corr_include.n == 8

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        dist_df, corr = priority_age_distribution(df)
        assert dist_df.empty
        assert corr.n == 0
        assert corr.rho is None

    def test_missing_columns(self):
        df = pd.DataFrame({"key": ["OBS-1"]})
        dist_df, corr = priority_age_distribution(df)
        assert dist_df.empty
        assert corr.n == 0

    def test_days_since_update_metric(self):
        df = _sample_open_df()
        dist_df, corr = priority_age_distribution(df, metric_col="days_since_update")

        assert not dist_df.empty
        assert "days_since_update" in dist_df.columns

    def test_uses_existing_priority_value(self):
        df = _sample_open_df()
        dist_df, _ = priority_age_distribution(df)
        assert "priority_value" in dist_df.columns
        blocker_rows = dist_df[dist_df["priority"] == "Blocker"]
        assert (blocker_rows["priority_value"] == 5).all()

    def test_fallback_without_priority_value(self):
        df = _sample_open_df().drop(columns=["priority_value"])
        dist_df, corr = priority_age_distribution(df)
        assert not dist_df.empty
        assert corr.n > 0


class TestPriorityAgeByGroup:
    def test_basic_grouping(self):
        df = _sample_open_df()
        result = priority_age_by_group(df, group_col="obs_system", min_group_size=2)

        assert not result.empty
        assert "group" in result.columns
        assert "rho" in result.columns
        assert "n" in result.columns

        pooled = result[result["group"] == "All groups"]
        assert len(pooled) == 1
        assert pooled.iloc[0]["is_pooled"] == True  # noqa: E712

    def test_min_group_size_filter(self):
        df = _sample_open_df()
        result_low = priority_age_by_group(df, group_col="obs_system", min_group_size=2)
        result_high = priority_age_by_group(df, group_col="obs_system", min_group_size=10)

        non_pooled_low = result_low[~result_low["is_pooled"]]
        non_pooled_high = result_high[~result_high["is_pooled"]]

        assert len(non_pooled_low) >= len(non_pooled_high)

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = priority_age_by_group(df, group_col="obs_system")
        assert result.empty

    def test_missing_group_column(self):
        df = _sample_open_df()
        result = priority_age_by_group(df, group_col="nonexistent")
        assert result.empty

    def test_handles_null_groups(self):
        df = _sample_open_df()
        result = priority_age_by_group(df, group_col="obs_system", min_group_size=1)

        groups = result["group"].tolist()
        assert "(Unspecified)" in groups or "All groups" in groups


class TestMedianAgeHeatmap:
    def test_basic_heatmap(self):
        df = _sample_open_df()
        result = median_age_heatmap(df, group_col="obs_system")

        assert not result.empty
        assert "group" in result.columns
        assert "priority" in result.columns
        assert "median" in result.columns
        assert "count" in result.columns
        assert "max_days" in result.columns
        assert "tickets_info" in result.columns
        assert "attention_count" in result.columns

    def test_attention_score_threshold(self):
        df = _sample_open_df()
        # Score threshold 100 = e.g., Blocker(5) × 20d or Critical(4) × 25d
        result = median_age_heatmap(df, group_col="obs_system", attention_score_threshold=100)

        assert not result.empty
        assert "attention_count" in result.columns
        total_attention = result["attention_count"].sum()
        assert total_attention >= 0

    def test_tickets_info_populated(self):
        df = _sample_open_df()
        result = median_age_heatmap(df, group_col="obs_system")

        non_empty_info = result[result["tickets_info"] != ""]
        assert len(non_empty_info) > 0

    def test_top_n_groups(self):
        df = _sample_open_df()
        result_all = median_age_heatmap(df, group_col="obs_system", top_n_groups=100)
        result_limited = median_age_heatmap(df, group_col="obs_system", top_n_groups=2)

        unique_groups_all = result_all["group"].nunique()
        unique_groups_limited = result_limited["group"].nunique()

        assert unique_groups_limited <= 2
        assert unique_groups_limited <= unique_groups_all

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = median_age_heatmap(df, group_col="obs_system")
        assert result.empty

    def test_missing_columns(self):
        df = pd.DataFrame({"key": ["OBS-1"]})
        result = median_age_heatmap(df, group_col="obs_system")
        assert result.empty


class TestHasHierarchyData:
    def test_has_data(self):
        df = _sample_open_df()
        assert has_hierarchy_data(df, "obs_system") is True

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        assert has_hierarchy_data(df, "obs_system") is False

    def test_missing_column(self):
        df = _sample_open_df()
        assert has_hierarchy_data(df, "nonexistent") is False

    def test_all_null_values(self):
        df = pd.DataFrame({"obs_system": [None, None, None]})
        assert has_hierarchy_data(df, "obs_system") is False

    def test_all_empty_strings(self):
        df = pd.DataFrame({"obs_system": ["", "  ", ""]})
        assert has_hierarchy_data(df, "obs_system") is False


class TestCorrelationResult:
    def test_direction_positive(self):
        result = CorrelationResult(rho=0.5, p_value=0.01, n=10, significant=True)
        assert result.direction == "positive"

    def test_direction_negative(self):
        result = CorrelationResult(rho=-0.5, p_value=0.01, n=10, significant=True)
        assert result.direction == "negative"

    def test_direction_zero(self):
        result = CorrelationResult(rho=0.0, p_value=0.99, n=10, significant=False)
        assert result.direction == "none"

    def test_direction_none_when_rho_none(self):
        result = CorrelationResult(rho=None, p_value=None, n=2, significant=None)
        assert result.direction is None


class TestComputeAttentionScores:
    def test_basic_scores(self):
        df = _sample_open_df()
        result = compute_attention_scores(df, top_n=5)

        assert not result.empty
        assert "attention_score_age" in result.columns
        assert "attention_score_inactivity" in result.columns
        assert "key" in result.columns
        assert "priority" in result.columns

    def test_score_calculation(self):
        df = _sample_open_df()
        result = compute_attention_scores(df, top_n=10)

        # Blocker (priority_value=5) with days_open=5 should score 25
        blocker_row = result[result["key"] == "OBS-1"]
        if not blocker_row.empty:
            assert blocker_row.iloc[0]["attention_score_age"] == 5 * 5  # 25

    def test_sorted_by_age_score(self):
        df = _sample_open_df()
        result = compute_attention_scores(df, top_n=10)

        if len(result) > 1:
            scores = result["attention_score_age"].tolist()
            assert scores == sorted(scores, reverse=True)

    def test_top_n_limit(self):
        df = _sample_open_df()
        result = compute_attention_scores(df, top_n=3)

        # Should have at most 2*top_n (combined from both metrics, deduplicated)
        assert len(result) <= 6

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        result = compute_attention_scores(df)
        assert result.empty

    def test_missing_columns(self):
        df = pd.DataFrame({"key": ["OBS-1"], "summary": ["Test"]})
        result = compute_attention_scores(df)
        assert result.empty

    def test_min_score_filter(self):
        df = _sample_open_df()
        # Get all scores first
        all_results = compute_attention_scores(df, top_n=100)
        if all_results.empty:
            return

        # Find a threshold that filters some but not all
        median_score = all_results["attention_score_age"].median()
        filtered = compute_attention_scores(df, top_n=100, min_score=median_score)

        # Filtered should have fewer or equal tickets
        assert len(filtered) <= len(all_results)
        # All filtered tickets should exceed threshold
        if not filtered.empty:
            assert (
                (filtered["attention_score_age"] > median_score)
                | (filtered["attention_score_inactivity"] > median_score)
            ).all()


class TestComputeAttentionThreshold:
    def test_basic_threshold(self):
        df = _sample_open_df()
        threshold = compute_attention_threshold(df, percentile=50)

        assert threshold >= 0
        assert isinstance(threshold, float)

    def test_higher_percentile_higher_threshold(self):
        df = _sample_open_df()
        threshold_50 = compute_attention_threshold(df, percentile=50)
        threshold_90 = compute_attention_threshold(df, percentile=90)

        assert threshold_90 >= threshold_50

    def test_empty_dataframe(self):
        df = pd.DataFrame()
        threshold = compute_attention_threshold(df)
        assert threshold == 0.0

    def test_missing_columns(self):
        df = pd.DataFrame({"key": ["OBS-1"], "summary": ["Test"]})
        threshold = compute_attention_threshold(df)
        assert threshold == 0.0

    def test_different_metric_cols(self):
        df = _sample_open_df()
        threshold_age = compute_attention_threshold(df, metric_col="days_open")
        threshold_update = compute_attention_threshold(df, metric_col="days_since_update")

        # Both should be valid non-negative values
        assert threshold_age >= 0
        assert threshold_update >= 0

from datetime import datetime, timedelta

import pytest

from app.domain.services.review_policy import ReviewPolicy


@pytest.fixture
def policy():
    return ReviewPolicy()


class TestKnown:
    def test_advances_stage(self, policy):
        stage, _ = policy.calculate(0, "known")
        assert stage == 1

    def test_stage_capped_at_max(self, policy):
        max_stage = len(policy.intervals) - 1
        stage, _ = policy.calculate(max_stage, "known")
        assert stage == max_stage

    def test_next_review_matches_interval(self, policy):
        before = datetime.now()
        stage, next_at = policy.calculate(1, "known")
        expected_days = policy.intervals[stage]
        assert next_at >= before + timedelta(days=expected_days - 1)
        assert next_at <= before + timedelta(days=expected_days + 1)


class TestFuzzy:
    def test_keeps_stage(self, policy):
        stage, _ = policy.calculate(2, "fuzzy")
        assert stage == 2

    def test_next_review_tomorrow(self, policy):
        before = datetime.now()
        _, next_at = policy.calculate(2, "fuzzy")
        assert next_at >= before + timedelta(hours=23)
        assert next_at <= before + timedelta(hours=25)


class TestUnknown:
    def test_resets_to_stage_zero(self, policy):
        stage, _ = policy.calculate(4, "unknown")
        assert stage == 0

    def test_next_review_tomorrow(self, policy):
        before = datetime.now()
        _, next_at = policy.calculate(3, "unknown")
        assert next_at >= before + timedelta(hours=23)
        assert next_at <= before + timedelta(hours=25)


class TestInvalid:
    def test_raises_on_bad_level(self, policy):
        with pytest.raises(ValueError):
            policy.calculate(0, "maybe")

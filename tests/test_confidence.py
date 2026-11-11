import numpy as np
import pytest

from timetravel3d.confidence import ConfidenceConfig, score_and_filter
from timetravel3d.experiments import grid_coverage, matched_retention_masks


def test_scores_monotonic_and_observation_support_is_real():
    scores, masks = score_and_filter([.1, .5, 1], [2, 2, 2], [4, 4, 4])
    assert np.all(np.diff(scores["combined"]) < 0)
    s, _ = score_and_filter([.1] * 3, [2] * 3, [2, 3, 4])
    assert np.all(np.diff(s["multiview"]) > 0)
    assert masks["baseline"].all()


def test_low_parallax_not_hidden_by_low_reprojection_error():
    _, masks = score_and_filter([0, 0], [.001, 3], [2, 4])
    assert masks["reprojection"].tolist() == [True, True]
    assert masks["combined"].tolist() == [False, True]
    assert masks["multiview"].tolist() == [False, True]


def test_two_view_support_filter_is_explicit_and_empty_is_valid():
    _, masks = score_and_filter([0, 0], [2, 3], [2, 2])
    assert not masks["multiview"].any()
    _, empty = score_and_filter([], [], [])
    assert empty["baseline"].size == 0


def test_reject_invalid_inputs_and_config():
    with pytest.raises(ValueError):
        ConfidenceConfig(combined_weights=(0, 0))
    with pytest.raises(ValueError):
        score_and_filter([np.nan], [2], [3])
    with pytest.raises(ValueError):
        score_and_filter([1, 2], [2], [3])


def test_count_matched_controls_and_fixed_coverage_denominator():
    s, masks = score_and_filter([.1, .2, 2], [2, .01, 2], [3, 3, 3])
    control = matched_retention_masks(s, masks)
    assert all(m.sum() == masks["combined"].sum() for m in control.values())
    data = {"view_ids": np.array([0]), "obs_view": np.array([0, 0, 0]),
            "obs_point": np.array([0, 1, 2]), "obs_xy": np.array([[0, 0], [10, 10], [20, 20]])}
    base = grid_coverage(data, np.array([True, True, True]))
    filtered = grid_coverage(data, np.array([True, False, False]))
    assert base["grid_coverage_retention"] == 1
    assert filtered["grid_coverage_retention"] == pytest.approx(1 / 3)
    assert filtered["baseline_occupied_cells"] == 3

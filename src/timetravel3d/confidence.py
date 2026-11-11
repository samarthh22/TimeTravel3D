"""Project contribution: heuristic confidence, separate from frozen SfM geometry."""
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import yaml


@dataclass(frozen=True)
class ConfidenceConfig:
    error_scale_px: float = 1.
    angle_scale_deg: float = 1.
    support_target: int = 4
    reprojection_threshold_px: float = .5
    angle_threshold_deg: float = .3
    score_threshold: float = .65
    min_observations: int = 3
    combined_weights: tuple = (.6, .4)
    multiview_weights: tuple = (.45, .35, .2)

    def __post_init__(self):
        numeric = [self.error_scale_px, self.angle_scale_deg, self.reprojection_threshold_px,
                   self.angle_threshold_deg, self.score_threshold]
        if not np.isfinite(numeric).all() or min(numeric[:4]) <= 0:
            raise ValueError("Confidence scales and geometric thresholds must be finite and positive")
        if not 0 <= self.score_threshold <= 1:
            raise ValueError("Confidence threshold must be in [0, 1]")
        if self.support_target < 3 or self.min_observations < 2:
            raise ValueError("Support target must be >=3; minimum observations must be >=2")
        for weights, size in ((self.combined_weights, 2), (self.multiview_weights, 3)):
            if len(weights) != size or not np.isfinite(weights).all() or min(weights) < 0 or sum(weights) <= 0:
                raise ValueError("Score weights must be finite, nonnegative, and have positive sum")

    @classmethod
    def load(cls, path=None):
        return cls(**(yaml.safe_load(Path(path).read_text()) or {})) if path else cls()

    def dictionary(self):
        return asdict(self)


def weighted_geometric(signals, weights):
    weights = np.asarray(weights, float)
    weights = weights / weights.sum()
    return np.exp(np.sum(np.log(np.clip(np.asarray(signals), 1e-15, 1)) * weights[:, None], axis=0))


def score_and_filter(errors, angle, support, config=None):
    config = config or ConfidenceConfig()
    errors, angle, support = [np.asarray(x, float) for x in (errors, angle, support)]
    if errors.ndim != 1 or errors.shape != angle.shape or errors.shape != support.shape:
        raise ValueError("Confidence inputs must be equal-length vectors")
    if not all(np.isfinite(x).all() for x in (errors, angle, support)):
        raise ValueError("Confidence inputs must be finite")
    if (errors < 0).any() or (angle < 0).any() or (angle > 180).any() or (support < 2).any() or (support != np.floor(support)).any():
        raise ValueError("Invalid error, angle, or observation support")
    r = np.exp(-errors / config.error_scale_px)
    a = np.clip(angle / config.angle_scale_deg, 0, 1)
    s = np.clip((support - 1) / (config.support_target - 1), 0, 1)
    combined = weighted_geometric([r, a], config.combined_weights)
    multiview = weighted_geometric([r, a, s], config.multiview_weights)
    scores = {"reprojection": r, "angle": a, "support": s,
              "combined": combined, "multiview": multiview}
    masks = {"baseline": np.ones(len(errors), bool),
        "reprojection": errors <= config.reprojection_threshold_px,
        "angle": angle >= config.angle_threshold_deg,
        "combined": combined >= config.score_threshold,
        "multiview": (multiview >= config.score_threshold) & (support >= config.min_observations)}
    return scores, masks

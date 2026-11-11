# Confidence contribution (dedicated commit)

Research question: can reprojection error, ray angle and observation support
identify unreliable sparse SfM points while preserving useful spatial coverage?
The project tests this combination as a course-level contribution. These signals
and confidence filtering already exist in the field; no field-level novelty or
accuracy improvement is claimed without measured evidence.

## Method

For each frozen baseline point, let e be its mean observation residual in pixels,
theta its largest pairwise triangulation angle in degrees, and n the number of
distinct registered images with a verified observation.

- Reprojection signal: `r = exp(-e / error_scale_px)`.
- Angle signal: `a = clip(theta / angle_scale_deg, 0, 1)`.
- Support signal: `s = clip((n - 1) / (support_target - 1), 0, 1)`.
- Combined score: normalized weighted geometric mean of `(r, a)`.
- Multi-view score: normalized weighted geometric mean of `(r, a, s)`.

Geometric averaging penalizes a weak signal instead of allowing a strong signal
to compensate completely. Scores are rankings, not calibrated probabilities.
All weights, scales, and cutoffs are prespecified heuristic hypotheses in
`configs/confidence.yaml`. They are not learned from or optimized on test data.
Observation support is always two in two-view geometry and cannot discriminate
points there; the default multi-view filter requires at least three observations.

## Controlled experiments

```powershell
python -m timetravel3d ablate results/rig_delivery_area --config configs/confidence.yaml --output results/rig_ablation
```

Five modes: all baseline points, reprojection-only, angle-only, combined, and
multi-view support. Two additional controls rank by reprojection or angle and
retain exactly the combined method's point count. Cameras, features, geometry,
and geometric verification gates are frozen before filtering.

Reports pair residuals with retention and occupied-cell retention in a fixed
10x10 image grid per view. Grid bounds and occupied-cell denominators come from
the baseline and never shrink with the filter. This is a feature coverage proxy,
not surface completeness. Independent disparity/laser-scan evaluation is needed
to test 3D quality, and results can contradict the hypothesis.

Outputs: ablation JSON, CSV, per-mode colored PLY, raw scores/masks, confidence
histograms, and retention/coverage plots. Empty filters are reported as empty,
with undefined quality metrics represented by JSON null, never fabricated zeros.

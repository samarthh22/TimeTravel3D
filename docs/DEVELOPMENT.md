# Validated development stages

Each successful stage is committed and pushed separately. The confidence
contribution will have a dedicated commit after the geometric baseline.

## Stage 1: calibrated two-view baseline

- Inspected actual local ETH3D `calib.txt`, `cameras.txt`, `images.txt`, PFM,
  and mask filenames before implementing the loader.
- Implemented SIFT, mutual ratio matching, RANSAC essential matrix,
  cheirality pose selection, triangulation, reprojection/angle metrics,
  camera exports, colored PLY, and report provenance.
- Environment: dedicated repository `.venv`, Python 3.13.7.
- `python -m pytest -q`: **7 passed**.
- `python -m timetravel3d two-view ../two_view_training/delivery_area_1l --output results/baseline_delivery_area_1l`:
  322 ratio matches, 287 essential inliers, 165 finite positive-depth points,
  median reprojection error 0.2453 px, median angle 0.1414 degrees.
- This pair has weak parallax. Passing checks does not imply accurate depth;
  independent ground-truth evaluation follows in the evaluation stage.

Raw datasets, derived point clouds, environments, and machine-specific paths
are excluded from Git. Small aggregate measured tables may be committed to
`benchmarks/` in a later stage.

## Stage 2: incremental multi-view geometry

- Inspected rig calibration: delivery_area has 948 images, four cameras, 237
  timestamps per camera, PINHOLE models and per-image world-to-camera extrinsics.
- Inspected high-resolution courtyard: 38 images with four intrinsic blocks.
- Implemented conflict-aware tracks, parallax-based initialization, PnP-RANSAC,
  consensus multi-view triangulation, and constrained robust sparse BA.
- `python -m pytest -q`: **11 passed**, including a four-camera synthetic
  incremental reconstruction, PnP with outliers, and BA against known 3D geometry.
- Rig delivery_area, `--views 5 --stride 12`: **5/5 estimated cameras**, 562
  points, median residual 0.2268 px, mean observation support 2.8203.
- Same subset with `--known-poses`: 562 points, median residual 0.1579 px;
  explicitly recorded as a known-pose experiment.
- High-resolution courtyard, `--views 6` (images resized to 1600 px maximum):
  **6/6 estimated cameras**, 5,267 points, median residual 0.0925 px,
  mean support 3.0328; reconstruction runtime 29.10 seconds.
- BA on the estimated rig subset converged in 5 evaluations, residual component
  RMSE 0.3080 to 0.2961 px. This is optimizer validation, not evidence of improved
  ground-truth reconstruction accuracy.

## Stage 3: dedicated confidence contribution

- Added separate `confidence.py`, configurable geometric score hypotheses,
  five ablations, two matched-count controls, and frozen-baseline grid coverage.
- `python -m pytest -q`: **16 passed**.
- Rig delivery_area: baseline 562 points; reprojection 487; angle 562;
  combined 530 (94.31% retention, 95.32% occupied-cell retention);
  multi-view support 275 (48.93% retention, 75.92% occupied-cell retention).
- No 3D accuracy conclusion is inferred from these retention/residual results.

## Stage 4: independent evaluation and reproducible experiments

- Implemented PFM endian/orientation and non-occlusion handling, stereo metric
  scale, camera-pose similarity alignment, MeshLab scan transforms, and sampled
  laser-scan nearest-neighbor diagnostics with explicit protocol limitations.
- Added runtime, native process peak memory, environment lock, full benchmark
  runner, measured report generator, presentation outline and viva notes.
- `python -m pytest -q`: **21 passed**. `python -m pip check`: no broken requirements.
- Full benchmark: **31/31 experiments completed**, covering every local two-view
  training scene plus two rig and two DSLR subsets. All four subsets had 5+
  registered cameras; meadow registered 5/6 and reports the missing view.
- Recomputed all ablations/evaluation from frozen baselines after correcting the
  angle-only matched-count control to rank unsaturated angles. No confidence
  thresholds or reconstruction parameters were tuned from the measured errors.
- Aggregate 217-row tables and interpretation are in `benchmarks/measured/`
  and `docs/RESULTS.md`. Filtering does not consistently improve independent
  ground-truth diagnostics; empty filters and undefined metrics are retained.

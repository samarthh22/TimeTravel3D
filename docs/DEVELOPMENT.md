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

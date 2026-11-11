# TimeTravel 3D

Confidence-Aware Sparse 3D Reconstruction Using Feature Matching and Multi-View Geometry.
Python source files implement the geometry; no notebooks or COLMAP wrapper are required.

## Environment (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
```

Activation is optional: `.\.venv\Scripts\python.exe` can replace `python` in every command.
Python 3.10+ is supported. Keep the virtual environment and ETH3D data outside Git.

## Calibrated two-view baseline

With the extracted datasets beside this repository:

```powershell
python -m timetravel3d inspect ..\two_view_training\delivery_area_1l
python -m timetravel3d two-view ..\two_view_training\delivery_area_1l --config configs\default.yaml --output results\delivery_area_1l
```

Outputs: `points_baseline.ply`, `reconstruction.npz`, `cameras.json`, `report.json`,
`feature_matches.jpg`, and `reconstruction.png`. The baseline retains finite,
positive-depth essential-matrix inlier triangulations; it has no confidence filter.

Intrinsics come from the supplied PINHOLE calibration. Images are resized with
matching intrinsics. Coordinates use `X_camera = R @ X_world + t`, and camera
centers are `-R.T @ t`. COLMAP pixel centers are converted to OpenCV coordinates.
Estimated monocular SfM has arbitrary scale. Supplied extrinsics are never used
to estimate the baseline pose. Parameters and software versions are in reports.

## Incremental multi-view reconstruction

```powershell
python -m timetravel3d inspect ..\multi_view_training_rig_undistorted\delivery_area
python -m timetravel3d multi-view ..\multi_view_training_rig_undistorted\delivery_area --views 5 --stride 12 --output results\rig_delivery_area
python -m timetravel3d multi-view ..\multi_view_training_dslr_undistorted\courtyard --views 6 --output results\dslr_courtyard
```

Fresh SIFT matches build conflict-free tracks. The initial pair is chosen using
inlier support and parallax; further cameras use PnP-RANSAC with 2D-3D tracks.
Consensus triangulation supports more than two observations. Sparse robust bundle
adjustment fixes intrinsics and the two seed poses (including their relative pose).
The baseline has standard 4 px track verification and a 0.05 degree conditioning
floor, applied before every later confidence variant. Use `--no-ba` to disable BA.

For rig data the default is a temporal subset of the lowest camera ID; use
`--camera-id` to choose another sensor. This is single-sensor SfM from rig images,
not a rigid-rig optimizer. `--views`, `--stride`, and `--start` define the subset.
Use a temporal stride that provides parallax; neighboring video frames can be
degenerate. Unregistered views and registration rate are reported explicitly.

Adding `--known-poses` uses supplied ETH3D extrinsics and disables pose estimation
and BA. Reports label this `known_pose_triangulation`; it is not estimated SfM.
Supplied COLMAP points and observations are never reused as input or ground truth.

## References and research scope

The [confidence method](docs/NOVELTY.md) has its own implementation commit.
Run its five frozen-baseline ablations and two point-count-matched controls:

```powershell
python -m timetravel3d ablate results\rig_delivery_area --config configs\confidence.yaml --output results\rig_ablation
```

JSON/CSV, point clouds, and plots expose retention and image grid coverage.
Weights and cutoffs are configurable hypotheses.

- [Schönberger & Frahm, Structure-from-Motion Revisited, CVPR 2016](https://openaccess.thecvf.com/content_cvpr_2016/html/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.html)
- [COLMAP](https://github.com/colmap/colmap) and its [text format](https://colmap.github.io/format.html)
- [Pan et al., Global Structure-from-Motion Revisited, ECCV 2024](https://arxiv.org/abs/2407.20219)
- [ETH3D dataset documentation](https://www.eth3d.net/documentation)

The proposed contribution is an experimentally evaluated combination of geometric
confidence signals, not a claim that confidence filtering is new to the field.
Lower reprojection error alone does not establish improved 3D accuracy. Report
point retention, image coverage, and independent ground-truth error together.

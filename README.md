# TimeTravel 3D

Confidence-Aware Sparse 3D Reconstruction Using Feature Matching and Multi-View Geometry.

The finalized Python project includes an offline interactive demo and a frozen experimental study. Development and execution use the repository virtual environment. No notebooks or GPU training are required.

## Project documentation

- [Final results and limitations](docs/FINAL_RESULTS.md)
- [V2 contribution and formula](docs/NOVELTY_V2.md)
- [CIF alignment](docs/COURSE_ALIGNMENT.md) and [viva preparation](docs/VIVA.md)

## Measured evidence

At an 80% point budget, median distance to a fixed scan sample improves on **9/11 evaluable V2 held-out multi-view subsets**, with **11.96% mean relative reduction** against retaining all points. Against equal-budget reprojection ranking, it improves on 6/11, averaging **6.46% lower distance**. Median occupied image-cell coverage retention across primary successful experiments is **100%**.

In a controlled Gaussian-noise study over ten seeds, mean seed-level median 3D error is **29.64% lower** than the full baseline and **16.39% lower** than equal-budget reprojection ranking. This study uses known cameras and correspondences.

These are bounded empirical results. Two eligible held-out subsets regress. Playground rig fails positive-scale alignment at three seeds. Some camera registrations remain incomplete. Conditional covariance cannot detect systematic camera bias. No universal superiority or official ETH3D leaderboard score is claimed.

## Environment and demo (PowerShell)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest -q
python scripts/run_demo.py
```

Open the printed `results/demo/viewer.html` path in a browser. Drag to rotate, scroll to zoom, and toggle baseline versus proposed selection. The demo reuses cached final courtyard results when present and reconstructs the same six-view subset otherwise. Activation is optional: use `.venv/Scripts/python.exe` directly. Python 3.10+ is supported; the validated environment uses Python 3.13.7.

## Reproduce the final study

Keep the six original extracted dataset folders beside this repository, matching the supplied structure. Original archives and datasets remain unchanged.

```powershell
python scripts/run_final_study.py
python scripts/synthetic_study.py
python scripts/report_final_study.py
```

The frozen protocol attempts every provided scene: 27 stereo pairs, 5 rig scenes and 13 DSLR scenes, using 5 or 6 images per multi-view scene. Twelve additional multi-view subsets run at three seeds. **66/69 runs completed evaluation**. All attempts, failures, partial registrations, seeds, image names and source revisions are recorded. Final-protocol images use a maximum side of 1200 pixels. This does not process every multi-view image at native resolution.

`--resume` reuses successful runs with the same protocol hash. Large point clouds and logs remain under ignored `results/`. Aggregate tables live in `benchmarks/final/` and `benchmarks/synthetic/`. Earlier V1 measurements remain in `benchmarks/measured/` for transparency.

[final_protocol.json](configs/final_protocol.json) fixes the development split, 80% budget, 0.5 px noise floor and 500,000-point scan sampling budget before the additional multi-view evaluation. Prior V1 stereo exposure includes some shared physical scenes, so this is not a pristine external test set.

## Implementation and geometry modes

SIFT, Lowe-ratio/mutual matching, RANSAC essential geometry, conflict-free tracks, PnP-RANSAC, consensus triangulation and sparse robust BA form the baseline. Minimal-gauge BA fixes the first pose and seed baseline length while refining the second seed pose. Supplied COLMAP points and feature observations are never reused as input.

The proposed selector ranks continuous conditional covariance, reserves safe representatives of occupied image cells, then fills a fixed budget. Controls isolate residual, angle, support, uncertainty and coverage effects on identical frozen geometry.

```powershell
python -m timetravel3d inspect ../multi_view_training_rig_undistorted/delivery_area
python -m timetravel3d multi-view ../multi_view_training_rig_undistorted/delivery_area --views 5 --stride 12 --output results/rig_example
python -m timetravel3d two-view ../two_view_training/delivery_area_1l --config configs/rectified.yaml --output results/stereo_example
```

Default two-view mode estimates general relative pose through an essential matrix. The final stereo study explicitly uses ETH3D's declared rectification through `rectified_stereo`, without GT extrinsics or disparity. Multi-view `--known-poses` is separately labeled known-pose triangulation. Rig subsets use a temporal sensor stream, not rigid-rig optimization.

Coordinates use `Xcamera = R @ Xworld + t` and camera center `-R.T @ t`. Monocular scale is arbitrary until evaluation. Real calibration supplies intrinsics. JSON/NPZ, camera poses, matching images and colored PLY exports record provenance. Static cloud plots use central 96% display bounds so extreme points cannot compress the view; complete point clouds and evaluations retain every baseline point.

## Release checks

```powershell
python -m pytest -q
python scripts/check_release.py
```

These checks validate the project and result accounting without requiring any presentation files. Presentation materials remain local and are excluded from this repository.

## References

- [Schönberger and Frahm, Structure-from-Motion Revisited, CVPR 2016](https://openaccess.thecvf.com/content_cvpr_2016/html/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.html)
- [COLMAP](https://colmap.github.io/) and [Pan et al., GLOMAP, ECCV 2024](https://arxiv.org/abs/2407.20219)
- [Ceres least-squares covariance](https://ceres-solver.readthedocs.io/latest/nnls_covariance.html)
- [ETH3D documentation](https://www.eth3d.net/documentation) and [dataset license](https://www.eth3d.net/)

This is an implemented and measured course project combination of established ideas. COLMAP/GLOMAP are literature references; a numerical comparison against them is not claimed.

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

## References and research scope

- [Schönberger & Frahm, Structure-from-Motion Revisited, CVPR 2016](https://openaccess.thecvf.com/content_cvpr_2016/html/Schonberger_Structure-From-Motion_Revisited_CVPR_2016_paper.html)
- [COLMAP](https://github.com/colmap/colmap) and its [text format](https://colmap.github.io/format.html)
- [Pan et al., Global Structure-from-Motion Revisited, ECCV 2024](https://arxiv.org/abs/2407.20219)
- [ETH3D dataset documentation](https://www.eth3d.net/documentation)

The proposed contribution is an experimentally evaluated combination of geometric
confidence signals, not a claim that confidence filtering is new to the field.
Lower reprojection error alone does not establish improved 3D accuracy. Report
point retention, image coverage, and independent ground-truth error together.

# Evaluation and reproducibility

This document records the V1 evaluation workflow. The final V2 protocol,
minimal-gauge optimizer, complete scene attempt list, repeated seeds and measured
conclusions are in [FINAL_RESULTS.md](FINAL_RESULTS.md) and the root README.

## Run all three categories

From the repository, using the dedicated virtual environment:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe scripts\run_benchmarks.py --data-root .. --output results\benchmark --publish-dir benchmarks\measured
```

The data root contains the six original extracted ETH3D training directories.
No images, archives, source metadata, or ground truth are modified. Each scene
runs in a fresh process using the same virtual-environment Python. The runner
records failures and returns a nonzero exit status if any experiment fails.
Large reconstructions and logs stay in ignored `results/`. Only small metric
tables and provenance manifests are published to `benchmarks/measured/`.

Selection is prespecified: all 27 available two-view training scenes; five views
at temporal stride 12 from the lowest camera ID of delivery_area and electro rig
sequences; first six filename-sorted DSLR views from courtyard and meadow.
High-resolution source images are resized to a maximum side of 1600 pixels with
intrinsics adjusted identically. This tests a high-resolution dataset source,
not a claim of native-resolution processing or full-scene reconstruction.

Configuration is fixed before evaluation. No parameters are tuned on any of
these reporting scenes. They are exploratory training-data experiments, not a
held-out generalization study. An independent development/test split and more
seeds are needed before claiming generalizable improvements.

## Two-view ground truth

```powershell
python -m timetravel3d evaluate results\delivery_area_1l --scene ..\two_view_training\delivery_area_1l --ground-truth ..\two_view_training_gt\delivery_area_1l --config configs\confidence.yaml --output results\delivery_area_eval
```

PFM files are little-endian, vertically reversed relative to normal image arrays,
and use infinity for invalid data. Only mask value 255 (non-occluded pixels) is
evaluated. Each left-view SIFT observation maps back to native resolution; the
nearest native pixel supplies disparity. No interpolation spans invalid regions.
Depth is `Z_m = fx * baseline_mm / (1000 * (disparity + doffs))`.
The supplied baseline fixes the otherwise unknown monocular scale for evaluation
only. Its value is never fed into pose estimation. Predicted points are compared
in the first-camera frame against ground truth along the observed native ray.

Report evaluated sample count, point/depth/disparity errors, point retention,
and image-grid coverage together. These are sparse diagnostics, not official
dense ETH3D error rates or complete surface estimates. Nearest-pixel sampling
can introduce error at depth discontinuities.

## Multi-view laser scans

```powershell
python -m timetravel3d evaluate results\rig_delivery_area --scene ..\multi_view_training_rig_undistorted\delivery_area --ground-truth ..\multi_view_training_rig_scan_eval\delivery_area\rig_scan_eval --output results\rig_eval
```

Each PLY scan is transformed to the scene world using its `MLMatrix44` from
`scan_alignment.mlp`. A fixed deterministic uniform vertex-index sample, up to
200,000 points total, bounds memory. `--max-scan-points` changes this budget.
Nearest-neighbor distance to a sampled scan overestimates distance to the full
scan; this approximation is recorded in the report. The same scan sample serves
every method and count-matched control within a scene.

Estimated SfM is aligned using corresponding supplied camera poses, not scan ICP:
average orientation differences determine rotation; camera centers determine
positive scale and translation. This works even for nearly collinear video
trajectories. Report camera-center RMSE and median rotation error after alignment.
The exact same fitted similarity is applied to every filtered point set.
Known-pose experiments already use the scene frame and use the identity alignment.

Report retained-point distance distributions and the fraction within a fixed
5 cm threshold. Reverse nearest-neighbor coverage over the sampled **whole scene**
is also reported, explicitly as sampled scene coverage. A small camera subset
cannot cover the entire scene, so this is not official completeness. Visibility,
occlusion meshes, and official ETH3D evaluation tolerances are not reproduced.
Official leaderboard metrics require the [official evaluation tools](https://www.eth3d.net/documentation#evaluation).

## Timing, memory and comparisons

Reconstruction time covers image loading, features, matching, geometry and BA;
it excludes output plots/exports and subsequent evaluation. Peak process working
set/RSS includes Python and native libraries up to report creation. Every method
reuses one reconstruction, so its reconstruction time and camera count are shared.
Filtering/evaluation overhead is not represented as a separate performance claim.

`requirements-lock.txt` records the actual Python 3.13 environment. To recreate
it with a compatible Python interpreter, install the lock and then the package:

```powershell
python -m pip install -r requirements-lock.txt
python -m pip install -e .
```

For another supported Python version, use `requirements.txt` to resolve compatible
versions instead. Reports record the actual versions used. A COLMAP numerical
baseline is not run here; COLMAP and GLOMAP are literature references, while
synthetic known geometry independently validates the implemented calculations.

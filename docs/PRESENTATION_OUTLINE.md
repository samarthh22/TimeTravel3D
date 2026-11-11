# Ten-slide presentation source

This is a slide content outline, not a generated PPTX. Use the exact ten-slide
structure from the project handover; measured source tables are in `benchmarks/`.

## 1. Motivation

Sparse 3D reconstruction links camera images to scene geometry. Bad feature
matches, small baselines and pose errors can create unreliable depth. Ask whether
transparent confidence signals improve reliability while retaining coverage.

## 2. Literature: main reference

Schönberger and Frahm, *Structure-from-Motion Revisited*, CVPR 2016; COLMAP.
Use it to explain incremental SfM and robust reconstruction. Our implementation
uses OpenCV/SciPy primitives with Python track/geometry logic; it is not COLMAP.
We do not claim COLMAP's robustness or report an unmeasured numerical comparison.

## 3. Literature: broader context and contribution

Pan et al., *Global Structure-from-Motion Revisited*, ECCV 2024 (GLOMAP),
illustrates the global alternative. Our smaller course project studies a
confidence-filtering hypothesis, not a replacement for a complete global system.
The measured contribution is the separate confidence module and controlled
single-signal, combined, support and count-matched ablations.

## 4. Methodology: system overview

ETH3D undistorted images + real calibration -> SIFT -> ratio/mutual matching ->
RANSAC geometry -> triangulation -> incremental PnP + BA -> frozen baseline ->
confidence filtering -> retention, coverage and ground-truth diagnostics.
Use all three source categories; high-resolution DSLR images are resized for
development. Keep known-pose triangulation distinct from estimated SfM.

## 5. Methodology: feature extraction and matching

Explain DoG extrema, SIFT orientations/descriptors, descriptor distances,
Lowe ratio 0.75, and mutual checks. Show a locally generated
`results/benchmark/*/baseline/feature_matches.jpg` from a two-view scene.
OpenCV implements SIFT; Python implements the matching policy and data flow.

## 6. Methodology: robust epipolar geometry

Normalize pixel observations with each image's own intrinsics. RANSAC estimates
E, satisfying `x2.T E x1 = 0`. Decompose E and select the positive-depth solution.
Show synthetic outlier and different-intrinsics tests as correctness evidence.

## 7. Methodology: camera pose and triangulation

Use `Xc = R Xw + t`, `P = K[R|t]`, `C = -R.T t`.
Explain homogeneous triangulation, cheirality and monocular scale ambiguity.
Show why weak parallax can preserve small pixel residuals while depth is wrong.

## 8. Methodology: multi-view extension

Conflict-free feature tracks -> seed pair with parallax -> 2D-3D PnP-RANSAC ->
consensus multi-view DLT -> constrained robust sparse BA.
BA fixes intrinsics and both seed poses. Rig experiments use one temporal
sensor stream, not rigid-rig optimization. Meadow registers only 5/6 views.

## 9. Methodology: confidence and experimental controls

Define `r=exp(-e/sigma)`, saturated angle score, and distinct-image support.
Combine them with configurable weighted geometric means. Freeze geometry for
all filters. Compare baseline, reprojection-only, angle-only, combined and
multi-view support; include matched-point-count ranking controls.
Evaluate errors alongside point retention and baseline image-grid retention.

## 10. Results and limitations

Use `benchmarks/measured/comparison.png` and `docs/RESULTS.md`.
31 experiments completed; courtyard reconstructed 5,267 points with 6/6 cameras.
Courtyard sampled-scan median distance: baseline 0.03485 m; combined 0.03469 m
(5,219 points); support variant 0.03303 m (2,704 points). These are approximate
sparse scan diagnostics after camera-pose alignment, not official ETH3D scores.
Delivery_area rig gets worse after filtering. Five two-view combined filters
return no points. The heuristic does not consistently improve 3D error; the
hypothesis remains unproven. Explain sampling, coverage loss, exploratory
training-only evaluation, constrained BA and missing dense/official benchmarks.

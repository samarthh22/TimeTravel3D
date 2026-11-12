# Viva preparation

**What is implemented?** A Python pipeline around OpenCV SIFT and numerical
geometry primitives, with our own calibrated loaders, matching policy, pose
selection, feature tracks, incremental registration, triangulation consensus,
SciPy sparse bundle adjustment, confidence experiments, exports and evaluation.
It does not call COLMAP or use the supplied COLMAP reconstruction as its answer.

**Why SIFT?** It detects scale-space extrema using differences of Gaussians,
assigns orientations and describes local gradients. Descriptor distances permit
matching across changes in scale, rotation, and moderate viewpoint changes.

**What does Lowe's ratio test do?** It rejects ambiguous descriptors when the
nearest candidate is not sufficiently better than the second nearest. Mutual
matching additionally requires the reverse match to agree.

**Why RANSAC?** Some descriptor matches are wrong. RANSAC fits geometry to small
samples and scores consensus, reducing the influence of these outliers.

**What is the essential matrix?** For calibrated normalized coordinates,
`x2.T @ E @ x1 = 0`, with `E = [t]_cross @ R`. It constrains a match to an
epipolar line and supports relative pose recovery up to translation scale.

**How is the correct pose selected?** Essential-matrix decomposition gives two
rotations and two translation signs. Triangulate inliers under all candidates
and select the one with the most points in front of both cameras (cheirality).

**Why can depth still be wrong with low reprojection error?** Small-baseline or
nearly parallel viewing rays constrain depth poorly. Several distant 3D points
can explain almost the same image observations. The actual ETH3D results show
why residual-only quality claims are insufficient.

**How are camera centers calculated?** From world-to-camera `Xc = R Xw + t`,
set `Xc = 0` to obtain `C = -R.T @ t`. The translation vector itself is not
the camera position.

**How is a track different from a match?** A match links two keypoints. A track
represents one scene point across multiple images. Our merge rejects tracks
that would include two different keypoints from the same image.

**What does PnP estimate?** A new camera's world-to-camera pose from existing
3D points and their 2D observations. PnP-RANSAC rejects incorrect correspondences,
then nonlinear pose refinement uses the inliers.

**What does bundle adjustment optimize?** Pixel residuals across registered
camera poses and 3D points, with fixed intrinsics. This implementation uses
robust soft-L1 loss and sparse Jacobian structure. Final minimal-gauge BA fixes
the first pose and seed baseline length, while allowing the second seed pose
to improve. The earlier two-fixed-pose optimizer remains a reproducible option.

**What is the proposed contribution?** V2 ranks continuous conditional positional
uncertainty from projection Jacobians and residual variance, then reserves
spatial representatives within a fixed 80% point budget. Geometry and distinct
view support enter the information matrix. Matched-count and coverage-matched
controls isolate its effects. It is a measured combination of established ideas.

**Why report count-matched controls?** Throwing away more points can make average
error look better. Keeping exactly the combined filter's point budget compares
ranking quality without that point-count advantage.

**Why is two-view support not informative?** Every reconstructed point has two
observations. More-view support becomes useful only after track formation and
camera registration; the support filter's minimum of three gives an empty
two-view result by design in V1. V2 uses a fixed budget and does not require
three observations, so it also produces nonempty two-view selections.

**How is monocular scale handled?** The estimated seed baseline is one arbitrary
unit. Evaluation alone uses calibrated stereo baseline or camera-pose similarity
alignment to compare against metric ground truth.

**What are the main limitations?** Exploratory training scenes, no native full
resolution or full rig optimization, fixed-camera conditional uncertainty, no dense MVS,
no COLMAP numerical benchmark, approximate sampled-scan diagnostics, and no
visibility-aware official ETH3D completeness scores.

**What improved in the final study?** At a fixed 80% budget, 9/11 eligible V2
held-out multi-view subsets had lower median sampled-scan distance, averaging
11.96% relative reduction versus all points. Against equal-budget residual
ranking the mean reduction was 6.46%, with 6/11 wins. The synthetic noise study
showed 29.64% reduction versus all points over ten seeds. Read FINAL_RESULTS.md
for failures, the exact split and prior V1 scene exposure.

**Does this prove field-level novelty?** No. It supports this implemented
error-coverage tradeoff under documented assumptions. Covariance and coverage
selection are established ideas, some scenes regress, and pose bias remains
outside the conditional model.

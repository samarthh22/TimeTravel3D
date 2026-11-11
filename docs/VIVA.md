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
robust soft-L1 loss and sparse Jacobian structure. Two seed poses remain fixed,
so their initial relative-pose errors cannot be corrected by this constrained BA.

**What is the proposed contribution?** A configurable geometric confidence rule
and controlled ablations. It combines residual, ray angle, and distinct-image
support. The constituent signals are established ideas. We report what the
combination actually does without claiming it is a new general SfM algorithm.

**Why report count-matched controls?** Throwing away more points can make average
error look better. Keeping exactly the combined filter's point budget compares
ranking quality without that point-count advantage.

**Why is two-view support not informative?** Every reconstructed point has two
observations. More-view support becomes useful only after track formation and
camera registration; the support filter's minimum of three gives an empty
two-view result by design.

**How is monocular scale handled?** The estimated seed baseline is one arbitrary
unit. Evaluation alone uses calibrated stereo baseline or camera-pose similarity
alignment to compare against metric ground truth.

**What are the main limitations?** Exploratory training scenes, no native full
resolution or full rig optimization, constrained seed poses in BA, no dense MVS,
no COLMAP numerical benchmark, approximate sampled-scan diagnostics, and no
visibility-aware official ETH3D completeness scores.

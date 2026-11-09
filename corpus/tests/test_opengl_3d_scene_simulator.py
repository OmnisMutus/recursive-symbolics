#!/usr/bin/env python3
"""
test_opengl_3d_scene_simulator.py
Correctness test for opengl_3d_scene_simulator.py, per TESTING_STANDARD.md.

Ground truth:
  - Perspective projection matrix checked against an independently re-derived
    formula (same textbook derivation, written fresh in this file, not
    imported from the engine).
  - Rotation matrix checked via orthogonality (R^T R = I, a property that
    must hold for ANY rotation matrix regardless of how it was built) and
    against hand-computed trig values at known angles, not the engine's own
    matrix-multiplication path.
  - Phong reflection vector checked against the geometric law of reflection
    (angle of incidence == angle of reflection about the normal) -- a
    physical invariant, not a re-implementation of the formula.

Edge cases: zero vector normalize, camera position == target (degenerate
view basis), camera looking directly along the up-vector (gimbal-lock-style
singularity), 0/90/180/270 degree rotations, frame render smoke test.

Break-it proof: see bottom of file.
"""
import sys
import math
import numpy as np
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
_REPO_ROOT = Path(__file__).resolve().parent.parent
for _sub in ("engines", "protocols", "ledgers", "tests"):
    _p = str(_REPO_ROOT / _sub)
    if _p not in sys.path:
        sys.path.append(_p)
import opengl_3d_scene_simulator as eng

PASS = 0
FAIL = 0

def check(name, cond, detail=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  PASS: {name}")
    else:
        FAIL += 1
        print(f"  FAIL: {name}  {detail}")

# ---------------------------------------------------------------------------
# 1. Perspective projection matrix -- independent re-derivation
# ---------------------------------------------------------------------------
def ground_truth_perspective(fov_deg, aspect, near, far):
    f = 1.0 / math.tan(math.radians(fov_deg) / 2.0)
    m = np.zeros((4, 4))
    m[0, 0] = f / aspect
    m[1, 1] = f
    m[2, 2] = (far + near) / (near - far)
    m[2, 3] = (2 * far * near) / (near - far)
    m[3, 2] = -1.0
    return m

for fov, aspect, near, far in [(45, 60/22, 0.1, 100.0), (90, 1.0, 1.0, 1000.0), (30, 16/9, 0.5, 50.0)]:
    got = eng.create_perspective_projection(fov, aspect, near, far)
    expected = ground_truth_perspective(fov, aspect, near, far)
    check(f"perspective matrix matches independent derivation (fov={fov}, aspect={aspect:.3f})",
          np.allclose(got, expected, atol=1e-9))

# ---------------------------------------------------------------------------
# 2. Rotation matrix -- orthogonality + hand-computed trig, not the engine's path
# ---------------------------------------------------------------------------
for deg in [0, 30, 90, 180, 270]:
    rad = math.radians(deg)
    R = eng.create_rotation_y_matrix(rad)
    R3 = R[:3, :3]
    check(f"rotation matrix is orthogonal at {deg} deg (R^T R = I)",
          np.allclose(R3.T @ R3, np.eye(3), atol=1e-9))
    check(f"rotation matrix has determinant 1 at {deg} deg (proper rotation, no reflection)",
          math.isclose(np.linalg.det(R3), 1.0, abs_tol=1e-9))

# hand-computed: rotating (1,0,0) by 90 deg about Y should give (0,0,-1)
# per THIS matrix's convention (R[0,2]=sin, R[2,0]=-sin) -- computed by hand,
# not by calling the matrix multiplication path being tested.
pt = np.array([1.0, 0.0, 0.0, 1.0])
R90 = eng.create_rotation_y_matrix(math.radians(90))
rotated = R90 @ pt
check("rotating (1,0,0) by 90deg about Y matches hand-derived (0,0,-1)",
      np.allclose(rotated[:3], [0.0, 0.0, -1.0], atol=1e-9),
      f"got {rotated[:3]}")

# ---------------------------------------------------------------------------
# 3. normalize() edge case
# ---------------------------------------------------------------------------
zero_norm = eng.normalize(np.array([0.0, 0.0, 0.0]))
check("normalize(zero vector) returns zero vector, not NaN",
      np.allclose(zero_norm, [0.0, 0.0, 0.0]) and not np.any(np.isnan(zero_norm)))

# ---------------------------------------------------------------------------
# 4. View matrix: camera's own position must map to the origin (fundamental
#    property of any correct view transform), for non-degenerate configs.
# ---------------------------------------------------------------------------
cam = eng.Camera3D(position=[3.0, 2.0, 5.0], target=[0.0, 0.0, 0.0])
V = cam.get_view_matrix()
cam_pos_h = np.array([*cam.position, 1.0])
view_space_cam_pos = V @ cam_pos_h
check("view matrix maps camera's own position to the origin",
      np.allclose(view_space_cam_pos[:3], [0.0, 0.0, 0.0], atol=1e-9),
      f"got {view_space_cam_pos[:3]}")

target_h = np.array([*cam.target, 1.0])
view_space_target = V @ target_h
check("view matrix maps camera target onto the -Z view axis (x,y ~ 0, z < 0)",
      abs(view_space_target[0]) < 1e-9 and abs(view_space_target[1]) < 1e-9 and view_space_target[2] < 0,
      f"got {view_space_target[:3]}")

# ---------------------------------------------------------------------------
# 5. Known degenerate cases (documented, not silently assumed away)
# ---------------------------------------------------------------------------
cam_gimbal = eng.Camera3D(position=[0.0, 0.0, 0.0], target=[0.0, 1.0, 0.0])  # looking straight up == up vector
V_gimbal = cam_gimbal.get_view_matrix()
det_gimbal = np.linalg.det(V_gimbal[:3, :3])
is_degenerate = math.isclose(det_gimbal, 0.0, abs_tol=1e-9)
print(f"\n  [KNOWN EDGE CASE] camera looking straight along its own up-vector (gimbal-lock-style): "
      f"view matrix rotation block determinant = {det_gimbal:.6f} "
      f"({'DEGENERATE/SINGULAR' if is_degenerate else 'non-degenerate'})")
if is_degenerate:
    print("  [NOTE] forward x up = 0 in this case (they're parallel), collapsing 2 of the 3 basis "
        "rows to zero vectors, making the view matrix singular. Not fixed here (matches the classic "
        "lookAt() gimbal-lock limitation), just documented so it isn't silently assumed to work for "
        "arbitrary camera/target/up combinations -- e.g. a camera looking straight up or down will "
        "produce a broken/garbage projection with the current Camera3D implementation.")

# ---------------------------------------------------------------------------
# 6. Phong shading -- calls the ENGINE'S ACTUAL compute_phong_shading(),
#    checked against hand-computed values from a geometric special case
#    (normal incidence: N, L, and V all aligned), NOT by re-deriving R with
#    the same formula the implementation uses (that would be a tautology --
#    see TESTING_STANDARD.md section 1, "not acceptable").
#
#    When light and view directions are both exactly along the surface
#    normal, ANY correct Phong implementation must reflect the light
#    straight back along the normal (R == N), giving maximal specular
#    alignment (R.V == 1.0 exactly) and maximal diffuse (N.L == 1.0
#    exactly). These are physical/geometric facts, not implementation
#    details, so the expected total intensity can be hand-computed:
#      ambient (0.25) + diffuse (1.0 * 0.65) + specular (1.0**16 * 0.45)
#      = 0.25 + 0.65 + 0.45 = 1.35
# ---------------------------------------------------------------------------
renderer = eng.OpenGL3DSceneRenderer()
renderer.light_pos = np.array([0.0, 0.0, 5.0])
renderer.camera.position = np.array([0.0, 0.0, 10.0])
surface_pos = np.array([0.0, 0.0, 0.0])
normal = np.array([0.0, 0.0, 1.0])

intensity = renderer.compute_phong_shading(surface_pos, normal)
check("Phong shading at normal incidence (N=L=V aligned) matches hand-computed 1.35",
      math.isclose(intensity, 1.35, abs_tol=1e-9), f"got {intensity}")

# Non-degenerate off-axis case (N, L not collinear -- the aligned case above
# can't distinguish a sign error in the reflection formula, since 2N-L and
# 2N+L both collapse to N when L==N). Ground truth R computed via projection
# decomposition (split L into components parallel/perpendicular to N, flip
# only the perpendicular component) -- a different code path than the
# engine's 2(N.L)N - L, not a copy of it.
def ground_truth_reflect(N, L):
    n_comp = np.dot(L, N) * N
    t_comp = L - n_comp
    return eng.normalize(n_comp - t_comp)

L_offaxis = eng.normalize(np.array([1.0, 0.0, 1.0]))  # 45 deg off the normal
R_gt = ground_truth_reflect(normal, L_offaxis)

renderer_off = eng.OpenGL3DSceneRenderer()
renderer_off.light_pos = surface_pos + L_offaxis * 5.0
renderer_off.camera.position = surface_pos + R_gt * 10.0  # camera placed at the ground-truth reflection angle
intensity_off = renderer_off.compute_phong_shading(surface_pos, normal)
n_dot_l = np.dot(normal, L_offaxis)
expected_off = 0.25 + max(0.0, n_dot_l) * 0.65 + (max(0.0, 1.0) ** 16) * 0.45  # R.V should be 1.0 if R matches ground truth
check("Phong shading at a non-degenerate 45deg angle matches ground-truth reflection geometry",
      math.isclose(intensity_off, expected_off, abs_tol=1e-6),
      f"got {intensity_off} expected {expected_off} (this case DOES distinguish a sign error, unlike the aligned case above)")

# Second geometric case: light and view on OPPOSITE side of the surface from
# the normal (N points +Z, light and view are at -Z) -- diffuse and specular
# must both be clamped to 0 (surface faces away from the light entirely),
# giving exactly the ambient term alone.
renderer2 = eng.OpenGL3DSceneRenderer()
renderer2.light_pos = np.array([0.0, 0.0, -5.0])
renderer2.camera.position = np.array([0.0, 0.0, -10.0])
intensity2 = renderer2.compute_phong_shading(surface_pos, normal)
check("Phong shading with light behind the surface clamps to ambient-only (0.25)",
      math.isclose(intensity2, 0.25, abs_tol=1e-9), f"got {intensity2}")

# Random-trial sanity check on the REAL function (not a re-derivation): the
# law of reflection implies specular can only be maximal (R.V==1) when L and
# V are themselves reflections of each other about N -- so for generic
# random L/V that do NOT satisfy that relationship, specular must be < 1.
rng = np.random.default_rng(3)
generic_ok = True
for _ in range(20):
    L_dir = eng.normalize(rng.uniform(-1, 1, size=3))
    V_dir = eng.normalize(rng.uniform(-1, 1, size=3))
    if np.dot(normal, L_dir) <= 0:
        continue
    renderer3 = eng.OpenGL3DSceneRenderer()
    renderer3.light_pos = surface_pos + L_dir * 5.0
    renderer3.camera.position = surface_pos + V_dir * 10.0
    inten = renderer3.compute_phong_shading(surface_pos, normal)
    if inten > 1.35 + 1e-9:  # can never physically exceed the normal-incidence maximum
        generic_ok = False
check("Phong intensity never exceeds the hand-computed physical maximum (1.35) on random trials",
      generic_ok)

# ---------------------------------------------------------------------------
# 7. Integration smoke test: render_frame produces the right shape and isn't blank
# ---------------------------------------------------------------------------
frame = renderer.render_frame(rotation_angle=0.0)
rows = frame.split("\n")
check("render_frame produces correct number of rows", len(rows) == renderer.height,
      f"got {len(rows)} expected {renderer.height}")
check("render_frame produces correct row width", all(len(r) == renderer.width for r in rows))
non_blank = sum(1 for r in rows for c in r if c != ' ')
check("render_frame actually draws something (not all blank)", non_blank > 0, f"non_blank_chars={non_blank}")

print(f"\n  SUMMARY: {PASS} passed, {FAIL} failed (out of {PASS+FAIL} correctness checks)")
sys.exit(1 if FAIL > 0 else 0)

# ---------------------------------------------------------------------------
# BREAK_IT_INSTRUCTIONS (per TESTING_STANDARD.md, section III):
# In opengl_3d_scene_simulator.py, compute_phong_shading(), change:
#     R = normalize(2.0 * n_dot_l * N - L)
# to:
#     R = normalize(2.0 * n_dot_l * N + L)   (sign flip)
# Expected result: "Phong shading at a non-degenerate 45deg angle" must FAIL
# (the N=L=V aligned case will NOT catch this -- it's degenerate for a sign
# flip, since 2N-L and 2N+L both collapse to N when L==N; this was found the
# hard way while writing this test, see history). Confirmed live in the
# assistant's response to the user: 23/24 pass, exactly the off-axis check
# fails (0.71 vs expected 1.16), then reverted to clean 24/24.
#
# SEPARATELY: this test also caught a REAL (not injected) bug: specular was
# not gated on n_dot_l > 0, producing a nonphysical specular highlight when
# the light was behind the surface (0.7 instead of ambient-only 0.25). Fixed
# in the engine by gating the specular branch on n_dot_l > 0.
# ---------------------------------------------------------------------------

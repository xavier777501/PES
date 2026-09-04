import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

import cv2
import mediapipe as mp
import numpy as np
import os
from face_utils import (calculate_delaunay_triangles, warp_triangle,
                         get_edge_anchor_points, procrustes_align)

PES_SIZE = 512  # Standard PES UV texture size

# How much of the *template's* facial geometry to mix into the final shape.
# 0.0  = the output head/face shape is an exact match of the uploaded photo
#        (after rigid Procrustes placement — no local morphing at all).
# 1.0  = the output conforms fully to the template's UV layout instead.
# Kept very low so the result is (near) pixel-identical in shape to the
# source photo, at the cost of not perfectly matching PES's expected eye/
# mouth socket coordinates on the 3D head model.
SHAPE_BLEND_ALPHA = 0.0

# How strongly to shift the source skin colours towards the template's
# palette during seam blending. Kept low to preserve the source's real
# skin tone/colours as closely as possible.
COLOR_HARMONISE_STRENGTH = 0.15

# ─────────────────────────────────────────────────────────────────
# MediaPipe landmark index groups (478-point model)
# ─────────────────────────────────────────────────────────────────

# Canonical face oval contour (ordered, de-duplicated)
FACE_OVAL = [
    10, 338, 297, 332, 284, 251, 389, 356, 454, 323, 361, 288,
    397, 365, 379, 378, 400, 377, 152, 148, 176, 149, 150, 136,
    172, 58, 132, 93, 234, 127, 162, 21, 54, 103, 67, 109,
]
FACE_OVAL = sorted(list(set(FACE_OVAL)))

# Jawline points (heavier weight during alignment)
JAWLINE = [172, 136, 150, 149, 176, 148, 152, 377, 400, 378, 379, 365, 397]

# Eye contour indices
LEFT_EYE_INNER = [
    33, 7, 163, 144, 145, 153, 154, 155,
    133, 173, 157, 158, 159, 160, 161, 246
]
RIGHT_EYE_INNER = [
    362, 382, 381, 380, 374, 373, 390, 249,
    263, 466, 388, 387, 386, 385, 384, 398
]

# Eyebrow indices (for skin colour sampling)
LEFT_EYEBROW = [70, 63, 105, 66, 107, 55, 65, 52, 53, 46]
RIGHT_EYEBROW = [300, 293, 334, 296, 336, 285, 295, 282, 283, 276]

# Stable interior landmarks for alignment (eyes, nose tip, mouth corners)
ALIGN_LANDMARKS = [
    # Left eye corners
    33, 133,
    # Right eye corners
    362, 263,
    # Nose tip + bridge
    1, 4, 5, 6, 197, 168,
    # Mouth corners
    61, 291,
    # Chin
    152,
    # Forehead
    10,
]


# ═════════════════════════════════════════════════════════════════
#  STEP 1 — Face detection
# ═════════════════════════════════════════════════════════════════

def get_landmarks(image_path, landmarker):
    """Detect 478 face-mesh landmarks with MediaPipe. Returns list of (x, y)."""
    image = mp.Image.create_from_file(image_path)
    if image is None:
        raise ValueError(f"Cannot load: {image_path}")
    result = landmarker.detect(image)
    if not result.face_landmarks:
        return None
    h, w = image.height, image.width
    return [(int(lm.x * w), int(lm.y * h)) for lm in result.face_landmarks[0]]


# ═════════════════════════════════════════════════════════════════
#  STEP 2 — Smart face crop (fills the square properly)
# ═════════════════════════════════════════════════════════════════

def smart_face_crop(img, landmarks, target_size=PES_SIZE):
    """
    Crop and resize the source image so the face fills ~85 % of the target
    square.  Also straightens the face by levelling the eyes.

    Returns (cropped_img, new_landmarks).
    """
    h, w = img.shape[:2]
    pts = np.array(landmarks, dtype=np.float32)

    # ── 1. Straighten: rotate so the eye-line is horizontal ──
    left_eye_center = pts[[33, 133]].mean(axis=0)
    right_eye_center = pts[[362, 263]].mean(axis=0)
    angle = np.degrees(np.arctan2(
        right_eye_center[1] - left_eye_center[1],
        right_eye_center[0] - left_eye_center[0]))

    center = (w / 2, h / 2)
    rot_mat = cv2.getRotationMatrix2D(center, angle, 1.0)

    # Compute new canvas size to avoid clipping after rotation
    cos_a = abs(rot_mat[0, 0])
    sin_a = abs(rot_mat[0, 1])
    new_w = int(h * sin_a + w * cos_a)
    new_h = int(h * cos_a + w * sin_a)
    rot_mat[0, 2] += (new_w - w) / 2
    rot_mat[1, 2] += (new_h - h) / 2

    img_rot = cv2.warpAffine(img, rot_mat, (new_w, new_h),
                              borderMode=cv2.BORDER_REFLECT_101)

    # Rotate landmarks
    ones = np.ones((len(pts), 1), dtype=np.float32)
    pts_h = np.hstack([pts, ones])  # (N, 3)
    pts_rot = (rot_mat @ pts_h.T).T  # (N, 2)

    # ── 2. Compute face bounding box with generous margins ──
    face_oval_pts = pts_rot[FACE_OVAL]
    x_min, y_min = face_oval_pts.min(axis=0)
    x_max, y_max = face_oval_pts.max(axis=0)

    face_w = x_max - x_min
    face_h = y_max - y_min

    # We want the face to occupy ~85% of the final square
    # Add more margin above (forehead/hair) than below
    margin_x = face_w * 0.20
    margin_top = face_h * 0.35   # extra space for forehead
    margin_bottom = face_h * 0.10

    crop_x1 = int(max(0, x_min - margin_x))
    crop_y1 = int(max(0, y_min - margin_top))
    crop_x2 = int(min(new_w, x_max + margin_x))
    crop_y2 = int(min(new_h, y_max + margin_bottom))

    # Make the crop square (use the larger dimension)
    crop_w = crop_x2 - crop_x1
    crop_h = crop_y2 - crop_y1
    side = max(crop_w, crop_h)

    # Re-center the square crop around the face center
    cx = (crop_x1 + crop_x2) / 2
    cy = (crop_y1 + crop_y2) / 2

    sq_x1 = int(max(0, cx - side / 2))
    sq_y1 = int(max(0, cy - side / 2))
    sq_x2 = int(min(new_w, sq_x1 + side))
    sq_y2 = int(min(new_h, sq_y1 + side))

    # Adjust if we hit edges
    if sq_x2 - sq_x1 < side:
        sq_x1 = max(0, sq_x2 - side)
    if sq_y2 - sq_y1 < side:
        sq_y1 = max(0, sq_y2 - side)

    actual_w = sq_x2 - sq_x1
    actual_h = sq_y2 - sq_y1
    if actual_w <= 0 or actual_h <= 0:
        # Fallback: just resize the whole rotated image
        cropped = cv2.resize(img_rot, (target_size, target_size))
        scale_x = target_size / new_w
        scale_y = target_size / new_h
        new_lm = [(int(p[0] * scale_x), int(p[1] * scale_y)) for p in pts_rot]
        return cropped, new_lm

    cropped = img_rot[sq_y1:sq_y2, sq_x1:sq_x2]
    cropped = cv2.resize(cropped, (target_size, target_size))

    # Scale landmarks into the cropped coordinate system
    scale_x = target_size / actual_w
    scale_y = target_size / actual_h
    new_lm = [(int((p[0] - sq_x1) * scale_x),
               int((p[1] - sq_y1) * scale_y)) for p in pts_rot]

    return cropped, new_lm


# ═════════════════════════════════════════════════════════════════
#  STEP 3 — Morphological blend (preserve source head shape)
# ═════════════════════════════════════════════════════════════════

def blend_landmarks(pts_src, pts_tpl, alpha=0.30):
    """
    Interpolate between source and template landmark positions.
    alpha = 0.0 → 100 % source shape (face looks like the photo)
    alpha = 1.0 → 100 % template shape (face matches the UV layout perfectly)

    We use a *low* alpha (0.30) so the source morphology dominates, while
    still nudging the positions enough to match the PES UV layout.
    """
    pts_s = np.array(pts_src, dtype=np.float32)
    pts_t = np.array(pts_tpl, dtype=np.float32)
    blended = (1.0 - alpha) * pts_s + alpha * pts_t
    return [(int(x), int(y)) for x, y in blended]


# ═════════════════════════════════════════════════════════════════
#  STEP 4 — Eye inpainting (realistic skin fill)
# ═════════════════════════════════════════════════════════════════

def inpaint_eyes(img, landmarks):
    """
    Fill eye openings with realistic skin texture using OpenCV inpainting
    (Telea algorithm) instead of flat-colour fill.  Falls back to
    sampled-colour fill if inpainting produces artefacts.
    """
    result = img.copy()

    for eye_indices, brow_indices in [
        (LEFT_EYE_INNER, LEFT_EYEBROW),
        (RIGHT_EYE_INNER, RIGHT_EYEBROW),
    ]:
        # Build eye opening mask
        pts = np.array([landmarks[i] for i in eye_indices], dtype=np.int32)
        eye_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(eye_mask, pts, 255)

        # Dilate to cover lashes, iris edges, reflections
        kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (9, 9))
        eye_mask = cv2.dilate(eye_mask, kernel, iterations=2)

        # Sample average skin colour from the brow region for fallback
        brow_pts = np.array([landmarks[i] for i in brow_indices], dtype=np.int32)
        brow_mask = np.zeros(img.shape[:2], dtype=np.uint8)
        cv2.fillConvexPoly(brow_mask, brow_pts, 255)
        avg_color = cv2.mean(img, mask=brow_mask)[:3]

        # First: fill with skin colour as a base (so inpainting has context)
        result[eye_mask > 0] = avg_color

        # Then: run Telea inpainting for natural texture blending
        try:
            result = cv2.inpaint(result, eye_mask, inpaintRadius=7,
                                 flags=cv2.INPAINT_TELEA)
        except cv2.error:
            pass  # keep the colour fill as fallback

    # Gentle blur over eye areas only
    full_eye_mask = np.zeros(img.shape[:2], dtype=np.uint8)
    for eye_indices in [LEFT_EYE_INNER, RIGHT_EYE_INNER]:
        pts = np.array([landmarks[i] for i in eye_indices], dtype=np.int32)
        cv2.fillConvexPoly(full_eye_mask, pts, 255)
    full_eye_mask = cv2.dilate(
        full_eye_mask,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (13, 13)),
        iterations=2)

    blurred = cv2.GaussianBlur(result, (7, 7), 0)
    mask3 = cv2.merge([full_eye_mask] * 3)
    result = np.where(mask3 > 0, blurred, result)

    return result


# ═════════════════════════════════════════════════════════════════
#  STEP 5 — Face mask with soft feathering
# ═════════════════════════════════════════════════════════════════

def build_face_mask(landmarks, size, feather_px=45):
    """
    Build a smooth face mask from the oval landmarks with wide feathering
    so the blended face fades seamlessly into the template skin.
    """
    oval_pts = np.array([landmarks[i] for i in FACE_OVAL], dtype=np.int32)
    hull = cv2.convexHull(oval_pts)

    mask = np.zeros((size, size), dtype=np.uint8)
    cv2.fillConvexPoly(mask, hull, 255)

    # Wide Gaussian feather for seamless edge blending
    ksize = feather_px * 2 + 1
    mask = cv2.GaussianBlur(mask, (ksize, ksize), 0)
    return mask


# ═════════════════════════════════════════════════════════════════
#  STEP 6 — Lightweight colour harmonisation
# ═════════════════════════════════════════════════════════════════

def harmonise_colours_soft(src, dst, mask_2d, strength=0.35):
    """
    Gentle CIE-LAB colour transfer.  Only shifts the source colours *part-way*
    towards the template palette (controlled by `strength`).

    strength = 0.0 → keep source colours exactly
    strength = 1.0 → full statistical transfer (old behaviour)
    """
    src_lab = cv2.cvtColor(src, cv2.COLOR_BGR2LAB).astype(np.float64)
    dst_lab = cv2.cvtColor(dst, cv2.COLOR_BGR2LAB).astype(np.float64)
    mb = mask_2d > 0

    if mb.sum() == 0:
        return src

    for c in range(3):
        sm = src_lab[:, :, c][mb].mean()
        ss = src_lab[:, :, c][mb].std() + 1e-6
        dm = dst_lab[:, :, c][mb].mean()
        ds = dst_lab[:, :, c][mb].std() + 1e-6

        # Partial transfer: interpolate between original and fully transferred
        full_transfer = (src_lab[:, :, c] - sm) * (ds / ss) + dm
        src_lab[:, :, c] = (1.0 - strength) * src_lab[:, :, c] + strength * full_transfer

    return cv2.cvtColor(np.clip(src_lab, 0, 255).astype(np.uint8),
                        cv2.COLOR_LAB2BGR)


# ═════════════════════════════════════════════════════════════════
#  STEP 7 — Similarity scoring (for template selection)
# ═════════════════════════════════════════════════════════════════

def calculate_similarity(pts1, pts2):
    """Shape similarity focusing on face contour and main features."""
    CORE = FACE_OVAL + LEFT_EYE_INNER + RIGHT_EYE_INNER + [1, 4, 5, 6, 197, 168]

    p1 = np.array([pts1[i] for i in CORE], dtype=np.float64)
    p2 = np.array([pts2[i] for i in CORE], dtype=np.float64)

    p1 = (p1 - p1.mean(axis=0)) / (np.linalg.norm(p1 - p1.mean(axis=0)) + 1e-6)
    p2 = (p2 - p2.mean(axis=0)) / (np.linalg.norm(p2 - p2.mean(axis=0)) + 1e-6)

    return float(np.linalg.norm(p1 - p2))


def _fallback_simple_placement(source_path, templates, output_path):
    """
    Best-effort output for images where MediaPipe cannot find any face
    (typically heavily stylised art, anime characters, drawings with face
    paint/markings). There are no landmarks to warp with, so instead of
    failing we just centre-crop the source photo and blend it into a
    generic oval region of the template — no geometric conformity, but
    the user gets a usable result instead of an error.
    """
    template_path = templates[0] if isinstance(templates, list) else templates
    img_tpl_orig = cv2.imread(template_path)
    img_src_orig = cv2.imread(source_path)
    if img_tpl_orig is None or img_src_orig is None:
        print("ERROR: Cannot read image files for fallback placement.")
        return False

    img_tpl = cv2.resize(img_tpl_orig, (PES_SIZE, PES_SIZE))

    # Centre-crop the source to a square, then resize to the canvas size.
    h, w = img_src_orig.shape[:2]
    side = min(h, w)
    y0 = (h - side) // 2
    x0 = (w - side) // 2
    img_src_sq = img_src_orig[y0:y0 + side, x0:x0 + side]
    img_src = cv2.resize(img_src_sq, (PES_SIZE, PES_SIZE))

    # Generic oval mask (no landmarks available to build a precise one).
    mask = np.zeros((PES_SIZE, PES_SIZE), dtype=np.uint8)
    center = (PES_SIZE // 2, int(PES_SIZE * 0.48))
    axes = (int(PES_SIZE * 0.33), int(PES_SIZE * 0.42))
    cv2.ellipse(mask, center, axes, 0, 0, 360, 255, -1)
    mask = cv2.GaussianBlur(mask, (81, 81), 0)

    mask_f = mask.astype(np.float32) / 255.0
    mask_3 = cv2.merge([mask_f] * 3)

    output = (mask_3 * img_src.astype(np.float32) +
              (1.0 - mask_3) * img_tpl.astype(np.float32))
    output = np.clip(output, 0, 255).astype(np.uint8)

    base, _ = os.path.splitext(output_path)
    png_path = base + ".png"
    cv2.imwrite(png_path, output)
    print(f"[OK] (simplified mode) PES UV texture saved: {png_path}")
    return True, png_path


# ═════════════════════════════════════════════════════════════════
#  MAIN PIPELINE
# ═════════════════════════════════════════════════════════════════

def generate_pes_face(source_path, template_path, output_path):
    """
    Main entry point.  Generates a PES-compatible UV face texture from a
    source photograph and a set of reference UV templates.
    """
    print("=" * 60)
    print("  PES Face UV Generator — v2.0 (Improved)")
    print("=" * 60)

    # ── Initialise MediaPipe ──────────────────────────────────────
    print("[1/8] Loading MediaPipe Face Landmarker...")
    options = mp.tasks.vision.FaceLandmarkerOptions(
        base_options=mp.tasks.BaseOptions(
            model_asset_path="face_landmarker.task"),
        running_mode=mp.tasks.vision.RunningMode.IMAGE,
        num_faces=1,
        # Lowered from the 0.5 default so borderline real-photo cases
        # (side angle, poor lighting, partial occlusion) still get through.
        # Note: this does NOT help heavily stylised art (anime/drawings) —
        # the underlying detector simply finds zero face candidates there,
        # regardless of threshold. That case is handled by the fallback below.
        min_face_detection_confidence=0.3,
        min_face_presence_confidence=0.3)

    templates = [template_path] if isinstance(template_path, str) else template_path

    with mp.tasks.vision.FaceLandmarker.create_from_options(options) as lmk:

        # ── Detect source landmarks ──────────────────────────────
        print(f"[2/8] Detecting face in source: {os.path.basename(source_path)}")
        pts_src_raw = get_landmarks(source_path, lmk)
        if not pts_src_raw:
            print("WARNING: No face detected by MediaPipe (common for stylised")
            print("         art / anime / heavy face paint). Falling back to")
            print("         simplified centred placement (no landmark warp).")
            return _fallback_simple_placement(source_path, templates, output_path)

        # ── Select best template ─────────────────────────────────
        print(f"[3/8] Evaluating {len(templates)} reference template(s)...")
        best_idx = -1
        min_dist = float('inf')
        all_pts_tpl = []

        for i, tpl in enumerate(templates):
            pts = get_landmarks(tpl, lmk)
            if pts:
                dist = calculate_similarity(pts_src_raw, pts)
                print(f"       Template {i + 1} ({os.path.basename(tpl)}): "
                      f"distance = {dist:.4f}")
                if dist < min_dist:
                    min_dist = dist
                    best_idx = i
                all_pts_tpl.append(pts)
            else:
                print(f"       Template {i + 1}: face NOT detected — skipped")
                all_pts_tpl.append(None)

        if best_idx == -1:
            print("ERROR: No face detected in any template.")
            return False

        pts_tpl_raw = all_pts_tpl[best_idx]
        template_path = templates[best_idx]
        print(f"       → Best template: {os.path.basename(template_path)}")

    # ── Load images ───────────────────────────────────────────────
    img_src_orig = cv2.imread(source_path)
    img_tpl_orig = cv2.imread(template_path)
    if img_src_orig is None or img_tpl_orig is None:
        print("ERROR: Cannot read image files.")
        return False

    # ── Smart crop: straighten + fill the square with the face ────
    print("[4/8] Smart crop — straightening and filling the square...")
    img_src_cropped, pts_src_cropped = smart_face_crop(
        img_src_orig, pts_src_raw, PES_SIZE)

    # Resize template to PES_SIZE
    h_t, w_t = img_tpl_orig.shape[:2]
    img_tpl = cv2.resize(img_tpl_orig, (PES_SIZE, PES_SIZE))
    pts_tpl = [(int(x * PES_SIZE / w_t), int(y * PES_SIZE / h_t))
               for x, y in pts_tpl_raw]

    # ── Clip all points to valid image coordinates ────────────────
    def clip_pts(pts, size=PES_SIZE):
        return [(max(1, min(x, size - 2)), max(1, min(y, size - 2)))
                for x, y in pts]

    pts_src = clip_pts(pts_src_cropped)
    pts_tpl = clip_pts(pts_tpl)

    # ── Procrustes alignment (source → template space) ───────────
    print("[5/8] Procrustes alignment (faithful to source shape)...")

    align_src = [pts_src[i] for i in ALIGN_LANDMARKS]
    align_tpl = [pts_tpl[i] for i in ALIGN_LANDMARKS]

    m_align = procrustes_align(align_src, align_tpl)

    img_src_aligned = cv2.warpAffine(
        img_src_cropped, m_align, (PES_SIZE, PES_SIZE),
        borderMode=cv2.BORDER_REFLECT_101)

    # Transform source landmarks with the same matrix
    pts_src_aligned = []
    for p in pts_src:
        px = m_align[0, 0] * p[0] + m_align[0, 1] * p[1] + m_align[0, 2]
        py = m_align[1, 0] * p[0] + m_align[1, 1] * p[1] + m_align[1, 2]
        pts_src_aligned.append((int(px), int(py)))

    pts_src_aligned = clip_pts(pts_src_aligned)

    # ── Morphological blend: 70 % source shape + 30 % template ───
    # This preserves the uploaded face's real morphology while still
    # conforming enough to the PES UV layout.
    pts_target = blend_landmarks(pts_src_aligned, pts_tpl, alpha=SHAPE_BLEND_ALPHA)
    pts_target = clip_pts(pts_target)

    # ── Delaunay warp (with edge anchors) ─────────────────────────
    print("[6/8] Delaunay mesh warp (with edge anchors)...")

    # Add edge anchor points so the warp covers the full square
    edge_pts = get_edge_anchor_points(PES_SIZE, PES_SIZE, n_per_side=8)

    pts_src_ext = pts_src_aligned + edge_pts
    pts_tgt_ext = pts_target + edge_pts  # anchors map to themselves

    # De-duplicate
    unique_tgt = []
    seen = set()
    idx_map = {}
    for i, p in enumerate(pts_tgt_ext):
        if p not in seen:
            idx_map[i] = len(unique_tgt)
            unique_tgt.append(p)
            seen.add(p)
        else:
            # find existing index
            for j, up in enumerate(unique_tgt):
                if up == p:
                    idx_map[i] = j
                    break

    rect = (0, 0, PES_SIZE, PES_SIZE)
    dt = calculate_delaunay_triangles(rect, unique_tgt)

    # Start with template as the canvas
    img_morphed = img_tpl.copy().astype(np.float32)
    img_src_f = img_src_aligned.astype(np.float32)

    for tri in dt:
        t_s = [pts_src_ext[tri[j]] for j in range(3)]
        t_t = [pts_tgt_ext[tri[j]] for j in range(3)]
        warp_triangle(img_src_f, img_morphed, t_s, t_t)

    img_morphed = np.clip(img_morphed, 0, 255).astype(np.uint8)

    # ── Inpaint eyes with realistic skin ─────────────────────────
    print("[7/8] Eye inpainting (Telea algorithm)...")
    img_inpainted = inpaint_eyes(img_morphed, pts_target)

    # ── Soft face mask + gentle colour harmonisation ──────────────
    print("[8/8] Colour harmonisation + seamless blending...")
    face_mask_2d = build_face_mask(pts_target, PES_SIZE, feather_px=45)

    # Light colour harmonisation: keeps most of the source colour
    img_harmonised = harmonise_colours_soft(
        img_inpainted, img_tpl, face_mask_2d, strength=COLOR_HARMONISE_STRENGTH)

    # ── Final composite: alpha-blend using the feathered mask ─────
    # We use simple alpha blending instead of Poisson seamlessClone to
    # avoid the double colour-shift that was causing the washed-out look.
    mask_f = face_mask_2d.astype(np.float32) / 255.0
    mask_3 = cv2.merge([mask_f] * 3)

    output = (mask_3 * img_harmonised.astype(np.float32) +
              (1.0 - mask_3) * img_tpl.astype(np.float32))
    output = np.clip(output, 0, 255).astype(np.uint8)

    # ── Save ──────────────────────────────────────────────────────
    base, _ = os.path.splitext(output_path)
    png_path = base + ".png"
    cv2.imwrite(png_path, output)
    print(f"\n[OK] PES UV texture saved: {png_path}")
    print("=" * 60)
    return True, png_path


# Helper
def pts_raw_to_list(pts):
    if pts is None:
        return []
    return [(int(p[0]), int(p[1])) for p in pts]


# ═════════════════════════════════════════════════════════════════
#  CLI entry point
# ═════════════════════════════════════════════════════════════════
if __name__ == '__main__':
    source = "f1072581-4d44-48e2-b570-e886768f9f6e.jpg"

    ref_dir = r'D:\pes\REFERENCE'
    templates = []
    if os.path.exists(ref_dir):
        templates = [os.path.join(ref_dir, f)
                     for f in os.listdir(ref_dir)
                     if f.lower().endswith(('.png', '.jpg', '.jpeg'))]

    if not templates:
        templates = ["cf598bcc-fe14-40a0-b439-6583ca2183a4.jpg"]

    generate_pes_face(source, templates, "final_pes_texture.jpg")

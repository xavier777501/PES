import cv2
import numpy as np


def rect_contains(rect, point):
    """Check if a point is inside a rectangle (x, y, w, h)."""
    if point[0] < rect[0] or point[1] < rect[1]:
        return False
    if point[0] > rect[0] + rect[2] or point[1] > rect[1] + rect[3]:
        return False
    return True


def get_edge_anchor_points(w, h, n_per_side=8):
    """
    Generate anchor points along the edges and corners of the image.
    These stabilize the Delaunay triangulation in non-face regions so there
    are no holes or distortion artefacts at the borders.
    """
    pts = []
    # Four corners
    margin = 1
    pts += [(margin, margin), (w - margin, margin),
            (margin, h - margin), (w - margin, h - margin)]
    # Points along edges
    for i in range(1, n_per_side):
        t = i / n_per_side
        pts.append((int(t * w), margin))          # top
        pts.append((int(t * w), h - margin))      # bottom
        pts.append((margin, int(t * h)))           # left
        pts.append((w - margin, int(t * h)))       # right
    return pts


def calculate_delaunay_triangles(rect, points):
    """
    Compute Delaunay triangulation for a set of points.
    Returns a list of (i, j, k) index tuples into the *original* points list.
    Uses an extended subdivision rectangle to avoid Subdiv2D::locate errors.
    """
    padding = 1000
    extended_rect = (-padding, -padding,
                     rect[2] + 2 * padding, rect[3] + 2 * padding)
    subdiv = cv2.Subdiv2D(extended_rect)

    # De-duplicate points (Subdiv2D crashes on exact duplicates)
    unique_points = []
    seen = set()
    for p in points:
        px, py = float(p[0]), float(p[1])
        while (px, py) in seen:
            px += 0.01
            py += 0.01
        unique_points.append((px, py))
        seen.add((px, py))
        subdiv.insert((px, py))

    triangle_list = subdiv.getTriangleList()
    delaunay_tri = []

    for t in triangle_list:
        pts_tri = [(t[0], t[1]), (t[2], t[3]), (t[4], t[5])]
        center_x = (t[0] + t[2] + t[4]) / 3.0
        center_y = (t[1] + t[3] + t[5]) / 3.0

        if rect_contains(rect, (center_x, center_y)):
            try:
                def find_closest_idx(p, original_pts):
                    dists = [(p[0] - x) ** 2 + (p[1] - y) ** 2
                             for x, y in original_pts]
                    return int(np.argmin(dists))

                i1 = find_closest_idx(pts_tri[0], points)
                i2 = find_closest_idx(pts_tri[1], points)
                i3 = find_closest_idx(pts_tri[2], points)

                # Skip degenerate triangles (duplicate indices)
                if i1 != i2 and i2 != i3 and i1 != i3:
                    delaunay_tri.append((i1, i2, i3))
            except Exception:
                continue

    return delaunay_tri


def apply_affine_transform(src, src_tri, dst_tri, size):
    """Apply an affine transform defined by two triangles."""
    warp_mat = cv2.getAffineTransform(np.float32(src_tri), np.float32(dst_tri))
    dst = cv2.warpAffine(src, warp_mat, (size[0], size[1]),
                         None, flags=cv2.INTER_LINEAR,
                         borderMode=cv2.BORDER_REFLECT_101)
    return dst


def warp_triangle(img1, img2, t1, t2):
    """
    Warp a triangular region from img1 to img2 using affine transformation.
    Includes safe boundary clipping so out-of-bounds rectangles don't crash.
    """
    h1, w1 = img1.shape[:2]
    h2, w2 = img2.shape[:2]

    r1 = cv2.boundingRect(np.float32([t1]))
    r2 = cv2.boundingRect(np.float32([t2]))

    # ── Clip bounding rectangles to image boundaries ──
    r1_x2 = min(r1[0] + r1[2], w1)
    r1_y2 = min(r1[1] + r1[3], h1)
    r1 = (max(0, r1[0]), max(0, r1[1]),
          r1_x2 - max(0, r1[0]), r1_y2 - max(0, r1[1]))

    r2_x2 = min(r2[0] + r2[2], w2)
    r2_y2 = min(r2[1] + r2[3], h2)
    r2 = (max(0, r2[0]), max(0, r2[1]),
          r2_x2 - max(0, r2[0]), r2_y2 - max(0, r2[1]))

    # Skip if either rectangle has zero area
    if r1[2] <= 0 or r1[3] <= 0 or r2[2] <= 0 or r2[3] <= 0:
        return

    t1_rect = []
    t2_rect = []
    t2_rect_int = []

    for i in range(3):
        t1_rect.append(((t1[i][0] - r1[0]), (t1[i][1] - r1[1])))
        t2_rect.append(((t2[i][0] - r2[0]), (t2[i][1] - r2[1])))
        t2_rect_int.append(((t2[i][0] - r2[0]), (t2[i][1] - r2[1])))

    mask = np.zeros((r2[3], r2[2], 3), dtype=np.float32)
    cv2.fillConvexPoly(mask, np.int32(t2_rect_int), (1.0, 1.0, 1.0), 16, 0)

    img1_rect = img1[r1[1]:r1[1] + r1[3], r1[0]:r1[0] + r1[2]]
    if img1_rect.size == 0:
        return

    size = (r2[2], r2[3])

    try:
        img2_rect = apply_affine_transform(img1_rect, t1_rect, t2_rect, size)
    except cv2.error:
        return

    img2_rect = img2_rect * mask

    # Safe slice into destination
    y1, y2 = r2[1], r2[1] + r2[3]
    x1, x2 = r2[0], r2[0] + r2[2]
    if y2 > h2 or x2 > w2:
        return

    img2[y1:y2, x1:x2] = img2[y1:y2, x1:x2] * (1.0 - mask) + img2_rect


def warp_image_tps(src, src_pts, dst_pts, size):
    """
    Warp source image to destination geometry using Thin Plate Spline.
    Provides smoother deformation than Delaunay.
    """
    tps = cv2.createThinPlateSplineShapeTransformer()

    s_pts = np.array(src_pts).reshape(1, -1, 2).astype(np.float32)
    d_pts = np.array(dst_pts).reshape(1, -1, 2).astype(np.float32)

    matches = [cv2.DMatch(i, i, 0) for i in range(s_pts.shape[1])]
    tps.estimateTransformation(d_pts, s_pts, matches)

    warped = tps.warpImage(src)
    return warped


def procrustes_align(pts_src, pts_dst):
    """
    Calculate an optimal similarity transform (rotation, scale, translation)
    to align pts_src to pts_dst.  Returns a 2×3 affine matrix.
    """
    pts_src = np.array(pts_src, dtype=np.float64)
    pts_dst = np.array(pts_dst, dtype=np.float64)

    mu_src = pts_src.mean(axis=0)
    mu_dst = pts_dst.mean(axis=0)

    pts_src_c = pts_src - mu_src
    pts_dst_c = pts_dst - mu_dst

    s_src = np.linalg.norm(pts_src_c) / len(pts_src)
    s_dst = np.linalg.norm(pts_dst_c) / len(pts_dst)

    pts_src_c /= (s_src + 1e-8)
    pts_dst_c /= (s_dst + 1e-8)

    u, s, vh = np.linalg.svd(pts_src_c.T @ pts_dst_c)
    r = u @ vh

    s_total = s_dst / (s_src + 1e-8)
    m = np.zeros((2, 3), dtype=np.float64)
    m[:, :2] = s_total * r
    m[:, 2] = mu_dst - s_total * r @ mu_src

    return m

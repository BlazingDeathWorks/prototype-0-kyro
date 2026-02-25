import os
import json
import time
import pathlib
import argparse
import cv2
import numpy as np

IMAGE_PATH_DEFAULT = "/Users/jasonchan/Documents/Programming/Python/Python 3.13/project-kyro/snapshots/gemini_fullpage_20251115_183016.png"

def auto_canny(gray, sigma=0.33):
    v = np.median(gray)
    lower = int(max(0, (1.0 - sigma) * v))
    upper = int(min(255, (1.0 + sigma) * v))
    return cv2.Canny(gray, lower, upper)

def preprocess(img_bgr):
    gray = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2GRAY)
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray = clahe.apply(gray)
    gray = cv2.bilateralFilter(gray, d=7, sigmaColor=50, sigmaSpace=50)
    edges = auto_canny(gray, sigma=0.4)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (5, 5))
    closed = cv2.morphologyEx(edges, cv2.MORPH_CLOSE, kernel, iterations=1)
    grad = cv2.morphologyEx(gray, cv2.MORPH_GRADIENT, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)))
    _, grad_bin = cv2.threshold(grad, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    grad_bin = cv2.morphologyEx(grad_bin, cv2.MORPH_CLOSE, cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3)), iterations=1)
    return gray, closed, grad_bin

def is_gray_border(img_bgr, x, y, w, h):
    if w < 50 or h < 20:
        return False
    H, W = img_bgr.shape[:2]
    x = max(0, min(x, W - 1))
    y = max(0, min(y, H - 1))
    w = max(1, min(w, W - x))
    h = max(1, min(h, H - y))
    bw = max(1, min(3, h // 6))
    top = img_bgr[y:y + bw, x:x + w]
    bottom = img_bgr[y + h - bw:y + h, x:x + w]
    left = img_bgr[y:y + h, x:x + bw]
    right = img_bgr[y:y + h, x + w - bw:x + w]
    border = np.concatenate([top.reshape(-1, 3), bottom.reshape(-1, 3), left.reshape(-1, 3), right.reshape(-1, 3)], axis=0)
    inner_pad = max(2, bw + 1)
    ix = x + inner_pad
    iy = y + inner_pad
    iw = max(1, w - 2 * inner_pad)
    ih = max(1, h - 2 * inner_pad)
    inner = img_bgr[iy:iy + ih, ix:ix + iw].reshape(-1, 3)
    if inner.size == 0 or border.size == 0:
        return False
    b_mean = np.mean(border, axis=0)
    i_mean = np.mean(inner, axis=0)
    b_gray = np.mean(b_mean)
    i_gray = np.mean(i_mean)
    chroma = max(abs(b_mean[0] - b_mean[1]), abs(b_mean[1] - b_mean[2]), abs(b_mean[2] - b_mean[0]))
    if chroma > 60:
        return False
    if not (70 <= b_gray <= 240):
        return False
    if i_gray < b_gray + 2:
        return False
    return True

def dedupe_boxes(boxes, iou_thresh=0.6):
    uniq = []
    for b in boxes:
        if not uniq:
            uniq.append(b)
            continue
        keep = True
        for u in uniq:
            ix1 = max(b[0], u[0])
            iy1 = max(b[1], u[1])
            ix2 = min(b[2], u[2])
            iy2 = min(b[3], u[3])
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            inter = iw * ih
            ub = (u[2] - u[0]) * (u[3] - u[1])
            bb = (b[2] - b[0]) * (b[3] - b[1])
            union = ub + bb - inter
            iou = inter / union if union > 0 else 0.0
            if iou >= iou_thresh:
                keep = False
                break
        if keep:
            uniq.append(b)
    return uniq

def scan_all_borders(img_bgr, gray, grad_bin, edges):
    H, W = gray.shape[:2]
    boxes = []
    contours, _ = cv2.findContours(grad_bin, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in contours:
        area = cv2.contourArea(c)
        if area < 200 or area > (W * H * 0.35):
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if w < 140 or h < 20 or h > 130:
            continue
        ratio = w / float(max(1, h))
        if ratio < 2.0:
            continue
        if not is_gray_border(img_bgr, x, y, w, h):
            continue
        boxes.append([x, y, x + w, y + h])
    win_h = 300
    stride = 60
    rx = 360
    rw = 720
    y = 0
    while y < H:
        y1 = max(0, y)
        y2 = min(H - 1, y + win_h)
        loc = locate_box_in_window(gray, y1, y2, rx=rx, rw=rw)
        if loc is not None:
            ax1, ay1, ax2, ay2 = loc
            w = ax2 - ax1
            h = ay2 - ay1
            ratio = w / float(max(1, h))
            if w >= 140 and 20 <= h <= 130 and ratio >= 2.0 and is_gray_border(img_bgr, ax1, ay1, w, h):
                boxes.append([ax1, ay1, ax2, ay2])
        y += stride
    cnts2, _ = cv2.findContours(edges, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    for c in cnts2:
        area = cv2.contourArea(c)
        if area < 200 or area > (W * H * 0.35):
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if w < 140 or h < 20 or h > 130:
            continue
        ratio = w / float(max(1, h))
        if ratio < 2.0:
            continue
        if not is_gray_border(img_bgr, x, y, w, h):
            continue
        boxes.append([x, y, x + w, y + h])
    return dedupe_boxes(boxes, iou_thresh=0.6)

def find_control_candidates(edge_img):
    contours, _ = cv2.findContours(edge_img, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    candidates = []
    h_img, w_img = edge_img.shape[:2]
    for c in contours:
        area = cv2.contourArea(c)
        if area < 300 or area > (w_img * h_img * 0.4):
            continue
        peri = cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, 0.02 * peri, True)
        if len(approx) != 4:
            continue
        x, y, w, h = cv2.boundingRect(approx)
        if w < 100 or h < 20:
            continue
        if h > 110:
            continue
        if w / float(h) < 2.8:
            continue
        candidates.append((x, y, w, h))
    candidates = sorted(candidates, key=lambda r: (r[1], r[0]))
    return candidates

def make_chevron_templates():
    temps = []
    for s in [10, 12, 14, 16, 18, 20, 22, 24, 26]:
        for t in [1, 2, 3]:
            img = np.zeros((s, s), dtype=np.uint8)
            pts = np.array([[t, t], [s // 2, s - t - 1], [s - t - 1, t]], dtype=np.int32)
            cv2.polylines(img, [pts], False, 255, thickness=t)
            temps.append(img)
            tri = np.zeros((s, s), dtype=np.uint8)
            tri_pts = np.array([[t, t], [s - t - 1, t], [s // 2, s - t - 1]], dtype=np.int32)
            cv2.fillPoly(tri, [tri_pts], 255)
            temps.append(tri)
    return temps

def make_funnel_templates():
    temps = []
    for w in [12, 14, 16, 18, 20, 22, 24]:
        h = w
        img = np.zeros((h, w), dtype=np.uint8)
        top = np.array([[1, 1], [w - 2, 1], [w // 2 + 2, h // 2], [w // 2 - 2, h // 2]], dtype=np.int32)
        cv2.fillPoly(img, [top], 255)
        stem_w = max(2, w // 6)
        cv2.rectangle(img, (w // 2 - stem_w // 2, h // 2), (w // 2 - stem_w // 2 + stem_w, h - 2), 255, -1)
        temps.append(img)
    return temps

CHEVRON_TEMPLATES = make_chevron_templates()
FUNNEL_TEMPLATES = make_funnel_templates()

def edge_templates(temps):
    out = []
    for t in temps:
        e = auto_canny(t, sigma=0.4)
        out.append(e)
    return out

CHEVRON_TEMPLATES_EDGE = edge_templates(CHEVRON_TEMPLATES)
FUNNEL_TEMPLATES_EDGE = edge_templates(FUNNEL_TEMPLATES)

def roi_match_score(roi_gray, templates):
    best = (0.0, (0, 0), (0, 0))
    for t in templates:
        th, tw = t.shape[:2]
        if roi_gray.shape[0] < th or roi_gray.shape[1] < tw:
            continue
        res = cv2.matchTemplate(roi_gray, t, cv2.TM_CCOEFF_NORMED)
        min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
        if max_val > best[0]:
            best = (max_val, max_loc, (tw, th))
    return best

def is_dropdown_and_icon(img_gray, box):
    x, y, w, h = box
    rx = x + int(w * 0.75)
    ry = y
    rw = max(12, int(w * 0.25))
    rh = h
    rx = max(0, min(rx, img_gray.shape[1] - 1))
    rw = max(10, min(rw, img_gray.shape[1] - rx))
    roi = img_gray[ry:ry + rh, rx:rx + rw]
    c_score, c_loc, c_size = roi_match_score(roi, CHEVRON_TEMPLATES)
    f_score, f_loc, f_size = roi_match_score(roi, FUNNEL_TEMPLATES)
    score = max(c_score, f_score)
    has = score >= 0.45
    icon_loc = None
    if c_score >= f_score and c_score >= 0.45:
        icon_loc = (rx + c_loc[0] + c_size[0] // 2, ry + c_loc[1] + c_size[1] // 2)
    elif f_score > c_score and f_score >= 0.45:
        icon_loc = (rx + f_loc[0] + f_size[0] // 2, ry + f_loc[1] + f_size[1] // 2)
    if not has:
        full_roi = img_gray[y:y + h, x:x + w]
        if full_roi.size > 0:
            rstrip = full_roi[:, max(0, w - min(24, w // 5)) : w]
            if rstrip.size > 0:
                if np.mean(rstrip) + 4 < np.mean(full_roi):
                    has = True
    return has, icon_loc

def detect_icons(img_gray, threshold=0.35, use_edges=True):
    icons = []
    # Match on grayscale
    for temps, ttype in [(CHEVRON_TEMPLATES, "chevron"), (FUNNEL_TEMPLATES, "funnel")]:
        for t in temps:
            th, tw = t.shape[:2]
            if img_gray.shape[0] < th or img_gray.shape[1] < tw:
                continue
            res = cv2.matchTemplate(img_gray, t, cv2.TM_CCOEFF_NORMED)
            yx = np.where(res >= threshold)
            for y, x in zip(yx[0], yx[1]):
                cx = x + tw // 2
                cy = y + th // 2
                score = float(res[y, x])
                icons.append((cx, cy, ttype, score))
    # Optionally match on edges
    if use_edges:
        edges_full = auto_canny(img_gray, sigma=0.5)
        for temps, ttype in [(CHEVRON_TEMPLATES_EDGE, "chevron"), (FUNNEL_TEMPLATES_EDGE, "funnel")]:
            for t in temps:
                th, tw = t.shape[:2]
                if edges_full.shape[0] < th or edges_full.shape[1] < tw:
                    continue
                res = cv2.matchTemplate(edges_full, t, cv2.TM_CCOEFF_NORMED)
                yx = np.where(res >= threshold)
                for y, x in zip(yx[0], yx[1]):
                    cx = x + tw // 2
                    cy = y + th // 2
                    score = float(res[y, x])
                    icons.append((cx, cy, ttype, score))
    # Deduplicate near hits, keep highest score per cluster
    merged = []
    for c in icons:
        if not merged:
            merged.append(c)
            continue
        found = False
        for i, m in enumerate(merged):
            if abs(c[0] - m[0]) <= 18 and abs(c[1] - m[1]) <= 18:
                if c[3] > m[3]:
                    merged[i] = c
                found = True
                break
        if not found:
            merged.append(c)
    return merged

def best_icon_in_window(img_gray, y1, y2):
    roi = img_gray[y1:y2, :]
    best = None
    for temps in [CHEVRON_TEMPLATES, FUNNEL_TEMPLATES]:
        for t in temps:
            th, tw = t.shape[:2]
            if roi.shape[0] < th or roi.shape[1] < tw:
                continue
            res = cv2.matchTemplate(roi, t, cv2.TM_CCOEFF_NORMED)
            min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
            if best is None or max_val > best[0]:
                best = (max_val, (max_loc[0] + tw // 2, max_loc[1] + th // 2))
    if best is None or best[0] < 0.4:
        return None
    return (best[1][0], y1 + best[1][1])

def locate_box_from_icon(img_gray, center):
    cx, cy = center
    h, w = img_gray.shape[:2]
    rx = max(0, cx - 800)
    ry = max(0, cy - 140)
    rw = min(w - rx, 860)
    rh = min(h - ry, 260)
    roi = img_gray[ry:ry + rh, rx:rx + rw]
    edges = auto_canny(roi, sigma=0.5)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=22, minLineLength=20, maxLineGap=6)
    if lines is None or len(lines) == 0:
        return None
    horizontals = []
    verticals = []
    for l in lines[:, 0, :]:
        x1, y1, x2, y2 = l
        if abs(y2 - y1) <= 2:
            horizontals.append((min(y1, y2), x1, x2))
        elif abs(x2 - x1) <= 2:
            verticals.append((min(x1, x2), y1, y2))
    if len(horizontals) < 2 or len(verticals) < 2:
        return None
    ys = sorted([hh[0] for hh in horizontals])
    best_pair = None
    for i in range(len(ys)):
        for j in range(i + 1, len(ys)):
            d = ys[j] - ys[i]
            if 24 <= d <= 80:
                if best_pair is None or abs((rh // 2) - ((ys[i] + ys[j]) // 2)) < abs((rh // 2) - ((best_pair[0] + best_pair[1]) // 2)):
                    best_pair = (ys[i], ys[j])
    if best_pair is None:
        return None
    top_y, bottom_y = best_pair
    v_filtered = []
    for x0, y1, y2 in verticals:
        ymin = min(y1, y2)
        ymax = max(y1, y2)
        if ymin <= top_y + 5 and ymax >= bottom_y - 5:
            v_filtered.append(x0)
    if len(v_filtered) < 2:
        return None
    xs = sorted(v_filtered)
    left_x = xs[0]
    right_x = xs[-1]
    bx1 = rx + left_x
    by1 = ry + top_y
    bx2 = rx + right_x
    by2 = ry + bottom_y
    if bx1 >= bx2 or by1 >= by2:
        return None
    return bx1, by1, bx2, by2

def locate_box_in_window(img_gray, y1, y2, rx=300, rw=900):
    h, w = img_gray.shape[:2]
    rx = max(0, rx)
    rw = min(w - rx, rw)
    ry = max(0, y1)
    rh = min(h - ry, max(20, y2 - y1))
    roi = img_gray[ry:ry + rh, rx:rx + rw]
    edges = auto_canny(roi, sigma=0.5)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=18, minLineLength=int(rw * 0.3), maxLineGap=6)
    if lines is None or len(lines) == 0:
        return None
    horizontals = []
    verticals = []
    for l in lines[:, 0, :]:
        x1, y1l, x2, y2l = l
        if abs(y2l - y1l) <= 2:
            horizontals.append(min(y1l, y2l))
        elif abs(x2 - x1) <= 2:
            verticals.append(min(x1, x2))
    if len(horizontals) < 2 or len(verticals) < 2:
        return None
    horizontals = sorted(horizontals)
    best_pair = None
    for i in range(len(horizontals)):
        for j in range(i + 1, len(horizontals)):
            d = horizontals[j] - horizontals[i]
            if 24 <= d <= 60:
                best_pair = (horizontals[i], horizontals[j])
                break
        if best_pair:
            break
    if not best_pair:
        return None
    top_y, bottom_y = best_pair
    xs = sorted(verticals)
    left_x = xs[0]
    right_x = xs[-1]
    bx1 = rx + left_x
    by1 = ry + top_y
    bx2 = rx + right_x
    by2 = ry + bottom_y
    if bx1 >= bx2 or by1 >= by2:
        return None
    return bx1, by1, bx2, by2

def locate_box_by_row_projection(img_gray, y1, y2, x1=300, x2=900):
    h, w = img_gray.shape[:2]
    x1 = max(0, min(x1, w - 1))
    x2 = max(0, min(x2, w - 1))
    if x2 <= x1:
        x1, x2 = x2, x1
    ry1 = max(0, y1)
    ry2 = min(h - 1, y2)
    roi = img_gray[ry1:ry2, x1:x2]
    edges = auto_canny(roi, sigma=0.5)
    profile = np.sum(edges, axis=1)
    if profile.size < 10:
        return None
    peaks = []
    thr = max(np.mean(profile) * 1.25, np.percentile(profile, 85))
    for i in range(1, profile.size - 1):
        if profile[i] > profile[i - 1] and profile[i] > profile[i + 1] and profile[i] >= thr:
            peaks.append(i)
    if len(peaks) < 2:
        return None
    best = None
    for i in range(len(peaks)):
        for j in range(i + 1, len(peaks)):
            d = abs(peaks[j] - peaks[i])
            if 24 <= d <= 60:
                best = (min(peaks[i], peaks[j]), max(peaks[i], peaks[j]))
                break
        if best:
            break
    if not best:
        return None
    top_y = ry1 + best[0]
    bottom_y = ry1 + best[1]
    etop = edges[max(0, best[0] - 2):min(edges.shape[0], best[0] + 3), :]
    ebottom = edges[max(0, best[1] - 2):min(edges.shape[0], best[1] + 3), :]
    lx = None
    rx = None
    for x in range(0, edges.shape[1]):
        if np.any(etop[:, x]) and np.any(ebottom[:, x]):
            lx = x
            break
    for x in range(edges.shape[1] - 1, -1, -1):
        if np.any(etop[:, x]) and np.any(ebottom[:, x]):
            rx = x
            break
    if lx is not None and rx is not None and rx - lx >= 200:
        return x1 + lx, top_y, x1 + rx, bottom_y
    return x1, top_y, x2, bottom_y

def refine_box(img_gray, box):
    x, y, w, h = box
    pad = 6
    rx = max(0, x - pad)
    ry = max(0, y - pad)
    rw = min(img_gray.shape[1] - rx, w + 2 * pad)
    rh = min(img_gray.shape[0] - ry, h + 2 * pad)
    roi = img_gray[ry:ry + rh, rx:rx + rw]
    edges = auto_canny(roi, sigma=0.5)
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=30, minLineLength=int(w * 0.5), maxLineGap=6)
    if lines is None or len(lines) == 0:
        return x, y, x + w, y + h
    horizontals = []
    verticals = []
    for l in lines[:, 0, :]:
        x1, y1, x2, y2 = l
        if abs(y2 - y1) <= 2:
            horizontals.append((min(y1, y2), x1, x2))
        elif abs(x2 - x1) <= 2:
            verticals.append((min(x1, x2), y1, y2))
    if not horizontals or not verticals:
        return x, y, x + w, y + h
    ys = sorted([hh[0] for hh in horizontals])
    xs = sorted([vv[0] for vv in verticals])
    top_y = ys[0]
    bottom_y = ys[-1]
    left_x = xs[0]
    right_x = xs[-1]
    ax1 = rx + left_x
    ay1 = ry + top_y
    ax2 = rx + right_x
    ay2 = ry + bottom_y
    ax1 = max(0, min(ax1, img_gray.shape[1] - 1))
    ax2 = max(0, min(ax2, img_gray.shape[1] - 1))
    ay1 = max(0, min(ay1, img_gray.shape[0] - 1))
    ay2 = max(0, min(ay2, img_gray.shape[0] - 1))
    if ay1 >= ay2 or ax1 >= ax2:
        return x, y, x + w, y + h
    return ax1, ay1, ax2, ay2

def draw_annotations(img_bgr, boxes):
    colors = [(255, 0, 0), (0, 255, 0), (0, 128, 255), (255, 0, 255), (0, 255, 255)]
    for i, b in enumerate(boxes):
        x1, y1, x2, y2 = b["abs_box"]
        cx, cy = b["click_point"]
        color = colors[i % len(colors)]
        cv2.rectangle(img_bgr, (x1, y1), (x2, y2), color, 3)
        r = 8
        cv2.line(img_bgr, (cx - r, cy), (cx + r, cy), color, 3)
        cv2.line(img_bgr, (cx, cy - r), (cx, cy + r), color, 3)
    return img_bgr

def nms_boxes(items, iou_thresh=0.5):
    bs = [(i, b["abs_box"]) for i, b in enumerate(items)]
    if not bs:
        return items
    areas = []
    for _, (x1, y1, x2, y2) in bs:
        areas.append(max(0, x2 - x1) * max(0, y2 - y1))
    order = np.argsort([-a for a in areas])
    keep_idx = []
    used = set()
    for oi in order:
        if oi in used:
            continue
        keep_idx.append(oi)
        x1, y1, x2, y2 = bs[oi][1]
        for oj in order:
            if oj == oi or oj in used:
                continue
            xx1, yy1, xx2, yy2 = bs[oj][1]
            ix1 = max(x1, xx1)
            iy1 = max(y1, yy1)
            ix2 = min(x2, xx2)
            iy2 = min(y2, yy2)
            iw = max(0, ix2 - ix1)
            ih = max(0, iy2 - iy1)
            inter = iw * ih
            union = areas[oi] + areas[oj] - inter
            iou = inter / union if union > 0 else 0.0
            if iou >= iou_thresh:
                used.add(oj)
    return [items[i] for i in keep_idx]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", type=str, default=None)
    ap.add_argument("--icons-only", action="store_true")
    ap.add_argument("--icon-thresh", type=float, default=0.35)
    ap.add_argument("--icon-box", type=int, default=28)
    ap.add_argument("--use-edge-templates", action="store_true")
    ap.add_argument("--all-borders", action="store_true")
    ap.add_argument("--candidates-only", action="store_true")
    args = ap.parse_args()
    candidates = []
    if args.image:
        candidates.append(args.image)
    envp = os.getenv("IMAGE_PATH")
    if envp:
        candidates.append(envp)
    candidates.append(IMAGE_PATH_DEFAULT)
    root = pathlib.Path(__file__).resolve().parents[2]
    snaps = sorted([p for p in (root / "snapshots").glob("gemini_fullpage_*.png") if "annotated" not in p.name and "dropdown" not in p.name], key=lambda p: p.stat().st_mtime if p.exists() else 0, reverse=True)
    if snaps:
        candidates.append(str(snaps[0]))
    chosen = None
    for c in candidates:
        if c and pathlib.Path(c).exists():
            chosen = c
            break
    if not chosen:
        raise RuntimeError("Image not found")
    p = pathlib.Path(chosen)
    img = cv2.imread(str(p))
    if img is None:
        raise RuntimeError("Image not found")
    print("Using image:", str(p))
    gray, edges, grad_bin = preprocess(img)
    if args.icons_only:
        icons = detect_icons(gray, threshold=args.icon_thresh, use_edges=args.use_edge_templates)
        items = []
        s = max(12, int(args.icon_box))
        r = s // 2
        for cx, cy, ttype, score in icons:
            x1 = int(max(0, cx - r))
            y1 = int(max(0, cy - r))
            x2 = int(min(img.shape[1] - 1, cx + r))
            y2 = int(min(img.shape[0] - 1, cy + r))
            items.append({
                "label": f"icon:{ttype}",
                "abs_box": [x1, y1, x2, y2],
                "click_point": [int(cx), int(cy)],
                "box_2d": [y1, x1, y2, x2],
                "score": float(score)
            })
        out_base = p.with_suffix('').as_posix()
        boxes_path = out_base + "_opencv_icons_boxes.json"
        with open(boxes_path, "w", encoding="utf-8") as f:
            json.dump({"image": str(p), "width": img.shape[1], "height": img.shape[0], "boxes": items}, f, indent=2)
        annotated = draw_annotations(img.copy(), items)
        out_img_path = out_base + "_opencv_icons_annotated.png"
        cv2.imwrite(out_img_path, annotated)
        print("Detected icons:", len(items))
        for i, d in enumerate(items, 1):
            print(i, d["label"], d["abs_box"], "score=", f"{d['score']:.2f}", "→", d["click_point"])
        print("Saved:", out_img_path)
        print("Saved:", boxes_path)
        return
    if args.all_borders:
        borders = scan_all_borders(img, gray, grad_bin, edges)
        items = []
        for b in borders:
            x1, y1, x2, y2 = [int(b[0]), int(b[1]), int(b[2]), int(b[3])]
            cx = int((x1 + x2) // 2)
            cy = int((y1 + y2) // 2)
            items.append({"label": "border", "abs_box": [x1, y1, x2, y2], "click_point": [cx, cy], "box_2d": [y1, x1, y2, x2]})
        out_base = p.with_suffix('').as_posix()
        boxes_path = out_base + "_opencv_allborders_boxes.json"
        with open(boxes_path, "w", encoding="utf-8") as f:
            json.dump({"image": str(p), "width": img.shape[1], "height": img.shape[0], "boxes": items}, f, indent=2)
        annotated = draw_annotations(img.copy(), items)
        out_img_path = out_base + "_opencv_allborders_annotated.png"
        cv2.imwrite(out_img_path, annotated)
        print("Detected:", len(items))
        for i, d in enumerate(items, 1):
            print(i, d["label"], d["abs_box"], "→", d["click_point"])
        print("Saved:", out_img_path)
        print("Saved:", boxes_path)
        return
    raw_candidates = find_control_candidates(grad_bin)
    print("Candidates:", len(raw_candidates))
    if args.candidates_only:
        items = []
        for (x, y, w, h) in raw_candidates:
            x1 = int(x)
            y1 = int(y)
            x2 = int(x + w)
            y2 = int(y + h)
            cx = int((x1 + x2) // 2)
            cy = int((y1 + y2) // 2)
            items.append({"label": "candidate", "abs_box": [x1, y1, x2, y2], "click_point": [cx, cy], "box_2d": [y1, x1, y2, x2]})
        out_base = p.with_suffix('').as_posix()
        boxes_path = out_base + "_opencv_candidates_boxes.json"
        with open(boxes_path, "w", encoding="utf-8") as f:
            json.dump({"image": str(p), "width": img.shape[1], "height": img.shape[0], "boxes": items}, f, indent=2)
        annotated = draw_annotations(img.copy(), items)
        out_img_path = out_base + "_opencv_candidates_annotated.png"
        cv2.imwrite(out_img_path, annotated)
        print("Detected:", len(items))
        for i, d in enumerate(items, 1):
            print(i, d["label"], d["abs_box"], "→", d["click_point"])
        print("Saved:", out_img_path)
        print("Saved:", boxes_path)
        return
    icons = detect_icons(gray)
    detections = []

    def detect_in_window(label, y1, y2):
        y1 = max(0, y1)
        y2 = min(gray.shape[0] - 1, y2)
        mask = np.zeros_like(grad_bin)
        mask[y1:y2, :] = grad_bin[y1:y2, :]
        window_candidates = find_control_candidates(mask)
        best = None
        for box in window_candidates:
            has_icon, icon_loc = is_dropdown_and_icon(gray, box)
            if not has_icon:
                continue
            ax1, ay1, ax2, ay2 = refine_box(gray, box)
            width = ax2 - ax1
            height = ay2 - ay1
            ratio = width / float(max(1, height))
            if width < 200 or height < 24 or height > 120 or ratio < 2.5:
                continue
            cx = int((ax1 + ax2) / 2)
            cy = int((ay1 + ay2) / 2)
            if icon_loc is not None:
                cx = max(ax1 + 6, min(ax2 - 6, icon_loc[0] - 6))
            cand = {
                "label": label,
                "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                "click_point": [int(cx), int(cy)],
            }
            if best is None or width > (best["abs_box"][2] - best["abs_box"][0]):
                best = cand
        if best is None:
            near_icons = [(cx, cy, t) for (cx, cy, t) in icons if y1 - 60 <= cy <= y2 + 60]
            for cx, cy, _ in near_icons:
                loc = locate_box_from_icon(gray, (cx, cy))
                if loc is None:
                    continue
                ax1, ay1, ax2, ay2 = loc
                ax1, ay1, ax2, ay2 = refine_box(gray, (ax1, ay1, ax2 - ax1, ay2 - ay1))
                width = ax2 - ax1
                height = ay2 - ay1
                ratio = width / float(max(1, height))
                if width < 200 or height < 24 or height > 120 or ratio < 2.5:
                    continue
                ccx = max(ax1 + 6, min(ax2 - 6, cx - 6))
                best = {
                    "label": label,
                    "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                    "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                    "click_point": [int(ccx), int(int((ay1 + ay2) / 2))],
                }
                break
        if best is None and window_candidates:
            widest = None
            for box in window_candidates:
                ax1, ay1, ax2, ay2 = refine_box(gray, box)
                width = ax2 - ax1
                height = ay2 - ay1
                ratio = width / float(max(1, height))
                if width < 200 or height < 24 or height > 120 or ratio < 2.5:
                    continue
                if widest is None or width > (widest["abs_box"][2] - widest["abs_box"][0]):
                    widest = {
                        "label": label,
                        "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                        "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                        "click_point": [int((ax1 + ax2) // 2), int((ay1 + ay2) // 2)],
                    }
            best = widest
        if best is None and label == "Country":
            bi = best_icon_in_window(gray, y1, y2)
            if bi is not None:
                loc = locate_box_from_icon(gray, bi)
                if loc is not None:
                    ax1, ay1, ax2, ay2 = loc
                    ax1, ay1, ax2, ay2 = refine_box(gray, (ax1, ay1, ax2 - ax1, ay2 - ay1))
                    width = ax2 - ax1
                    height = ay2 - ay1
                    ratio = width / float(max(1, height))
                    if width >= 200 and 24 <= height <= 120 and ratio >= 2.5:
                        best = {
                            "label": label,
                            "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                            "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                            "click_point": [int((ax1 + ax2) // 2), int((ay1 + ay2) // 2)],
                        }
        if best is None:
            loc = locate_box_in_window(gray, y1, y2)
            if loc is not None:
                ax1, ay1, ax2, ay2 = loc
                ax1, ay1, ax2, ay2 = refine_box(gray, (ax1, ay1, ax2 - ax1, ay2 - ay1))
                width = ax2 - ax1
                height = ay2 - ay1
                ratio = width / float(max(1, height))
                if width >= 200 and 24 <= height <= 120 and ratio >= 2.5:
                    best = {
                        "label": label,
                        "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                        "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                        "click_point": [int((ax1 + ax2) // 2), int((ay1 + ay2) // 2)],
                    }
        if best is None and label == "Country":
            loc = locate_box_by_row_projection(gray, y1, y2, x1=360, x2=720)
            if loc is not None:
                ax1, ay1, ax2, ay2 = loc
                ax1, ay1, ax2, ay2 = refine_box(gray, (ax1, ay1, ax2 - ax1, ay2 - ay1))
                width = ax2 - ax1
                height = ay2 - ay1
                ratio = width / float(max(1, height))
                if width >= 200 and 24 <= height <= 120 and ratio >= 2.5:
                    best = {
                        "label": label,
                        "box_2d": [int(ay1), int(ax1), int(ay2), int(ax2)],
                        "abs_box": [int(ax1), int(ay1), int(ax2), int(ay2)],
                        "click_point": [int((ax1 + ax2) // 2), int((ay1 + ay2) // 2)],
                    }
        return best

    label_windows = {
        "How Did You Hear About Us": (520, 620),
        "Country": (900, 1250),
        "State": (1440, 1480),
        "Phone Device Type": (1820, 1875),
        "Country Phone Code": (1900, 1970),
    }
    for lbl, (yy1, yy2) in label_windows.items():
        res = detect_in_window(lbl, yy1, yy2)
        if res is not None:
            detections.append(res)
    detections = [d for d in detections if (d["abs_box"][2] - d["abs_box"][0]) >= 200 and (d["abs_box"][3] - d["abs_box"][1]) >= 24 and (d["abs_box"][3] - d["abs_box"][1]) <= 120 and (d["abs_box"][2] - d["abs_box"][0]) / float(max(1, d["abs_box"][3] - d["abs_box"][1])) >= 2.5]
    detections = nms_boxes(detections, iou_thresh=0.6)
    out_base = p.with_suffix('').as_posix()
    boxes_path = out_base + "_opencv_dropdown_boxes.json"
    with open(boxes_path, "w", encoding="utf-8") as f:
        json.dump({"image": str(p), "width": img.shape[1], "height": img.shape[0], "boxes": detections}, f, indent=2)
    annotated = draw_annotations(img.copy(), detections)
    out_img_path = out_base + "_opencv_dropdown_annotated.png"
    cv2.imwrite(out_img_path, annotated)
    print("Detected:", len(detections))
    for i, d in enumerate(detections, 1):
        print(i, d["label"], d["abs_box"], "→", d["click_point"])
    print("Saved:", out_img_path)
    print("Saved:", boxes_path)

if __name__ == "__main__":
    main()

"""Conservative, tangent-guided gap repair for prepared binary trace images."""
from dataclasses import dataclass
import math
import heapq

import cv2
import numpy as np
from skimage.morphology import skeletonize


@dataclass
class Endpoint:
    xy: np.ndarray
    outward: np.ndarray
    width: float
    component: int


@dataclass
class RepairResult:
    image: np.ndarray
    added: np.ndarray
    skeleton: np.ndarray
    bridges: list


def _endpoints(mask, skeleton, components, span):
    """Estimate outward tangents from local geodesic skeleton neighborhoods."""
    distance = cv2.distanceTransform(mask.astype(np.uint8), cv2.DIST_L2, 5)
    count = cv2.filter2D(skeleton.astype(np.uint8), -1, np.ones((3, 3), np.float32),
                        borderType=cv2.BORDER_CONSTANT) - skeleton
    height, width = mask.shape
    points = []
    for y, x in np.argwhere(skeleton & (count == 1)):
        start = (int(y), int(x))
        distances = {start: 0.0}
        queue = [(0.0, start)]
        while queue:
            walked, (cy, cx) = heapq.heappop(queue)
            if walked > distances[(cy, cx)]:
                continue
            for ny in range(max(0, cy-1), min(height, cy+2)):
                for nx in range(max(0, cx-1), min(width, cx+2)):
                    if (ny, nx) == (cy, cx) or not skeleton[ny, nx]:
                        continue
                    candidate = walked + math.hypot(ny-cy, nx-cx)
                    if candidate <= span and candidate < distances.get((ny, nx), math.inf):
                        distances[(ny, nx)] = candidate
                        heapq.heappush(queue, (candidate, (ny, nx)))
        reach = max(distances.values())
        if reach < 3:
            continue
        # A geodesic neighborhood remains usable when raster caps have spurs.
        outer = [(py, px) for (py, px), d in distances.items() if d >= .7 * reach]
        weights = [max(1.0, float(distance[py, px])) for py, px in outer]
        reference = np.average(np.array(outer)[:, ::-1], axis=0, weights=weights)
        xy = np.array([x, y], dtype=float)
        outward = xy - reference
        norm = np.linalg.norm(outward)
        if norm == 0:
            continue
        radii = [distance[py, px] for (py, px), d in distances.items() if d >= .3 * reach]
        trace_width = max(1.0, 2.0 * float(np.median(radii)) - 1.0)
        # Recenter rasterized end caps only when their local body is linear.
        body = np.array([(px, py) for (py, px), d in distances.items() if d >= .3 * reach], dtype=float)
        center = body.mean(axis=0)
        covariance = (body-center).T @ (body-center) / len(body)
        eigenvalues, axes = np.linalg.eigh(covariance)
        if eigenvalues[0] <= .65**2 and eigenvalues[1] >= 3:
            axis = axes[:, 1]
            if axis @ outward < 0:
                axis = -axis
            projected = center + axis * ((xy-center) @ axis)
            px, py = np.rint(projected).astype(int)
            if (np.linalg.norm(projected-xy) <= max(1, trace_width*.25)
                    and 0 <= py < height and 0 <= px < width
                    and components[py, px] == components[y, x]):
                xy, outward, norm = projected, axis, 1.0
        points.append(Endpoint(xy, outward / norm, trace_width, int(components[y, x])))
    return points


def _curve(a, b, span):
    """Cubic Bezier with endpoint derivatives aligned to the local trace."""
    gap = float(np.linalg.norm(b.xy - a.xy))
    handle = min(gap / 3.0, span)
    control_a = a.xy + a.outward * handle
    control_b = b.xy + b.outward * handle
    t = np.linspace(0, 1, max(12, int(math.ceil(gap * 3))))[:, None]
    points = ((1-t)**3 * a.xy + 3*(1-t)**2*t*control_a
              + 3*(1-t)*t**2*control_b + t**3*b.xy)
    return np.rint(points).astype(np.int32)


def repair_trace(binary, *, max_gap=65.0, tangent_span=15.0,
                 max_endpoint_angle=110.0, max_mean_angle=70.0):
    """Reconnect compatible endpoints without thickening the existing trace.

    Input is a 2D binary mask with nonzero foreground. Matching uses outward
    tangents, distinct components, one connection per endpoint, and collision
    checks. Uncertain or obstructed pairs remain disconnected. All distances
    are in pixels; this function does not infer calibrated ECG samples.
    """
    array = np.asarray(binary)
    if array.ndim != 2 or array.size == 0:
        raise ValueError('Expected a nonempty 2D binary trace mask.')
    if not np.all(np.isin(array, (0, 1, 255))):
        raise ValueError('Threshold the image before calling repair_trace.')
    if max_gap <= 0 or tangent_span <= 0:
        raise ValueError('max_gap and tangent_span must be positive.')
    mask = array != 0
    skel = skeletonize(mask)
    n_components, components = cv2.connectedComponents(mask.astype(np.uint8), connectivity=8)
    endpoints = _endpoints(mask, skel, components, tangent_span)
    candidates = []
    for i, a in enumerate(endpoints):
        for j in range(i+1, len(endpoints)):
            b = endpoints[j]
            if a.component == b.component:
                continue
            displacement = b.xy - a.xy
            gap = float(np.linalg.norm(displacement))
            if gap == 0 or gap > max_gap:
                continue
            direction = displacement / gap
            angle_a = math.degrees(math.acos(float(np.clip(a.outward @ direction, -1, 1))))
            angle_b = math.degrees(math.acos(float(np.clip(b.outward @ -direction, -1, 1))))
            if max(angle_a, angle_b) > max_endpoint_angle:
                continue
            if (angle_a + angle_b) / 2 > max_mean_angle:
                continue
            score = gap + tangent_span * math.radians(angle_a + angle_b)
            candidates.append((score, i, j, gap, angle_a, angle_b))

    parent = list(range(n_components))
    def root(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k

    used = set()
    added = np.zeros(mask.shape, dtype=np.uint8)
    bridges = []
    for score, i, j, gap, angle_a, angle_b in sorted(candidates):
        a, b = endpoints[i], endpoints[j]
        if i in used or j in used or root(a.component) == root(b.component):
            continue
        points = _curve(a, b, tangent_span)
        # Match the thinner local trace; bounding-box width is not line width.
        line_width = max(1, int(round(min(a.width, b.width))) - 1)
        bridge = np.zeros(mask.shape, dtype=np.uint8)
        cv2.polylines(bridge, [points], False, 255, thickness=line_width, lineType=cv2.LINE_8)
        # Reject crossings of a third component, including the bridge's width.
        third = mask & (components != a.component) & (components != b.component)
        if np.any((bridge != 0) & third):
            continue
        caps = np.zeros(mask.shape, dtype=np.uint8)
        for endpoint in (a, b):
            radius = max(4, int(math.ceil(endpoint.width * 1.25)))
            cv2.circle(caps, tuple(endpoint.xy.astype(int)), radius, 255, -1)
        outside_caps = (bridge != 0) & (caps == 0)
        if np.any(outside_caps & (mask | (added != 0))):
            continue
        new_pixels = (bridge != 0) & ~mask
        if not np.any(new_pixels):
            continue
        added[new_pixels] = 255
        parent[root(a.component)] = root(b.component)
        used.update((i, j))
        bridges.append({'start_xy': a.xy.astype(int).tolist(), 'end_xy': b.xy.astype(int).tolist(),
                        'gap_px': round(gap, 3), 'width_px': line_width,
                        'endpoint_angles_deg': [round(angle_a, 2), round(angle_b, 2)],
                        'score': round(score, 3), 'path_xy': points.tolist()})
    output = (mask.astype(np.uint8) * 255) | added
    return RepairResult(output, added, (skeletonize(output != 0)*255).astype(np.uint8), bridges)

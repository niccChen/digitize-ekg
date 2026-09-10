"""Conservative, tangent-guided gap repair for prepared binary trace images."""
from dataclasses import dataclass
import math
import heapq

import cv2
import numpy as np
from skimage.morphology import skeletonize


@dataclass(frozen=True)
class PixelGrid:
    """Display-block spacing and edge phase, in input-image pixels."""

    step_x: float
    step_y: float
    offset_x: float = 0.0
    offset_y: float = 0.0

    def __post_init__(self):
        for step, offset in [(self.step_x, self.offset_x), (self.step_y, self.offset_y)]:
            if not math.isfinite(step) or step < 1 or not math.isfinite(offset):
                raise ValueError('Pixel-grid steps must be finite and at least one pixel; offsets must be finite.')


def estimate_pixel_grid(binary):
    """Find a strong, repeated edge lattice in a block-scaled binary image.

    Searches 2–12 pixel display blocks independently on each axis. Returns None
    when either axis has too few edges or weak periodic evidence.
    This estimates display pixel blocks, not physical time/voltage calibration.
    """
    mask = np.asarray(binary) != 0
    if mask.ndim != 2:
        raise ValueError('Expected a 2D binary mask.')
    estimates = []
    periods = np.linspace(2.0, 12.0, 10001)
    for axis in (1, 0):
        weights = np.abs(np.diff(mask.astype(float), axis=axis)).sum(axis=1-axis)
        positions = np.flatnonzero(weights) + 1
        if len(positions) < 20:
            return None
        weights = weights[positions-1]
        responses = []
        for chunk in np.array_split(periods, 50):
            response = (np.exp(2j*np.pi*positions[None, :]/chunk[:, None])*weights).sum(axis=1)
            responses.extend(np.abs(response) / weights.sum())
        responses = np.array(responses)
        peak = float(responses.max())
        if peak < .78:
            return None
        # Prefer the fundamental period over its shorter harmonic at a tie.
        choices = np.flatnonzero(responses >= peak - 1e-6)
        period = float(periods[choices[-1]])
        z = (np.exp(2j*np.pi*positions/period)*weights).sum()
        offset = float(np.angle(z)*period/(2*np.pi) % period)
        estimates.append((period, offset))
    return PixelGrid(estimates[0][0], estimates[1][0], estimates[0][1], estimates[1][1])


def _grid_projection(image, grid):
    """Sample the new stroke on a source-aligned coarse lattice only."""
    maps = []
    for length, step, offset in [(image.shape[1], grid.step_x, grid.offset_x),
                                 (image.shape[0], grid.step_y, grid.offset_y)]:
        k0 = math.floor(-offset/step)-1
        k1 = math.ceil((length-offset)/step)+1
        edges = np.unique(np.rint(offset + np.arange(k0, k1+1)*step).astype(int))
        index = np.searchsorted(edges, np.arange(length), side='right')-1
        centers = np.rint((edges[:-1]+edges[1:]-1)/2).astype(int)
        maps.append(np.clip(centers[index], 0, length-1))
    return image[np.ix_(maps[1], maps[0])]


def _paint_connection(shape, points, a, b, grid):
    """Blend the two local widths; optionally retain the source's block size."""
    width_a = max(1.0, a.width-1.0)
    width_b = max(1.0, b.width-1.0)
    lengths = np.linalg.norm(np.diff(points.astype(float), axis=0), axis=1)
    distance = np.r_[0.0, np.cumsum(lengths)]
    t = distance / max(distance[-1], 1.0)
    # A smooth width transition meets each end without a thin, constant neck.
    blend = t*t*(3-2*t)
    widths = width_a + (width_b-width_a)*blend
    bridge = np.zeros(shape, dtype=np.uint8)
    for index in range(len(points)-1):
        thickness = max(1, int(round((widths[index]+widths[index+1])/2)))
        cv2.line(bridge, tuple(points[index]), tuple(points[index+1]), 255,
                 thickness=thickness, lineType=cv2.LINE_8)
    if grid is not None:
        bridge = _grid_projection(bridge, grid)
    return bridge, [max(1, int(round(width_a))), max(1, int(round(width_b)))]


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
                 max_endpoint_angle=110.0, max_mean_angle=70.0, pixel_grid=None):
    """Reconnect compatible endpoints without thickening the existing trace.

    Input is a 2D binary mask with nonzero foreground. Matching uses outward
    tangents, distinct components, one connection per endpoint, and collision
    checks. Width transitions match both endpoints. An optional PixelGrid keeps
    newly drawn connections on the source block lattice. Uncertain or obstructed
    pairs remain disconnected. All distances are in pixels; this function does
    not infer calibrated ECG samples.
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
        bridge, endpoint_widths = _paint_connection(mask.shape, points, a, b, pixel_grid)
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
        if pixel_grid is not None:
            # Coarse sampling can erase a narrow section. Accept only a real
            # connection, with no detached blocks, before updating the graph.
            joined = (bridge != 0) | (components == a.component) | (components == b.component)
            if cv2.connectedComponents(joined.astype(np.uint8), connectivity=8)[0] != 2:
                continue
        new_pixels = (bridge != 0) & ~mask
        if not np.any(new_pixels):
            continue
        added[new_pixels] = 255
        parent[root(a.component)] = root(b.component)
        used.update((i, j))
        bridges.append({'start_xy': a.xy.astype(int).tolist(), 'end_xy': b.xy.astype(int).tolist(),
                        'gap_px': round(gap, 3), 'endpoint_widths_px': endpoint_widths,
                        'endpoint_angles_deg': [round(angle_a, 2), round(angle_b, 2)],
                        'score': round(score, 3), 'path_xy': points.tolist()})
    output = (mask.astype(np.uint8) * 255) | added
    return RepairResult(output, added, (skeletonize(output != 0)*255).astype(np.uint8), bridges)

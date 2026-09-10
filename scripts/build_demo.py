"""Build the README animation from the executed notebook's real output masks.

Run signal_fixing.ipynb first, then: python scripts/build_demo.py
"""
from pathlib import Path
import json
import platform
import shutil
from io import BytesIO

import cv2
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from skimage.morphology import skeletonize
from skimage.measure import label

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'docs' / 'assets'
RAW = ASSETS / 'demo'
OUTPUTS = ROOT / 'outputs' / 'signal-fixing'
RAW.mkdir(parents=True, exist_ok=True)

source_path = ROOT / 'result' / 'example.png'
source = cv2.imread(str(source_path), cv2.IMREAD_GRAYSCALE)
if source is None:
    raise FileNotFoundError(source_path)
results = {}
for name in ['component-bridged', 'constrained-bridged', 'endpoint-bridged', 'tangent-bridged']:
    path = OUTPUTS / f'{name}.png'
    if not path.exists():
        raise FileNotFoundError(f'{path.name} is missing. Run signal_fixing.ipynb first.')
    results[name] = cv2.imread(str(path), cv2.IMREAD_GRAYSCALE)
    if results[name].shape != source.shape:
        raise ValueError(f'{name}: output shape differs from the input.')

# Display actual pixels added by the repaired method.
skeleton = (skeletonize(source > 127) * 255).astype(np.uint8)
added = cv2.imread(str(OUTPUTS / 'tangent-added.png'), cv2.IMREAD_GRAYSCALE)
repaired_skeleton = cv2.imread(str(OUTPUTS / 'tangent-skeleton.png'), cv2.IMREAD_GRAYSCALE)
bridge_records = json.loads((OUTPUTS / 'tangent-bridges.json').read_text())
pixel_grid = json.loads((OUTPUTS / 'tangent-grid.json').read_text())
pairs = len(bridge_records)
for name in ['tangent-bridges.json', 'tangent-grid.json']:
    shutil.copyfile(OUTPUTS / name, RAW / name)
debug = cv2.cvtColor(((source > 127) * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB)
debug[added > 0] = [232, 164, 76]

BG, INK, BLUE, MUTED = '#f6f9fd', '#16314d', '#326c9f', '#60778d'
plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 13})
frames = []
stages = [
    ('01 / INPUT', 'A fragmented ECG trace', source,
     'Original repository crop · thresholded for reconstruction · 862 × 392 pixels'),
    ('02 / STRUCTURE', 'Estimate local trace direction', skeleton,
     'Endpoint tangents use skeleton neighborhoods rather than a single adjacent pixel'),
    ('03 / CONNECTIONS', 'Inspect the accepted bridges', debug,
     f'{pairs} accepted bridges · amber = newly added pixels · white = original binary foreground'),
    ('04 / REPAIR', 'Reconnect without global thickening', results['tangent-bridged'],
     'Two-end width transitions · source-aligned pixel blocks · original binary foreground preserved'),
    ('05 / REVIEW', 'Review the repaired centerline', repaired_skeleton,
     'Skeleton of the repaired image · inferred connections require review against the source'),
]
for kicker, title, data, subtitle in stages:
    fig = plt.figure(figsize=(12, 6.7), dpi=100, facecolor=BG)
    fig.text(.045, .941, kicker, color=BLUE, fontsize=12, weight='bold')
    fig.text(.045, .879, title, color=INK, fontsize=26, weight='bold')
    ax = fig.add_axes([.045, .17, .91, .635])
    ax.imshow(data, cmap='gray' if data.ndim == 2 else None, vmin=0, vmax=255, interpolation='nearest')
    ax.axis('off')
    fig.text(.045, .105, subtitle, color=MUTED, fontsize=11)
    fig.text(.045, .047, 'DIGITIZE EKG   /   REPRODUCIBLE IMAGE RECONSTRUCTION', color=BLUE, fontsize=10)
    with BytesIO() as buffer:
        fig.savefig(buffer, format='png', dpi=100, facecolor=BG)
        buffer.seek(0)
        frames.append(Image.open(buffer).convert('RGB'))
    plt.close(fig)
frames[0].save(ASSETS / 'walkthrough.gif', save_all=True, append_images=frames[1:],
               duration=[2200, 2200, 2800, 2200, 2800], loop=0, optimize=True)

counts = {'input': int(label(source > 127, connectivity=2).max())}
for name, data in results.items():
    counts[name] = int(label(data > 127, connectivity=2).max())

metrics = {
    'source': 'result/example.png',
    'shape_height_width': list(source.shape),
    'connectivity': 8,
    'foreground_components': counts,
    'tangent_repair': {'max_gap_px': 65, 'tangent_span_px': 15, 'accepted_bridges': pairs,
                       'source_display_grid': pixel_grid,
                       'added_foreground_pixels': int(np.count_nonzero(added)),
                       'original_foreground_preserved': bool(np.all(results['tangent-bridged'][source > 127] == 255))},
    'interpretation': 'Connectivity counts for one repository crop; not waveform accuracy or clinical validation.',
    'runtime': {'python': platform.python_version(), 'opencv': cv2.__version__, 'numpy': np.__version__},
}
(ASSETS / 'demo-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')

print(json.dumps(metrics, indent=2))
print('Built the animated walkthrough and reproducibility reports.')

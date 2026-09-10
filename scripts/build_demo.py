"""Build README figures from the executed notebook's real output masks.

Run signal_fixing.ipynb first, then: python scripts/build_demo.py
"""
from pathlib import Path
import json
import platform
import shutil
from html import escape

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
    shutil.copyfile(path, RAW / path.name)

# Display actual pixels added by the repaired method.
skeleton = (skeletonize(source > 127) * 255).astype(np.uint8)
cv2.imwrite(str(RAW / 'input-skeleton.png'), skeleton)
added = cv2.imread(str(OUTPUTS / 'tangent-added.png'), cv2.IMREAD_GRAYSCALE)
repaired_skeleton = cv2.imread(str(OUTPUTS / 'tangent-skeleton.png'), cv2.IMREAD_GRAYSCALE)
bridge_records = json.loads((OUTPUTS / 'tangent-bridges.json').read_text())
pairs = len(bridge_records)
for name in ['tangent-added.png', 'tangent-skeleton.png', 'tangent-bridges.json']:
    shutil.copyfile(OUTPUTS / name, RAW / name)
debug = cv2.cvtColor(((source > 127) * 255).astype(np.uint8), cv2.COLOR_GRAY2RGB)
debug[added > 0] = [232, 164, 76]
cv2.imwrite(str(RAW / 'tangent-overlay.png'), cv2.cvtColor(debug, cv2.COLOR_RGB2BGR))

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
     'Local-width cubic connections · endpoint matching and crossing checks · original foreground preserved'),
    ('05 / REVIEW', 'Review the repaired centerline', repaired_skeleton,
     'Skeleton of the repaired image · inferred connections require review against the source'),
]
for index, (kicker, title, data, subtitle) in enumerate(stages):
    fig = plt.figure(figsize=(12, 6.7), dpi=100, facecolor=BG)
    fig.text(.045, .941, kicker, color=BLUE, fontsize=12, weight='bold')
    fig.text(.045, .879, title, color=INK, fontsize=26, weight='bold')
    ax = fig.add_axes([.045, .17, .91, .635])
    ax.imshow(data, cmap='gray' if data.ndim == 2 else None, vmin=0, vmax=255, interpolation='nearest')
    ax.axis('off')
    fig.text(.045, .105, subtitle, color=MUTED, fontsize=11)
    fig.text(.045, .047, 'DIGITIZE EKG   /   REPRODUCIBLE IMAGE RECONSTRUCTION', color=BLUE, fontsize=10)
    path = RAW / f'stage-{index+1}.png'
    fig.savefig(path, dpi=100, facecolor=BG)
    plt.close(fig)
    frames.append(Image.open(path).convert('RGB'))
frames[0].save(ASSETS / 'walkthrough-static.png', optimize=True)
frames[0].save(ASSETS / 'walkthrough.gif', save_all=True, append_images=frames[1:],
               duration=[2200, 2200, 2800, 2200, 2800], loop=0, optimize=True)

fig, axes = plt.subplots(2, 2, figsize=(12, 7.6), dpi=150, facecolor=BG)
fig.subplots_adjust(left=.035, right=.975, top=.82, bottom=.11, hspace=.23, wspace=.07)
fig.text(.035, .94, 'ONE CROP / BEFORE AND AFTER THE ALGORITHM CHANGE', color=BLUE, fontsize=12, weight='bold')
fig.text(.035, .882, 'Earlier methods and the repaired version', color=INK, fontsize=22, weight='bold')
counts = {'input': int(label(source > 127, connectivity=2).max())}
for name, data in results.items():
    counts[name] = int(label(data > 127, connectivity=2).max())
for ax, (name, title, data) in zip(axes.ravel(), [
    ('input', 'Input crop', source),
    ('component-bridged', 'Previous: component baseline', results['component-bridged']),
    ('endpoint-bridged', 'Previous: endpoint variant', results['endpoint-bridged']),
    ('tangent-bridged', 'New: tangent-guided repair', results['tangent-bridged']),
]):
    ax.imshow(data, cmap='gray', vmin=0, vmax=255, interpolation='nearest')
    unit = 'component' if counts[name] == 1 else 'components'
    ax.set_title(f'{title}  ·  {counts[name]} {unit}', color=INK, fontsize=12, pad=10)
    ax.axis('off')
fig.text(.035, .041, '8-connected foreground components on this crop only. Fewer components do not establish reconstruction accuracy.', color=MUTED, fontsize=10)
fig.savefig(ASSETS / 'method-comparison.png', dpi=150, facecolor=BG)
plt.close(fig)

metrics = {
    'source': 'result/example.png',
    'shape_height_width': list(source.shape),
    'connectivity': 8,
    'foreground_components': counts,
    'tangent_repair': {'max_gap_px': 65, 'tangent_span_px': 15, 'accepted_bridges': pairs,
                       'added_foreground_pixels': int(np.count_nonzero(added)),
                       'original_foreground_preserved': bool(np.all(results['tangent-bridged'][source > 127] == 255))},
    'interpretation': 'Connectivity counts for one repository crop; not waveform accuracy or clinical validation.',
    'runtime': {'python': platform.python_version(), 'opencv': cv2.__version__, 'numpy': np.__version__},
}
(ASSETS / 'demo-metrics.json').write_text(json.dumps(metrics, indent=2) + '\n')

FONT = 'Arial, Helvetica, sans-serif'
def text(x, y, value, size=16, color=INK, weight=400, extra=''):
    return f'<text x="{x}" y="{y}" font-family="{FONT}" font-size="{size}" font-weight="{weight}" fill="{color}" {extra}>{escape(value)}</text>'
def svg(name, width, height, content, title):
    (ASSETS/name).write_text(f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img"><title>{escape(title)}</title>{content}</svg>\n')

hero = '<defs><pattern id="grid" width="24" height="24" patternUnits="userSpaceOnUse"><path d="M24 0H0V24" fill="none" stroke="#dce8f3" stroke-width=".8"/></pattern></defs>'
hero += '<rect x=".5" y=".5" width="1199" height="299" rx="16" fill="#f6f9fd" stroke="#d9e5f0"/>'
hero += '<rect x="39" y="29" width="39" height="39" rx="10" fill="#e3eff9"/>'
hero += '<path d="M46 50H52L55 42 60 58 64 47 67 50H72" fill="none" stroke="#326c9f" stroke-width="2.5" stroke-linejoin="round"/>'
hero += text(94, 46, 'COMPUTER VISION', 12, BLUE, 600, 'letter-spacing="1.5"')
hero += text(94, 64, 'ECG image reconstruction', 12, MUTED)
hero += text(39, 136, 'Digitize EKG', 58, INK, 700)
hero += text(41, 178, 'Reconstructing fragmented ECG traces', 26, '#385976')
hero += text(41, 219, 'Skeletons, endpoints, and geometric constraints.', 17, MUTED)
hero += text(41, 246, 'Local tangents. Width-aware gap repair.', 17, MUTED)
hero += text(41, 277, 'PYTHON  /  IMAGE PROCESSING  /  SIGNAL EXPLORATION', 10, BLUE, 600, 'letter-spacing="1.2"')
hero += '<rect x="788" y="35" width="370" height="230" rx="12" fill="white" stroke="#d9e5f0"/>'
hero += '<rect x="801" y="48" width="344" height="200" rx="8" fill="url(#grid)"/>'
hero += text(811, 73, 'FROM FRAGMENTS TO STRUCTURE', 10, BLUE, 600, 'letter-spacing="1"')
hero += '<path d="M808 173H842L854 164 867 173H888L896 185 906 105 918 204 932 173H955M979 173H997Q1027 130 1058 173H1080M1103 173H1140" fill="none" stroke="#326c9f" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"/>'
hero += '<path d="M955 173H979M1080 173H1103" fill="none" stroke="#d39a40" stroke-width="3" stroke-dasharray="4 4"/>'
hero += text(811, 241, 'IMAGE → SKELETON → RECONNECTION', 10, MUTED, 600)
svg('header.svg',1200,300,hero,'Digitize EKG — ECG image reconstruction')
for name, title, width in [('python','Python',75),('opencv','OpenCV',84),('skimage','scikit-image',108),('jupyter','Jupyter',79),('scipy','SciPy',68)]:
    content=f'<rect x=".5" y=".5" width="{width-1}" height="25" rx="5" fill="#edf4fb" stroke="#d4e3f0"/>'
    content+=text(width/2,17,title,12,'#426b8d',600,'text-anchor="middle"')
    svg(name+'.svg',width,26,content,title)
print(json.dumps(metrics, indent=2))
print('Built header, technology labels, walkthrough, and method comparison.')

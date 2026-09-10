# Animation and reproduction

The README uses a single animated walkthrough, `assets/walkthrough.gif`. Its five stages show the original `result/example.png` crop, its skeleton, the current method's added-pixel overlay, repaired mask, and repaired centerline. Amber pixels are newly inferred connections; white pixels in the overlay are the original binary foreground. Frame durations support reading rather than runtime measurement.

`assets/demo-metrics.json` records counts computed from the output masks. The bridge report in `assets/demo/tangent-bridges.json` records every accepted pair, two endpoint brush widths, direction scores, and centerline path before grid sampling. `assets/demo/tangent-grid.json` records the estimated block spacing and phase. These describe one crop, not waveform fidelity or physical calibration.

To reproduce, run `signal_fixing.ipynb` from the repository root and then `python scripts/build_demo.py`. The script reads the notebook outputs, renders animation frames in memory, and writes only the GIF and JSON reports under `docs/assets/`.

Original crops and page images remain in `result/` and `images/`. Generated reconstruction masks and debug views are available locally in `outputs/signal-fixing/` after running the notebook. See [data notes](./DATA.md) for their role and the PTB-XL reference.

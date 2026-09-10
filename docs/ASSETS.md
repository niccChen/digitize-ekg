# Asset credits and reproduction

- **Header and technology labels:** project-specific SVG artwork. The header's small ECG illustration is decorative; the scientific figures use actual notebook results.
- **Walkthrough:** the original `result/example.png` crop, its skeleton, a first-pass debug overlay from the notebook's `fix_ecg_debug` function, and real endpoint reconstruction outputs. Frame durations support reading and do not measure processing speed.
- **Method comparison:** the same input crop and the three outputs produced by `signal_fixing.ipynb`. Pixel geometry is preserved; the figure adds panel titles and connectivity counts.
- **Metrics:** 8-connected foreground-component counts computed directly from the binary image masks. These describe connectivity on one crop, not waveform fidelity.

To reproduce, run `signal_fixing.ipynb` from the repository root and then `python scripts/build_demo.py`. The script reads the output images, reuses the notebook's debug function, and rebuilds the figures under `docs/assets/`.

The original repository crops and page images remain in `result/` and `images/`. See [data notes](./DATA.md) for their role in the project and the PTB-XL reference.

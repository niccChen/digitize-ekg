# Asset credits and reproduction

- **Header and technology labels:** project-specific SVG artwork. The header's ECG illustration is decorative; the reconstruction figures use actual results.
- **Walkthrough:** the original `result/example.png` crop, its skeleton, the current method's added-pixel overlay, repaired mask, and repaired centerline. Amber pixels are newly inferred connections; white pixels in the overlay are the original binary foreground. Frame durations support reading rather than runtime measurement.
- **Method comparison:** the same input crop, the two earlier component and endpoint outputs, and the current tangent-guided result. Pixel geometry is preserved; the figure adds titles and connectivity counts.
- **Metrics and bridge report:** counts are computed from the output masks. The report includes every accepted pair, local stroke width, direction scores, and rendered path. These describe one crop, not waveform fidelity.

To reproduce, run `signal_fixing.ipynb` from the repository root and then `python scripts/build_demo.py`. The script reads the actual output images and bridge report, and rebuilds the figures under `docs/assets/`.

The original crops and page images remain in `result/` and `images/`. See [data notes](./DATA.md) for their role and the PTB-XL reference. Earlier debug files are retained under `docs/assets/demo/` for comparison.

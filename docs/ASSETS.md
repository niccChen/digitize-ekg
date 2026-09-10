# Asset credits and reproduction

- **Header and technology labels:** project-specific SVG artwork. The header's ECG illustration is decorative; the reconstruction figures use actual results.
- **Walkthrough:** the original `result/example.png` crop, its skeleton, the current method's added-pixel overlay, repaired mask, and repaired centerline. Amber pixels are newly inferred connections; white pixels in the overlay are the original binary foreground. Frame durations support reading rather than runtime measurement.
- **Method comparison:** the same input crop, the two earlier component and endpoint outputs, and the current tangent-guided result. Pixel geometry is preserved; the figure adds titles and connectivity counts.
- **Pixel close-ups:** two 90 × 90 pixel windows, shown at identical coordinates and magnification with nearest-neighbor sampling. `demo/prior-tangent-bridged.png` is the exact previous output from commit `987aff9`. The current output transitions between both endpoint widths and samples new bridges on the source's estimated display-block lattice; existing binary foreground remains intact.
- **Metrics and bridge report:** counts are computed from the output masks. The report includes every accepted pair, two endpoint brush widths, direction scores, and centerline path before grid sampling. `demo/tangent-grid.json` records the estimated block spacing and phase. These describe one crop, not waveform fidelity or physical calibration.

To reproduce, run `signal_fixing.ipynb` from the repository root and then `python scripts/build_demo.py`. The script reads the actual output images and bridge report, and rebuilds the figures under `docs/assets/`.

The original crops and page images remain in `result/` and `images/`. See [data notes](./DATA.md) for their role and the PTB-XL reference. Earlier debug files are retained under `docs/assets/demo/` for comparison.

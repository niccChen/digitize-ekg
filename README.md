# Digitize ECG Signals

A clean, reproducible pipeline to convert **scanned ECG images** into **analysis-ready** visuals and traces.  
It deskews pages, removes gridlines/shadows, bridges gaps, and enhances the ECG waveform for measurement or downstream ML.

---

## Table of Contents
- [Features](#features)
- [Repository Structure](#repository-structure)
- [Acknowledgments](#acknowledgments)

---

## Features
- **Image cleanup**: deskew/denoise, contrast normalization, background removal  
- **Grid suppression**: frequency/structural methods to remove graph paper  
- **Trace enhancement**: morphology-preserving filtering and **gap bridging**  
- **Batchable flow**: point to a directory of PNG/JPG scans  
- **Explorable**: Jupyter notebooks with step-by-step visuals

---

## Repository Structure

```text
.
├── images/                         # Sample inputs & intermediate visuals
├── result/                         # Example outputs (post-processing)
├── signal_fixing.ipynb             # Main pipeline notebook
├── testing_and_development.ipynb   # Experiments / ablations / scratch
├── ptxbl_database.csv              # (Optional) metadata/references
└── README.md
```
## Acknowledgments

#### Built with OpenCV, scikit-image, SciPy, and Matplotlib.

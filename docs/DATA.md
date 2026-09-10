# Data notes

This repository includes different kinds of material with different roles:

| Material | Role |
| --- | --- |
| `ptbxl_database.csv` | PTB-XL metadata used by the exploration notebook. It contains 21,799 data rows; metadata is not the waveform recording itself. |
| `images/00001_lr-0.png` through `00004_lr-0.png` | Full-page ECG examples already present in the repository. The filenames correspond to record-style IDs; the page-rendering script is not included. |
| `result/example.png` and `result/example1.png` | Prepared crops already present in the repository. The main reconstruction demo uses `example.png`. The notebook starts at this prepared-image stage. |
| Other images in `result/` | Historical experiment outputs retained for reference. Newly verified figures live in `docs/assets/`. |

The companion notebook calls `wfdb.rdsamp` to load the PTB-XL waveform files and uses `scp_statements.csv` to aggregate annotations. Those waveform files and the annotation mapping are external dependencies. Obtain them from the [official PhysioNet dataset page](https://physionet.org/content/ptb-xl/), then set `path` to the dataset directory with a trailing slash.

The main demo does not load patient metadata, classify diagnoses, or derive a reconstructed time-series signal from the full-page examples.

## Dataset citation

Wagner, P., Strodthoff, N., Bousseljot, R.-D., Kreiseler, D., Lunze, F. I., Samek, W., & Schaeffter, T. (2020). *PTB-XL, a large publicly available electrocardiography dataset*. Scientific Data, 7, 154. [DOI: 10.1038/s41597-020-0495-6](https://doi.org/10.1038/s41597-020-0495-6).

PTB-XL data is distributed under the terms stated on [PhysioNet](https://physionet.org/content/ptb-xl/). Dataset attribution and licensing are separate from the project-specific code and presentation assets.

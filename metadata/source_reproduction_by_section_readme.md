# Experiment reproduction by result subsection

This directory reorganizes the revised-algorithm and revised-assumption experiment materials by the manuscript result subsections.

Main revised run ids:

- P1--P8: multi_tower_repair2_full_20260612
- P9 public GIS: public_*_full_repair2_20260612 plus multi-region summaries dated 20260612
- P10 energy telemetry: airlab_energy_calibration_stop_batch_20260606
- P11 stress: repair_stress_repair2_20260612

Each result folder contains code, dataset, results, and plotting subfolders.

Validation before packaging:

```powershell
py -3.9 -m unittest discover -s 02_code\tests -q
# Ran 95 tests: OK
```

The full manuscript PDFs with highlighted revisions are in `../00_HIGHLIGHTED_MANUSCRIPT/` and `../00_FINAL_PDFs/`.

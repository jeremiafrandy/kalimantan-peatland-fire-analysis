# Kalimantan manuscript analysis consistency release

Analysis release: 5 October 2026. Supplementary update: 8 October 2026. This release covers the focused manuscript's MODIS
spatial summaries, rainfall association, Central Kalimantan 2023 burned area,
and published sensor/CAMS comparisons. It supersedes the older primary Poisson
table and figures that display IRR 0.316 as the main result. It does not publish
a repository, estimate peat-specific smoke exposure, or validate forecasts.

## Main results

- Full-year rainfall panel, 2020–2025: 773 cells, 1,694,416 grid-days, 3,059
  vegetation-fire detection days. Primary conditional logistic contrast:
  0–10 versus >100 mm preceding seven-day rainfall, adjusted odds ratio 10.50
  (approximate interval 6.78–16.27).
- Central Kalimantan, August–November 2023: burned fractions 4.41% within
  BIG ID 6 and 1.29% outside it; ratio 3.41.
- Published outdoor sensors, October 2023: mean 171.2 micrograms/m3.

## Reproduction

Main dependencies: Python 3.11 or later, numpy, pandas, scipy, matplotlib,
Pillow, python-docx, and system libtiff. `requirements.txt` records versions
used for this consistency pass. Optional raw sensor/CAMS checks use additional
dependencies listed in `requirements_sensor_cams.txt`; those checks had already
been completed in the 5 October verification report.

The supplied historical daily panel is sufficient to rerun the primary
statistical model and its observation-subset checks:

```bash
python code/Analyse_Rainfall_Conditional_Logistic.py --output .
python code/Analyse_Working_Poisson_Sensitivity.py --output .
```

For a complete rerun of the retained raw-data stages, place the original
attachments in a directory supplied as RAW_DIRECTORY. The rainfall directory
must contain the specified December 2019 and annual 2020–2025 GSMaP exports:

```bash
python code/Run_Analysis.py --output . --raw RAW_DIRECTORY \
  --rain RAINFALL_DIRECTORY --rebuild-panel \
  --manuscript ORIGINAL_MANUSCRIPT.docx
```

Required raw filenames and SHA-256 checksums are in `evidence/Input_SHA256.csv`
and `evidence/Burned_Area_Input_SHA256.csv`. Figure 1 also requires the original
ID 37 and ID 48 GeoJSON pages. These third-party map/rainfall inputs are not
redistributed in this focused package. Data-source endpoints are in the
manuscript and verification evidence. Reproduction targets are numerical;
compressed-file timestamps and font/rendering differences may alter file hashes.

Optional raw sensor/CAMS checks, after providing their dependencies:

```bash
python code/Verify_Published_Sensor_Data.py --sensor data/PA_data.nc \
  --daily-comparison data/Archived_Daily_2023_Comparison.csv --output evidence/Sensor_Rerun
python code/Verify_CAMS_UTC_WIB.py --help
```

The current figures and tables use the already verified daily sensor and CAMS
outputs in `evidence/`. The mean-of-reporting-sites statistic is not a
population-weighted or personal exposure estimate.

## Observation-bias scope

FIRMS CSVs contain detections only. Confidence, scan/track size, satellite, and
day/night checks are possible; observation opportunities, cloudy pixels,
unknown pixels, and missing swaths cannot be reconstructed from these fields.
No cloud correction was performed. A zero means no recorded detection,
not independently verified absence of fire. Future quantitative correction
requires spatially and temporally matched MOD14/MYD14 fire masks or equivalent
observation-availability data. MOD14A1/MYD14A1 daily composites can support a
daily availability screen but do not count all individual clear-sky overpasses.

## Current artifact order

Main manuscript: Figures 1–4, Tables 1–3. Supporting material: Figures S1–S3,
Tables S1–S10. `Artifact_Index.csv` links each output to its generation script
and inputs. `Supplementary_Results.md` explains the supporting material.
The revised graphical abstract uses the primary odds ratio; older graphical
abstracts displaying IRR 0.316 should not accompany this version.

The author's latest conclusion and MEXT acknowledgement are preserved.
Raw map provenance and sensor averaging-window uncertainties remain described;
they are not resolved by statistical sensitivity checks. See the audit report.

## Compact distribution

The daily analytic panel and classified MODIS records are supplied as CSV compressed with XZ rather than GZIP. Both decompressed CSV files are byte-for-byte identical to those in Supplement.zip. Analysis scripts and the panel-building script use the .csv.xz filenames. pandas detects this compression automatically; Python includes the lzma module. All tables, retained figures, and other data files are unchanged. Only duplicate PNG copies of Figures 1 and 2 are omitted; their original full-quality PDF versions are retained. Artifact_Index.csv points to those PDF files. The figure-generation scripts can regenerate PNG copies when the required map inputs are supplied. evidence/Release_SHA256.csv describes the files actually included in this compact archive. evidence/Compact_Distribution_Verification.json records the compression verification.

## Supplementary update of 8 October 2026

- Figure S1 is the author-supplied observational workflow. Its original transparent PNG is preserved byte-for-byte. The PDF places the same artwork on white without redrawing it.
- The previous observation-sensitivity Figure S1 is now Figure S2. The previous daily PM₂.₅ Figure S2 is now Figure S3. Their image and PDF contents are unchanged. Apply these figure-number changes in manuscript references before submission.
- Table S10 contains rainfall-category counts from the released complete panel, including informative strata and binary detection grid-days. Its CSV contains numeric counts; the caption and note are in Figure_and_Table_Captions.md.
- Supplementary_Additions_S1_S10.docx provides an editable version of the new figure, caption, table, and note in Times New Roman. The full accompanying text remains in Supplementary_Results.md; Tables S1–S9 remain in tables/.
- No statistical model was refitted for this update. Table S10 was recomputed from the existing panel and checked against the requested counts. Original data, estimates, and Tables S1–S9 are preserved. Historical verification reports retain their original dates and then-current filenames.

To reproduce the new table and assemble its editable supplement:

```bash
python code/Make_Table_S10_Rainfall_Category_Counts.py --output .
python code/Make_Supplementary_Additions_S1_S10.py --output .
```

The latter script requires python-docx, Pillow, and ReportLab. The original workflow artwork is a static input included in figures/. It does not indicate a fitted causal model or a source-resolved exposure estimate.

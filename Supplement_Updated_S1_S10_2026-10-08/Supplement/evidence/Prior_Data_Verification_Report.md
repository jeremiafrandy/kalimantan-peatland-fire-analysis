# Kalimantan data-verification report

Verification date: 5 October 2026. Scope: archived peatland map, published daily
sensor data, and raw CAMS cell-level PM2.5. Publication is outside this work.

## 1. ID 6: extraction completeness confirmed; original map provenance unresolved

The archived extract contains 100 unique features selected using
`landform LIKE '%Gambut%'` and an intersecting envelope of 108–120 degrees E
and 5 degrees S–5 degrees N, in EPSG:4326. Live `returnIdsOnly` and
`returnCountOnly` queries both returned the same 100 features. No archive IDs
were missing or extra. Attributes matched, and a fresh full-geometry GeoJSON
was byte-for-byte identical to the archive.

| Check | Result |
|---|---|
| Archived unique feature IDs | 100 |
| Live matching unique IDs / count | 100 / 100 |
| Missing / extra IDs | 0 / 0 |
| Matching full geometries | 100 / 100 |
| Full GeoJSON SHA-256 | 38bc876ecb68d6991e7bfa62edcb2f564037ee23bb14c7cef930b9da117c96b2 |
| Nonempty feature metadata | 0 / 100 |

The layer description and copyright fields are empty. Service-level information
credits Sekretariat Kebijakan Satupeta and contains a service description dated
08-08-2024; the service metadata XML has a creation date of 20240401. Neither
date proves when the underlying peatland was mapped. The original mapping
producer, year, scale, and original extraction date remain unspecified.

This closes the extraction-membership question for the current query. It does
not verify peatland-map accuracy, original scientific provenance, or complete
peatland coverage in the landscape. Continue to describe the comparison as
within versus outside the archived ID 6 map, without equating the outside
class to verified mineral soil.

## 2. Sensor data: source identity and monthly summaries reproduced

The NetCDF MD5 matches the cited Zenodo release:
`e811953a84db4fd14a33f67dd8f483dd`. The repository identifies the data as
humidity-adjusted daily concentrations and assigns CC BY 4.0.

The published paper uses both physical channels at most instruments and
physical Channel B at PA03/KR_06. The released file, however, contains all
nonmissing values under the field labelled A and none under B. The export's
physical-channel mapping is not explicitly documented. We therefore interpret
these as released processed concentrations, not raw physical Channel A values.

| Period | Reporting-site mean (micrograms/m3) | Fixed two-site mean | Mean excluding KR_06 | Site-days |
|---|---:|---:|---:|---:|
| 16–31 August | 40.1 | 37.7 | 40.5 | 125 |
| September | 100.3 | 93.9 | 101.7 | 233 |
| October | 171.2 | 156.4 | 171.9 | 224 |
| November | 47.0 | 31.5 | 48.5 | 234 |

The 107-day study interval contains 816 outdoor site-days and six to eight
reporting sites per day. PLK_01 and SBG_01 have complete coverage. The maximum
difference between regenerated daily network means and the archived table was
0.00000497 micrograms/m3, consistent with table rounding. October remains the
highest month when KR_06 is excluded and when a fixed two-site network is used.

The time coordinate uses midnight daily labels with units
`days since 2023-08-16 00:00:00` and a proleptic Gregorian calendar. It does not
explicitly identify the underlying daily averaging timezone. This uncertainty
cannot be resolved by treating midnight labels as hourly measurement records.

## 3. Raw CAMS daily means: UTC and WIB comparison

The supplied GRIB contains 2,920 three-hourly analysis times during 2023.
Its PM2.5 field is instantaneous surface concentration, parameter 210073,
in kg/m3, on a 0.75-degree grid. All eight sensor locations select the same
model cell. Every daily mean in the study interval has eight valid observations
under both UTC and local WIB (UTC+7) grouping.

| Daily CAMS convention | Paired days | CAMS mean (micrograms/m3) | Sensor mean | Spearman rho, daily levels | Spearman rho, first differences |
|---|---:|---:|---:|---:|---:|
| UTC | 107 | 187.8 | 96.9 | 0.882 | 0.383 |
| WIB | 107 | 187.9 | 96.9 | 0.881 | 0.204 |

Regenerated UTC values differ from the archived CAMS series by less than
0.00012 micrograms/m3. The broad seasonal correspondence and concentration
mean difference persist under both time conventions. Daily-change correlations
are more sensitive to the aggregation window. Neither convention establishes
which averaging period the original sensors used, and a higher correlation is
not a basis for declaring that convention correct.

## 4. Separate sensitivity to sensor date labels

Sensor dates were also shifted by one day in either direction while the
comparison series retained their existing dates.

| Sensor label offset | Paired days | CAMS rho, levels | CAMS rho, changes | Within-ID-6 burn rho, levels | Within-ID-6 burn rho, changes |
|---|---:|---:|---:|---:|---:|
| -1 day | 106 | 0.834 | -0.002 | 0.782 | 0.180 |
| 0 | 107 | 0.882 | 0.383 | 0.784 | 0.067 |
| +1 day | 106 | 0.802 | 0.349 | 0.764 | -0.042 |

A positive offset assigns the sensor value labelled D to D+1. These shifts are
not timezone conversions and do not reconstruct hourly sensor data. Sample
sizes change at the interval endpoints. Seasonal correspondence remains, but
precise daily timing and source attribution are not established.

## 5. Consequences for the manuscript

- Add the map completeness audit and verified snapshot checksum to Methods.
- Retain an unspecified original map year/scale rather than substituting the
  service's 2024 date.
- Describe the sensor input as the published processed daily series.
- Replace any implication of a channel switch in our analysis with an explicit
  statement that KR_06 was excluded as a sensitivity check for the instrument
  with a documented physical Channel-A failure.
- Report the UTC/WIB comparison as temporal sensitivity, not source validation.
- Preserve the October air-quality concern and the distinction between mapped
  burning and peat-fire-attributable exposure.

The original map producer/year/scale, exported physical-channel mapping, and
sensor daily averaging period still require clarification from the providers.
No provider messages have been sent. Rainfall models, burned-area rasters, and
wind fields were not rerun in this focused audit; see Analysis_Scope.md.

## Sources

BIG / Satu Peta, Peta Lahan Gambut layer 6:
https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/6

Service information:
https://kspservices.big.go.id/satupeta/rest/services/PUBLIK/SUMBER_DAYA_ALAM_DAN_LINGKUNGAN/MapServer/info/iteminfo?f=pjson

Graham and colleagues (2024), published daily sensor data:
https://doi.org/10.5281/zenodo.13767528

Graham and colleagues (2024), GeoHealth:
https://doi.org/10.1029/2024GH001125

ECMWF (2020), CAMS global reanalysis EAC4:
https://doi.org/10.24381/d58bbf47

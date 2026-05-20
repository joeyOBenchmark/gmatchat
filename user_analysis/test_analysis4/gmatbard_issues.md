# gmatbard Issues Log

## BurnReport FixedWidth=True breaks CSV parsing
**Date:** 2026-05-20
**Location:** gmatbard.high_level.mission_sequence_builder.MissionSequenceBuilder._setup_burn_report
**What happened:** `_setup_burn_report` sets `FixedWidth: True` and `ColumnWidth: 56` on the
ReportFile object. GMAT then writes the burn report as a fixed-width file where each row's
content is split into 56-character quoted chunks separated by commas, e.g.:

```
"burn_description,CubeSat.ElapsedDays,CubeSat.ElapsedSecs,bu","rn_type,n_burns,...
```

`pd.read_csv()` (used both by `BurnReportPlotter` and any manual parsing) treats each
56-character chunk as a separate column, so the resulting DataFrame has 8 mangled columns
instead of the expected 24+ named columns. All downstream processing fails.
**What was expected:** The burn report CSV should be standard comma-delimited with one column
per field so that `pd.read_csv()` and `BurnReportPlotter` can parse it without special handling.
The comment in the source says "Use fixed-width for reliable parsing" but it has the opposite effect.
**Workaround:** After constructing `MissionSequenceBuilder`, patch the report directly:

```python
msb = MissionSequenceBuilder(sim.script, vehicle.spacecraft, sim.propagator_name, ...)
# Disable FixedWidth so the CSV is parseable
for r in sim.script.reports:
    if r.name == 'BurnReport':
        r.properties['FixedWidth'] = False
        r.properties['Delimiter'] = ','
        break
```

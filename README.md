# NGIO_helper_functions

Functions to expand on the [NGIO](https://github.com/BioVisionCenter/ngio.git) library for needs specific to HCS (High-Content Screening) analysis.

## Simple Installation

```bash
pip install git+https://github.com/LiberaliLab/NGIO_helper_functions.git
```

## Installation for development

Clone the repo and install in editable mode:

```bash
git clone https://github.com/LiberaliLab/NGIO_helper_functions.git
cd NGIO_helper_functions
pip install -e .
```

This installs the package as `ngio_helpers`, importable from anywhere in your environment.

## Available Features

### HCS Dataset Iterator

Traverse wells across multiple OME-Zarr plates without manually nesting loops over plates and wells.

```python
from ngio_helpers import ZarrWellIterator, Formatter

plates = Formatter.collect_zarr_plates("/some/path")

for plate_name, well_name, well in ZarrWellIterator(plates):
    ...
```

`Formatter.collect_zarr_plates` scans a directory and builds a `{plate_name: path}` dictionary of all `.zarr` plates found. `ZarrWellIterator` then yields `(plate_name, well_name, well_container)` for every well across every plate, opening each plate as it goes, and skipping any plate that fails to open (logging the error) rather than halting the loop.

### Well Sampling

Randomly sample a fixed number of wells, distributed as evenly as possible across all plates — useful for spot-checking QC on a subset of a large dataset instead of reviewing every well.

```python
from ngio_helpers import Formatter, sample_wells, SampledWellIterator

plates = Formatter.collect_zarr_plates("/some/path")
subset = sample_wells(plates, n=10, seed=42)

for plate_name, well_name, well in SampledWellIterator(subset):
    ...
```

| Argument | Type | Description |
|---|---|---|
| `zarr_dict` | `dict[str, Path]` | `{plate_name: plate_path}` — output of `Formatter.collect_zarr_plates` |
| `n` | `int` | Total number of wells to sample across all plates |
| `seed` | `int`, optional | Random seed for reproducible sampling |

`sample_wells` opens each plate once to discover its wells, then allocates `n` as evenly as possible across all plates (redistributing automatically if a plate has fewer wells than its even share). It returns `{plate_name: {well_name: well_container}}`, with containers already open.

`SampledWellIterator` then yields `(plate_name, well_name, well_container)` from that pre-sampled dict. Unlike `ZarrWellIterator`, it does **not** re-open any plates — it simply flattens and iterates the containers `sample_wells` already opened, so use it specifically for `sample_wells` output rather than for a raw `{plate_name: plate_path}` dict.

### ROI Iterator

Iterates over the ROIs (regions of interest) within a single well, returning the composite image, the DAPI channel, the corresponding label map, and "cleaned" versions of both with neighboring objects suppressed.

```python
from ngio_helpers import ROIWellIterator

for roi_dict in ROIWellIterator(well_container, "DAPI_segmented_D11_D13_masking_ROI_table"):
    roi_dict["roi"]                      # the ROI object
    roi_dict["target_label"]             # label ID for this ROI's object
    roi_dict["roi_data"]                 # full multi-channel crop
    roi_dict["roi_data_dapi"]            # DAPI-only crop
    roi_dict["roi_data_label"]           # label map crop
    roi_dict["roi_data_dapi_cleaned"]    # DAPI crop, neighbors suppressed
    roi_dict["roi_data_label_cleaned"]   # label crop, neighbors suppressed
```

By default, the label container is inferred from the ROI table name (stripping the `_masking_ROI_table` suffix). Pass `label_name=...` explicitly if your table doesn't follow that convention.

### Image Cleaning

Suppresses background and neighboring objects in a crop, keeping only the pixels belonging to a target label.

```python
from ngio_helpers import ImageCleaning

cleaned = ImageCleaning.suppress_neighbors(
    intensity_crop,
    label_crop,
    target_label=7,
)
```

This is used internally by `ROIWellIterator` to produce the `_cleaned` fields above, but can also be called directly on any intensity/label crop pair.

## Formatter Class

Utility class for path discovery and metadata parsing. All methods are stateless.

```python
from ngio_helpers import Formatter
```

### `collect_zarr_plates(path_zarr)`

Scans a directory and returns a mapping of plate names to their paths.

```python
plates = Formatter.collect_zarr_plates("/data/experiment/")
# {"plate_A.zarr": PosixPath("/data/experiment/plate_A.zarr"), ...}
```

| Argument | Type | Description |
|---|---|---|
| `path_zarr` | `str` or `Path` | Root directory to scan for `.zarr` plate folders |

Returns `dict[str, Path]`. Returns an empty dict and logs a warning if the path does not exist.

---

### `rename_FE_image_channels(df, well_container)`

Renames numeric channel suffixes in a feature extraction DataFrame to human-readable channel labels from the OME-Zarr metadata.

```python
# Before: mean_intensity-0, mean_intensity-1
# After:  mean_intensity-DAPI, mean_intensity-Olfm4

df = Formatter.rename_FE_image_channels(df, well_container)
```

| Argument | Type | Description |
|---|---|---|
| `df` | `pd.DataFrame` | Feature table as returned by `run_extract` |
| `well_container` | `ngio.WellContainer` | Well container holding image and channel metadata |

Returns `pd.DataFrame` with channel columns renamed. Columns not matching the `<feature>-<index>` pattern are left unchanged.

---
## Project Structure

```
NGIO_helper_functions/
├── pyproject.toml
└── src/
    └── ngio_helpers/
        ├── __init__.py         # re-exports the public API listed below
        ├── iterators.py        # ZarrWellIterator, SampledWellIterator, ROIWellIterator
        ├── sampling.py          # sample_wells
        ├── formatting.py         # Formatter
        └── image_cleaning.py     # ImageCleaning
```

All public classes and functions are re-exported from the package root, so `from ngio_helpers import ...` works the same regardless of which submodule they actually live in:

```python
from ngio_helpers import (
    Formatter,
    ImageCleaning,
    ROIWellIterator,
    SampledWellIterator,
    ZarrWellIterator,
    sample_wells,
)
```

## Notes

- All iterators are designed to be resilient: if a single plate, well, or ROI fails to load, it is logged and skipped rather than halting the loop.
- Contributions and additional HCS-specific utilities are welcome — open a PR or issue.
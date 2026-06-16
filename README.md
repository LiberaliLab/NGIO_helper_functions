# NGIO_helper_functions

Functions to expand on the [NGIO](https://github.com/BioVisionCenter/ngio.git) library for needs specific to HCS (High-Content Screening) analysis.

## Installation

Clone the repo and install in editable mode:

```bash
git clone 
cd NGIO_helpers
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

`Formatter.collect_zarr_plates` scans a directory and builds a `{plate_name: path}` dictionary of all `.zarr` plates found. `ZarrWellIterator` then yields `(plate_name, well_name, well_container)` for every well across every plate, skipping any plate that fails to open and logging the error.

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

## Project Structure

```
NGIO_helpers/
├── pyproject.toml
└── src/
    └── ngio_helpers/
        ├── __init__.py
        ├── zarr_tools.py        # ZarrWellIterator, Formatter, ROIWellIterator, ImageCleaning
```

## Notes

- All iterators are designed to be resilient: if a single plate, well, or ROI fails to load, it is logged and skipped rather than halting the loop.
- Contributions and additional HCS-specific utilities are welcome — open a PR or issue.



import re
import logging
import numpy as np
from pathlib import Path
from ngio import open_ome_zarr_plate
import pandas as pd

#------------------------------------------------------------------------
# Custom extensions for the NGIO ecosystem, providing high-level iterators 
#     and formatting utilities for OME-Zarr plates.
#------------------------------------------------------------------------

class ZarrWellIterator:
    """
    Streamlined iterator to traverse wells across multiple OME-Zarr plates.
    Accepts either:
      - {plate_name: plate_path} (from collect_zarr_plates), or
      - {plate_name: {well_name: well_container}} (e.g. from sample_wells)
    Yields: (plate_name, well_name, well_container)
    """

    def __init__(self, zarr_dict):
        self.zarr_items = list(zarr_dict.items())
        self.plate_idx = 0
        self.well_iter = None
        self.current_plate_name = None

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if self.well_iter is None:
                if self.plate_idx >= len(self.zarr_items):
                    raise StopIteration

                plate_name, plate_value = self.zarr_items[self.plate_idx]
                self.plate_idx += 1
                self.current_plate_name = plate_name

                if isinstance(plate_value, dict):
                    # Already {well_name: well_container} — no need to open the plate
                    self.well_iter = iter(plate_value.items())
                else:
                    # It's a path — open the plate and get its wells
                    try:
                        plate = open_ome_zarr_plate(plate_value)
                        self.well_iter = iter(plate.get_images().items())
                    except Exception as e:
                        logging.error(f"Failed to open plate {plate_name}: {e}")
                        continue

            try:
                well_name, well_container = next(self.well_iter)
                return self.current_plate_name, well_name, well_container
            except StopIteration:
                self.well_iter = None

class ROIWellIterator:
    """
    Streamlined iterator to iterate through ROIs, returning labels, composite images and cleaned crops.
    Yields: dict with keys roi, roi_data, roi_data_dapi, roi_data_label,
            roi_data_dapi_cleaned, roi_data_label_cleaned
    """

    def __init__(self, well_container, table_name, label_name=None):
        self.well_container = well_container
        self.composite = well_container.get_image()
        self.roi_table = well_container.get_table(table_name)
        self.roi_iter = iter(self.roi_table.rois())

        self.label_name = label_name or table_name.replace("_masking_ROI_table", "")
        self.label_container = well_container.get_label(self.label_name)


    def __iter__(self):
        return self

    def __next__(self):
        while True:
            roi = next(self.roi_iter)
            try:
                target_label = roi.label

                roi_data = self.composite.get_roi_as_numpy(roi, c=None)
                roi_data_dapi = self.composite.get_roi_as_numpy(roi, c=0)
                roi_data_label = self.label_container.get_roi_as_numpy(roi)

                roi_data_dapi_cleaned = np.squeeze(
                    ImageCleaning.suppress_neighbors(roi_data_dapi, roi_data_label, target_label)
                )
                roi_data_label_cleaned = np.squeeze(
                    ImageCleaning.suppress_neighbors(roi_data_label, roi_data_label, target_label)
                )

                return {
                    "roi": roi,
                    "target_label": target_label,
                    "roi_data": roi_data,
                    "roi_data_dapi": roi_data_dapi,
                    "roi_data_label": roi_data_label,
                    "roi_data_dapi_cleaned": roi_data_dapi_cleaned,
                    "roi_data_label_cleaned": roi_data_label_cleaned,
                }
            except Exception as e:
                logging.error(f"Failed to extract/clean ROI {roi}: {e}")
                continue

class Formatter:
    """Utility methods for path discovery and metadata parsing."""

    @staticmethod
    def collect_zarr_plates(path_zarr):
        """Build dict: plate_name -> path to ome-zarr plate."""
        root = Path(path_zarr)
        if not root.exists():
            logging.warning(f"Path does not exist: {path_zarr}")
            return {}

        return {
            p.name: p
            for p in root.iterdir()
            if p.is_dir() and p.suffix == ".zarr"
        }
    @staticmethod
    def rename_FE_image_channels(df, well_container):
        """
        Rename feature extraction dataframe columns using ome-zarr channel labels.

        Converts columns like:
            mean_intensity-0 → mean_intensity-DAPI
            max_intensity-1 → max_intensity-Olfm4
            ...

        Parameters
        ----------
        df : pd.DataFrame
            Feature extraction dataframe.
        well_container : ngio.WellContainer
            Container holding image + channel metadata.

        Returns
        -------
        df : pd.DataFrame
            Dataframe with renamed columns.
        """

        img = well_container.get_image()

        # Build index → channel name mapping
        channel_map = {
            img.get_channel_idx(name): name
            for name in img.channel_labels
        }

        # Rename columns
        def rename_col(col):
            m = re.search(r"(.*)-(\d+)$", col)
            if m:
                base, idx = m.groups()
                idx = int(idx)
                if idx in channel_map:
                    return f"{base}-{channel_map[idx]}"
            return col

        df = df.rename(columns=rename_col)

        return df

class ImageCleaning:
    @staticmethod
    def suppress_neighbors(intensity_crop, label_crop, target_label, background_value=None):
        """
        intensity_crop: (H, W) single channel
        label_crop: (H, W) integer label map, same shape
        target_label: the label ID of YOUR organoid (e.g. 42)
        Removes background that is not within the label of the image
        """
        if background_value is None:
            bg_mask = (label_crop == 0)
            background_value = np.median(intensity_crop[bg_mask]) if bg_mask.any() else np.median(intensity_crop)
        neighbor_mask = (label_crop != target_label) & (label_crop != 0)
        cleaned = intensity_crop.copy()
        cleaned[neighbor_mask] = background_value
        return cleaned
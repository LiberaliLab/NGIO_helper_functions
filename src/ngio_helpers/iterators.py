import logging
import numpy as np
from ngio import open_ome_zarr_plate


class ZarrWellIterator:
    """
    Streamlined iterator to traverse wells across multiple OME-Zarr plates.
    Yields: (plate_name, well_name, well_container)
    """
    def __init__(self, zarr_dict):
        self.zarr_items = list(zarr_dict.items())
        self.plate_idx = 0
        self.well_iter = None
        self.current_plate_name = None # Initialized for safety

    def __iter__(self):
        return self

    def __next__(self):
        while True:
            if self.well_iter is None:
                if self.plate_idx >= len(self.zarr_items):
                    raise StopIteration

                plate_name, plate_path = self.zarr_items[self.plate_idx]
                self.plate_idx += 1

                try:
                    plate = open_ome_zarr_plate(plate_path)
                    self.current_plate_name = plate_name
                    self.well_iter = iter(plate.get_images().items()) # Get the dictionary of well name: well container 
                except Exception as e:
                    logging.error(f"Failed to open plate {plate_name}: {e}")
                    continue # Skip to the next plate if one is corrupt

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


class SampledWellIterator:
    """
    Iterator for pre-sampled wells with already-open containers.

    Unlike ZarrWellIterator, this does NOT call open_ome_zarr_plate —
    it expects containers to already be open (e.g. output of sample_wells).

    Expects: {plate_name: {well_name: well_container}}
    Yields: (plate_name, well_name, well_container)
    """

    def __init__(self, sampled_dict: dict):
        # Flatten upfront into a simple list of tuples
        self.items = [
            (plate_name, well_name, well_container)
            for plate_name, wells in sampled_dict.items()
            for well_name, well_container in wells.items()
        ]
        self.idx = 0

    def __iter__(self):
        return self

    def __next__(self):
        if self.idx >= len(self.items):
            raise StopIteration
        item = self.items[self.idx]
        self.idx += 1
        return item
class NgioExtensions: # Slightly more standard naming
    """
    Custom extensions for the NGIO ecosystem, providing high-level iterators 
     and formatting utilities for OME-Zarr plates.
    """

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
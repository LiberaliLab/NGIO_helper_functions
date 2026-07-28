import numpy as np

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
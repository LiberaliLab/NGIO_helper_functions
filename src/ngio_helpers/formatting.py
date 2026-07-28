import re
import logging
from pathlib import Path

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
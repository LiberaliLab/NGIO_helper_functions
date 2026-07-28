import random
from ngio_helpers.iterators import ZarrWellIterator

def sample_wells(zarr_dict: dict, n: int, seed: int = None) -> dict:
    """
    Randomly sample `n` wells total, distributed as evenly as possible across plates.

    Parameters
    ----------
    zarr_dict : dict
        {plate_name: plate_path} — output of collect_zarr_plates.
    n : int
        Total number of wells to sample across all plates.
    seed : int, optional
        Random seed for reproducibility.

    Returns
    -------
    dict
        {plate_name: {well_name: well_container}} containing only the sampled wells.
    """
    rng = random.Random(seed)

    # Discover wells per plate using the SAME code path as your working loop
    plate_wells = {}
    for plate_name, well_name, well_container in ZarrWellIterator(zarr_dict):
        plate_wells.setdefault(plate_name, {})[well_name] = well_container

    plate_names = list(plate_wells.keys())
    n_plates = len(plate_names)
    if n_plates == 0:
        return {}

    total_wells = sum(len(wells) for wells in plate_wells.values())
    if n > total_wells:
        raise ValueError(
            f"Requested {n} wells, but only {total_wells} available across all plates."
        )

    base_per_plate = n // n_plates
    remainder = n % n_plates

    shuffled_plates = plate_names.copy()
    rng.shuffle(shuffled_plates)

    allocation = {plate: base_per_plate for plate in plate_names}
    for plate in shuffled_plates[:remainder]:
        allocation[plate] += 1

    leftover = 0
    for plate in plate_names:
        available = len(plate_wells[plate])
        if allocation[plate] > available:
            leftover += allocation[plate] - available
            allocation[plate] = available

    if leftover > 0:
        candidates = [p for p in plate_names if allocation[p] < len(plate_wells[p])]
        rng.shuffle(candidates)
        i = 0
        while leftover > 0 and candidates:
            p = candidates[i % len(candidates)]
            if allocation[p] < len(plate_wells[p]):
                allocation[p] += 1
                leftover -= 1
            i += 1
            if i > 10_000:
                break

    sampled = {}
    for plate, count in allocation.items():
        if count == 0:
            continue
        well_names = list(plate_wells[plate].keys())
        chosen = rng.sample(well_names, count)
        sampled[plate] = {well: plate_wells[plate][well] for well in chosen}

    return sampled
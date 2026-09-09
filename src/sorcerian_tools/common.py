import os

type TrackSector = tuple[int, int]


def basename_no_ext(fn: str):
    name, _ = os.path.splitext(os.path.basename(fn))
    return name

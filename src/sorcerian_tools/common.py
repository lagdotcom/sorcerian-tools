import os

type TrackSector = tuple[int, int]


def bnnx(fn: str):
    name, _ = os.path.splitext(os.path.basename(fn))
    return name

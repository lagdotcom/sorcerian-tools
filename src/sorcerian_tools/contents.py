import os
import tomllib
from dataclasses import dataclass
from glob import glob

from .common import TrackSector, bnnx


@dataclass
class ContentsDisk:
    product: str
    sha1: str
    name: str | None = None

    def __str__(self) -> str:
        if self.name:
            return f"{self.product} ({self.name})"
        else:
            return self.product


@dataclass
class ContentsListing:
    type: str
    start: TrackSector = (1, 1)
    size: int | None = None


@dataclass
class ContentsEntry:
    filename: str
    type: str
    format: str | None = None
    size: tuple[int, int] | None = None
    tile_size: tuple[int, int] | None = None
    encoding: str | None = None


@dataclass
class ContentsTOML:
    toml_name: str
    disk: ContentsDisk
    listing: ContentsListing
    entries: list[ContentsEntry]

    @staticmethod
    def from_toml_file(fn: str):
        with open(fn, "r") as f:
            data = tomllib.loads(f.read())

            disk = data.get("disk", {})
            listing = data.get("listing", {})
            return ContentsTOML(
                bnnx(fn),
                ContentsDisk(
                    disk.get("product", "UNKNOWN"),
                    disk.get("sha1", "UNKNOWN"),
                    disk.get("name"),
                ),
                ContentsListing(
                    listing.get("type", "dir"),
                    listing.get("start", (1, 1)),
                    listing.get("size"),
                ),
                [
                    ContentsEntry(
                        e.get("filename", "UNKNOWN"),
                        e.get("type", "UNKNOWN"),
                        e.get("format"),
                        e.get("size"),
                        e.get("tile_size"),
                        e.get("encoding"),
                    )
                    for e in data.get("entry", [])
                ],
            )


def load_content_tomls() -> dict[str, ContentsTOML]:
    return {
        toml.disk.sha1: toml
        for toml in [
            ContentsTOML.from_toml_file(fn)
            for fn in glob(os.path.join("contents", "*.toml"))
        ]
    }


def get_empty_contents_toml(fn: str, sha1: str):
    return ContentsTOML(
        bnnx(fn),
        ContentsDisk("UNKNOWN", "UNKNOWN", sha1),
        ContentsListing("dir"),
        [],
    )

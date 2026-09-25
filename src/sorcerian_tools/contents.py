import os
import tomllib
from dataclasses import dataclass
from glob import glob
from typing import Any

from .common import TrackSector, basename_no_ext


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
class ImagePatterns:
    filename: str
    offset: int
    count: int
    mode: str
    base: int
    allow_ff: bool

    @staticmethod
    def from_dict(e: dict[Any, Any]):
        return ImagePatterns(
            e["filename"],
            e.get("offset", 0),
            e.get("count", 0),
            e["mode"],
            e.get("base", 0),
            e.get("allow_ff", False),
        )

    def is_valid(self, n: int, tiles: list[Any]):
        if n == 0xFF and not self.allow_ff:
            return False
        n_value = n - self.base
        return n_value >= 0 and n_value < len(tiles)


TEXT_TYPES = {"text", "menu", "scenario", "treasure"}
IMAGE_TYPES = {"image", "map"}


@dataclass
class ContentsEntry:
    filename: str
    type: str
    mount: int | None = None
    format: str | None = None
    size: tuple[int, int] | None = None
    tile_size: tuple[int, int] | None = None
    encoding: str | None = None
    write_as: str | None = None
    patterns: ImagePatterns | None = None
    tiles: str | None = None
    has_mask: bool = True

    def get_write_filename(self):
        if self.write_as:
            return self.write_as
        if self.type in TEXT_TYPES:
            return self.filename + ".txt"
        if self.type in IMAGE_TYPES:
            return self.filename + ".png"
        return self.filename + ".bin"

    @staticmethod
    def from_dict(e: dict[Any, Any]):
        patterns = None
        if "patterns" in e:
            patterns = ImagePatterns.from_dict(e["patterns"])

        return ContentsEntry(
            filename=e.get("filename", "UNKNOWN"),
            type=e.get("type", "UNKNOWN"),
            mount=e.get("mount"),
            format=e.get("format"),
            size=e.get("size"),
            tile_size=e.get("tile_size"),
            encoding=e.get("encoding"),
            write_as=e.get("write_as"),
            patterns=patterns,
            tiles=e.get("tiles"),
            has_mask=e.get("has_mask", True),
        )


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
                basename_no_ext(fn),
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
                [ContentsEntry.from_dict(e) for e in data.get("entry", [])],
            )

    def get_entry(self, filename: str):
        for e in self.entries:
            if e.filename == filename:
                return e


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
        basename_no_ext(fn),
        ContentsDisk("UNKNOWN", "UNKNOWN", sha1),
        ContentsListing("dir"),
        [],
    )

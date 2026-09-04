import os
import tomllib
from dataclasses import dataclass
from glob import glob
from pathlib import Path

from sorcerian_tools.image import to_1bpp

from .d88tool import D88
from .dir import Entry, get_entries, get_entry_data
from .hash import get_all_disk_files, get_sha1

type TrackSector = tuple[int, int]


def bnnx(fn: str):
    name, _ = os.path.splitext(os.path.basename(fn))
    return name


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


if __name__ == "__main__":
    tomls = load_content_tomls()
    d88s = list(get_all_disk_files())
    out_dir = Path("out")
    for fn in d88s:
        sha1 = get_sha1(fn)
        toml = tomls.get(sha1)
        if toml:
            print(f"{fn}: {toml.disk}")
        else:
            print(f"{fn}: no hash match")
            toml = ContentsTOML(
                bnnx(fn),
                ContentsDisk("UNKNOWN", "UNKNOWN", sha1),
                ContentsListing("dir"),
                [],
            )
        with open(fn, "rb") as f:
            dir = out_dir / toml.toml_name
            if not dir.exists():
                os.makedirs(dir)
            d88 = D88(f)

            listing = get_entries(f, toml.listing.start[0])
            lfn = dir / "listing.txt"
            print(f"> {lfn}", end="... ")
            with open(lfn, "w") as o:
                o.write(Entry.LINE_HEADER + "\n")
                o.writelines([e.as_line() + "\n" for e in listing.values()])
            print("OK")

            for e in toml.entries:
                ptr = listing.get(e.filename)
                if ptr is None:
                    print(f"! could not find {e.filename}")
                    continue

                if e.type == "image" and e.format == "1bpp":
                    if e.size is None or e.tile_size is None:
                        print(f"! {e.filename} needs size and tile_size")
                        continue
                    img = to_1bpp(
                        get_entry_data(f, ptr),
                        e.size[0],
                        e.tile_size[0],
                        e.tile_size[1],
                    )
                    ifn = dir / (e.filename + ".png")
                    print(f"> {ifn}", end="... ")
                    img.save(ifn)
                    print("OK")
                else:
                    ofn = dir / (e.filename + ".bin")
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "wb") as o:
                        o.write(get_entry_data(f, ptr))
                    print("OK")

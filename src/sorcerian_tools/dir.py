import struct
from dataclasses import dataclass
from enum import StrEnum
from typing import BinaryIO

from .d88tool import D88
from .image import to_1bpp


@dataclass
class Entry:
    name: str
    unknown: int
    load: int
    upto: int
    track: int
    record: int
    end_track: int
    end_record: int

    LINE_HEADER = "NAME     ?? LOAD UPTO START END"

    @staticmethod
    def from_bytes(b: bytes):
        if b[0] == 255:
            return None
        name, unknown, load, upto, track, record, end_track, end_record = struct.unpack(
            "<7sBHHBBBB", b
        )
        return Entry(
            name.rstrip(b"\0").decode("ascii"),
            unknown,
            load,
            upto,
            track,
            record,
            end_track,
            end_record,
        )

    def as_line(self):
        return f"{self.name:8} {self.unknown:2x} {self.load:4x} {self.upto:4x} {self.track:2} {self.record:2} {self.end_track:2} {self.end_record:2}"


def get_entries(f: BinaryIO, track_no: int = 1):
    d88 = D88(f)
    raw = d88.raw_tracks[track_no]
    entries: dict[str, Entry] = {}
    i = 0
    while i < len(raw):
        e = Entry.from_bytes(raw[i : i + 16])
        if not e:
            break
        entries[e.name] = e
        i += 16
    return entries


def get_entry_data(f: BinaryIO, entry: Entry):
    data = b""
    d88 = D88(f)
    remaining = (entry.upto + 1) - entry.load
    i = d88.get_sector_index(entry.track, entry.record)
    if i is None:
        raise ValueError(f"T{entry.track} S{entry.record} does not exist")
    while remaining > 0:
        sector = d88.sectors[i]
        raw = sector.data[:remaining]
        remaining -= len(raw)
        data += raw
        i += 1
    return data


class FileType(StrEnum):
    Binary = "bin"
    Image1bpp = "1bpp"


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("dir", description="Get D88 disk contents")
    parser.add_argument("filename")
    parser.add_argument("-l", "--list", help="list files", action="store_true")
    parser.add_argument("-x", "--extract", help="extract file name")
    parser.add_argument(
        "-t", "--type", help="file type", type=FileType, default=FileType.Binary
    )
    parser.add_argument("--width", help="image width", type=int)
    parser.add_argument("-o", "--output", help="output file name")
    args = parser.parse_args()

    with open(args.filename, "rb") as f:
        entries = get_entries(args.filename)

        if args.list:
            for e in entries.values():
                print(
                    f"{e.name:8} {e.unknown:4x} {e.load:4x} {e.upto:4x} {e.track:2} {e.record:2} {e.end_track:2} {e.end_record:2}"
                )

        if args.extract:
            entry = entries.get(args.extract)
            if not entry:
                print("Not found:", args.extract)
            else:
                raw_data = get_entry_data(args.filename, entry)
                if args.output:
                    if args.type == FileType.Image1bpp:
                        if args.width is None:
                            raise ValueError("image requires --width")
                        img = to_1bpp(raw_data, args.width, 16, 8)
                        print(
                            f"Writing: {args.output}; 1bpp, {img.width} x {img.height}"
                        )
                        img.save(args.output)
                    else:
                        print(f"Writing: {args.output}")
                        with open(args.output, "wb") as o:
                            o.write(raw_data)

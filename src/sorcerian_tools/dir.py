import struct
from dataclasses import dataclass
from enum import StrEnum

from PIL import Image

from .d88tool import D88


@dataclass
class Entry:
    name: str
    a: int
    b: int
    size: int
    track: int
    record: int
    end_track: int
    end_record: int

    @staticmethod
    def from_bytes(b: bytes):
        if b[0] == 255:
            return None
        name, _a, _b, size, track, record, end_track, end_record = struct.unpack(
            "<6shhhbbbb", b
        )
        return Entry(
            name.rstrip(b"\0").decode("ascii"),
            _a,
            _b,
            size,
            track,
            record,
            end_track,
            end_record,
        )


def dir_dump(fn: str, track_no: int = 1):
    with open(fn, "rb") as f:
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


def extract_file(fn: str, entry: Entry):
    data = b""
    with open(fn, "rb") as f:
        d88 = D88(f)
        remaining = entry.size
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


class BitIO:
    def __init__(self, data: bytes):
        self.data = data
        self.offset = 0
        self.mask = 0

    def next_bit(self):
        if self.mask == 0:
            self.byte = self.data[self.offset]
            self.offset += 1
            self.mask = 128
        r = self.byte & self.mask
        self.mask >>= 1
        return r


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
    entries = dir_dump(args.filename)

    if args.list:
        for e in entries.values():
            print(
                f"{e.name:8} {e.a:4x} {e.b:4x} {e.size:4x} {e.track:2} {e.record:2} {e.end_track:2} {e.end_record:2}"
            )

    if args.extract:
        entry = entries.get(args.extract)
        if not entry:
            print("Not found:", args.extract)
        else:
            raw_data = extract_file(args.filename, entry)
            if args.output:
                if args.type == FileType.Image1bpp:
                    if args.width is None:
                        raise ValueError("image requires --width")
                    w = args.width
                    h = (len(raw_data) * 8) // w
                    img = Image.new("P", (w, h))
                    img.putpalette([0, 0, 0, 255, 255, 255])
                    print(f"Writing: {args.output}; 1bpp, {w} x {h}")
                    tile_width = 16
                    tile_height = 8
                    tiles_across = w // tile_width
                    tiles_down = h // tile_height
                    f = BitIO(raw_data)
                    for ty in range(tiles_down):
                        for tx in range(tiles_across):
                            m = Image.new("P", (tile_width, tile_height))
                            m.putpalette([0, 0, 0, 255, 255, 255])
                            m_data: list[int] = []
                            for y in range(tile_height):
                                for x in range(tile_width):
                                    v = f.next_bit()
                                    m_data.append(1 if v else 0)

                            m.putdata(m_data)  # type: ignore
                            img.paste(m, (tx * tile_width, ty * tile_height))
                    img.save(args.output)
                else:
                    print(f"Writing: {args.output}")
                    with open(args.output, "wb") as f:
                        f.write(raw_data)

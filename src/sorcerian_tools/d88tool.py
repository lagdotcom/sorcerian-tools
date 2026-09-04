from enum import IntEnum
from typing import BinaryIO


class D88WriteProtect(IntEnum):
    Writeable = 0
    WriteProtected = 0x10


class D88Media(IntEnum):
    _2D = 0
    _2DD = 0x10
    _2HD = 0x20
    _1D = 0x30
    _1DD = 0x40


MAX_TRACKS = 164


def num(f: BinaryIO, size: int):
    return int.from_bytes(f.read(size), "little")


class D88Header:
    def __init__(self, f: BinaryIO):
        self.name = f.read(17)
        self.reserved = f.read(9)
        self.write_protect = D88WriteProtect(f.read(1)[0])
        self.media = D88Media(f.read(1)[0])
        self.size = num(f, 4)
        self.track_pointers = [num(f, 4) for _ in range(MAX_TRACKS)]

    def show(self):
        name = self.name.rstrip(b"\0").decode("ascii") or "(None)"
        print(f"Name: {name} -- {self.write_protect.name}, {self.media.name}")

        used = 0
        for ptr in self.track_pointers:
            if ptr > 0:
                used += 1
        print(f"  Size: {self.size} bytes -- Used Tracks: {used}/{MAX_TRACKS}")


class D88Density(IntEnum):
    DoubleDensity = 0
    SingleDensity = 0x40


class D88DDAM(IntEnum):
    Normal = 0
    Deleted = 0x10


class D88FDC(IntEnum):
    Normal = 0
    DataCRCError = 0xB0


class D88Sector:
    def __init__(self, f: BinaryIO, track: int):
        self.track_no = track
        self.cylinder = f.read(1)[0]
        self.head = f.read(1)[0]
        self.record = f.read(1)[0]
        self.sector_size = 128 << f.read(1)[0]
        self.sectors = num(f, 2)
        self.density = D88Density(f.read(1)[0])
        self.ddam = D88DDAM(f.read(1)[0])
        self.fdc = D88FDC(f.read(1)[0])
        self.reserved = f.read(5)
        self.data_size = num(f, 2)
        self.data = f.read(self.data_size)

    def show(self):
        if self.sector_size == self.data_size:
            size = str(self.sector_size)
        else:
            size = f"{self.sector_size} or {self.data_size}"
        print(
            f"-- C{self.cylinder:2} H{self.head} S{self.record:2}: {size} bytes -- {self.density.name}, {self.ddam.name}, {self.fdc.name}"
        )

    def __lt__(self, o: "D88Sector"):
        if self.cylinder > o.cylinder:
            return False
        if self.head > o.head:
            return False
        return self.record < o.record


class D88:
    def __init__(self, f: BinaryIO, debug: bool = False):
        f.seek(0, 2)
        self.total_size = f.tell()

        f.seek(0)
        self.header = D88Header(f)
        if debug:
            self.header.show()

        self.read_tracks(f, debug)

    def read_tracks(self, f: BinaryIO, debug: bool = False):
        self.sectors: list[D88Sector] = []
        track_count = 0
        self.raw_tracks: list[bytes] = []
        for track_no in range(MAX_TRACKS):
            track = b""
            ptr = self.header.track_pointers[track_no]
            if ptr > 0:
                track_count += 1
                f.seek(ptr)
                if debug:
                    print(f"- Track {track_no} @{ptr:x}")
                if track_no == MAX_TRACKS:
                    end_track = self.total_size
                else:
                    next_ptr = self.header.track_pointers[track_no + 1]
                    if next_ptr == 0:
                        end_track = self.total_size
                    else:
                        end_track = next_ptr
                while f.tell() < end_track:
                    sector = D88Sector(f, track_no)
                    if debug:
                        sector.show()
                    self.sectors.append(sector)
                    track += sector.data
            self.raw_tracks.append(track)
        if debug:
            print(f"Read {len(self.sectors)} sectors in {track_count} tracks")

    def get_sector_index(self, track_no: int, record: int):
        for i, sector in enumerate(self.sectors):
            if sector.track_no == track_no and sector.record == record:
                return i

    def dump(self, fn: str):
        with open(fn, "wb") as f:
            f.writelines(sector.data for sector in sorted(self.sectors))
        print("Wrote:", fn)


def examine(d88_fn: str, debug: bool, output_fn: str | None):
    with open(d88_fn, "rb") as f:
        disk = D88(f, debug)
        if output_fn:
            disk.dump(output_fn)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        "d88tool", description="Manipulates D88 disk files"
    )
    parser.add_argument("filename")
    parser.add_argument("-d", "--debug", action="store_true", help="show debug info")
    parser.add_argument("-o", "--output", help="write combined sectors to new file")
    args = parser.parse_args()
    examine(args.filename, args.debug, args.output)

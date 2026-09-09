import struct
from dataclasses import dataclass
from typing import TextIO

from .text import translate_multiline


@dataclass
class HeaderEntry:
    name_ptr: int
    row: int
    width: int
    id: int
    unknown_1: int
    max_party: int
    extra_id: int
    unknown_2: bytes

    @staticmethod
    def from_bytes(b: bytes):
        name_ptr, row, width, id, u1, max_party, extra_id = struct.unpack(
            "<HBBHHBB", b[:10]
        )
        return HeaderEntry(
            name_ptr,
            row,
            width,
            id,
            u1,
            max_party,
            extra_id,
            b[10:],
        )

    def write(self, o: TextIO):
        extra = "---" if self.extra_id == 0 else f"{self.extra_id:03}"
        o.write(
            f"[{self.id:03}/{extra}] @{self.name_ptr:4x} r{self.row} w{self.width} max{self.max_party} {self.unknown_1:4x} {self.unknown_2.hex(' ')}\n"
        )


@dataclass
class BestiaryEntry:
    pointers: list[int]
    text: str

    @staticmethod
    def from_bytes(b: bytes):
        pointers = struct.unpack("<HHHHHHHHHHHHHHHH", b[:32])
        return BestiaryEntry(
            list(pointers),
            translate_multiline(b[32:], b"\xff"),
        )

    def write(self, o: TextIO):
        o.write(" ".join([f"{n:04x}" for n in self.pointers]) + "\n")
        o.write(self.text + "\n\n")


@dataclass
class Menu:
    header: list[HeaderEntry]
    names: str
    descriptions: list[str]
    bestiary: list[BestiaryEntry]

    @staticmethod
    def from_bytes(b: bytes):
        header = [
            HeaderEntry.from_bytes(b[0x00:0x10]),
            HeaderEntry.from_bytes(b[0x10:0x20]),
            HeaderEntry.from_bytes(b[0x20:0x30]),
            HeaderEntry.from_bytes(b[0x30:0x40]),
            HeaderEntry.from_bytes(b[0x40:0x50]),
        ]
        names = translate_multiline(b[0x50:0x100])
        descriptions = [
            translate_multiline(b[0x100:0x200]),
            translate_multiline(b[0x200:0x300]),
            translate_multiline(b[0x300:0x400]),
            translate_multiline(b[0x400:0x500]),
            translate_multiline(b[0x500:0x600]),
        ]

        bestiary: list[BestiaryEntry] = []
        i = 0x600
        while i < len(b):
            bestiary.append(BestiaryEntry.from_bytes(b[i : i + 0x400]))
            i += 0x400

        return Menu(header, names, descriptions, bestiary)

    def write(self, o: TextIO):
        o.write("-- HEADER\n")
        for h in self.header:
            h.write(o)

        o.write(f"\n-- NAMES\n{self.names}\n")

        o.write("\n-- DESCRIPTIONS\n")
        o.writelines(d + "\n\n" for d in self.descriptions)

        o.write("-- BESTIARY\n")
        for b in self.bestiary:
            b.write(o)

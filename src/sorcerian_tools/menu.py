from dataclasses import dataclass
from typing import TextIO

from .text import translate_multiline


@dataclass
class HeaderEntry:
    unknown: bytes

    @staticmethod
    def from_bytes(b: bytes):
        return HeaderEntry(b)

    def write(self, o: TextIO):
        o.write(self.unknown.hex(" ") + "\n")


@dataclass
class BestiaryEntry:
    unknown: bytes
    text: str

    @staticmethod
    def from_bytes(b: bytes):
        return BestiaryEntry(b[:32], translate_multiline(b[32:], b"\xff"))

    def write(self, o: TextIO):
        o.write(self.unknown.hex(" ") + "\n")
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
        bestiary = [
            BestiaryEntry.from_bytes(b[0x0600:0x0A00]),
            BestiaryEntry.from_bytes(b[0x0A00:0x0E00]),
            BestiaryEntry.from_bytes(b[0x0E00:0x1200]),
            BestiaryEntry.from_bytes(b[0x1200:0x1600]),
            BestiaryEntry.from_bytes(b[0x1600:]),
        ]

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

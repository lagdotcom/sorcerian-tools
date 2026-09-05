from dataclasses import dataclass

from .text import translate
from .translation import get_generic_translations


@dataclass
class Treasure:
    name: str
    unknown: bytes

    LINE_HEADER = (
        "?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? ?? NAME"
    )

    @staticmethod
    def from_bytes(b: bytes):
        name_bytes = b[:10]
        unknown = b[10:]
        return Treasure(translate(name_bytes.rstrip(b"\0")), unknown)

    def as_line(self):
        base = f"{self.unknown.hex(sep=' ')} {self.name}"
        translated = get_generic_translations().get(self.name)
        if translated:
            base += f" ({translated})"
        return base

from collections import deque
from collections.abc import Callable
from dataclasses import dataclass
from struct import unpack
from typing import TextIO

from .text import translate_until_eof

Z80_OPS = {
    0x7E: "=",
    0x86: "+=",
    0x96: "-=",
    0xC2: "!=",
    0xCA: "==",
    0xD2: ">=",
    0xDA: "<",
}

HERB_NAMES = ["verbena", "lavender", "sage", "hyssop", "savoury"]


@dataclass
class ArgType:
    name: str
    type: str
    size: int
    is_ref: bool = False

    def format(self, value: int, base: int, raw: bytes, names: dict[int, str]):
        if self.type == "text":
            return translate_until_eof(raw[value - base :])
        elif self.type == "code":
            return Z80_OPS.get(value, str(value))
        elif self.type == "area":
            return f"area{value}"
        elif self.type == "flag":
            return f"flag_{value}"
        elif self.type == "herb":
            return HERB_NAMES[value]
        elif self.is_ref:
            ref = names.get(value, f"{value:04x}")
            return f"[{ref}]"
        else:
            return str(value)


arg_byte = ArgType("unknown", "unknown", 1)
arg_area = ArgType("area", "area", 1)
arg_code = ArgType("op", "code", 1)
arg_flag = ArgType("flag", "flag", 1)
arg_herb = ArgType("herb", "herb", 1)
arg_word = ArgType("unknown", "unknown", 2)
arg_ref = ArgType("unknown", "unknown", 2, True)
arg_text = ArgType("text", "text", 2, True)


@dataclass
class OpType:
    name: str
    code: int
    args: list[ArgType]
    keep_going: bool = True


@dataclass
class Op:
    type: OpType
    values: list[int]

    def format(self, base: int, raw: bytes, names: dict[int, str]):
        values = [
            arg.format(self.values[i], base, raw, names)
            for i, arg in enumerate(self.type.args)
        ]
        return f"{self.type.name} {' '.join(values)}"


CHECK_OPS = {
    0x00: OpType("end", 0, [], keep_going=False),
    0x01: OpType("if", 1, [arg_ref, arg_code, arg_byte]),
    0x02: OpType("if.is_set", 2, [arg_flag]),
    0x03: OpType("if.is_clear", 3, [arg_flag]),
    0x04: OpType("if.at_tile", 4, [arg_byte]),
    0x05: OpType("if.entered", 5, []),
}


def get_check_op(n: int):
    return (
        OpType(f"if.at {(n - 0x80)},", 1, [arg_byte]) if n & 0x80 else CHECK_OPS.get(n)
    )


APPLY_OPS = {
    0x00: OpType("end", 0, [], keep_going=False),
    0x01: OpType("say", 1, [arg_text]),
    0x02: OpType("warp", 2, [arg_byte, arg_area, arg_byte, arg_byte]),
    0x03: OpType("store", 3, [arg_ref, arg_code, arg_byte]),
    0x04: OpType("load_script", 4, [arg_word, arg_word]),
    0x05: OpType("trap?", 5, [arg_byte, arg_byte]),
    0x06: OpType("continue?", 6, [arg_byte]),
    0x07: OpType("call", 7, [arg_word]),
    0x08: OpType("change_tiles", 8, [arg_byte, arg_byte]),
    0x09: OpType("music", 9, [arg_byte]),
    0x0A: OpType("finish_adventure", 10, []),
    0x0B: OpType("op_0b", 11, [arg_byte]),
    0x0C: OpType("take", 12, [arg_byte]),
    0x0D: OpType("drop", 13, [arg_byte]),
    0x0E: OpType("clear_flag", 14, [arg_flag]),
    0x0F: OpType("set_flag", 15, [arg_flag]),
    0x10: OpType("redraw", 16, []),
    0x11: OpType("op_11", 17, [arg_byte]),
    0x12: OpType("open", 18, [arg_ref]),
    0x13: OpType("close", 19, [arg_ref]),
    0x14: OpType("spawn", 20, [arg_byte, arg_byte]),
    0x15: OpType("get_herb", 21, [arg_herb]),
    0x16: OpType("experience", 22, [arg_word]),
    0x17: OpType("gold", 23, [arg_byte, arg_byte]),
    0x18: OpType("scroll", 24, [arg_byte]),
    0x19: OpType("wait_for_key", 25, []),
    0x1A: OpType("wait", 26, [arg_byte]),
    0x1B: OpType("op_1b", 27, []),
    0x1C: OpType("op_1c", 28, []),
    0x1D: OpType("confirm", 29, []),
    0x1E: OpType("goto", 30, [arg_ref], keep_going=False),
    0x1F: OpType("nop", 31, []),
}


def get_apply_op(n: int):
    return APPLY_OPS.get(n)


EOF_OP = OpType("!!eof", -1, [], keep_going=False)


def get_next_op(raw: bytes, offset: int, getter: Callable[[int], OpType | None]):
    if len(raw) <= offset:
        type = EOF_OP
    else:
        op_byte = raw[offset]
        offset += 1
        type = getter(op_byte) or OpType(
            f"unknown_{op_byte:02x}", op_byte, [], keep_going=False
        )
    values = list[int]()
    for arg in type.args:
        value = int.from_bytes(raw[offset : offset + arg.size], "little")
        values.append(value)
        offset += arg.size
    op = Op(type, values)
    return op, offset, type.keep_going


SCRIPT_NAMES = ["left", "right", "down", "up"]


@dataclass
class ScenarioEntry:
    SIZE_OF = 12

    map_id: int
    unknown_2: int
    unknown_3: int
    ptr_left: int
    ptr_right: int
    ptr_down: int
    ptr_up: int

    @property
    def pointers(self):
        return [self.ptr_left, self.ptr_right, self.ptr_down, self.ptr_up]

    @property
    def valid_pointers(self):
        return [n for n in self.pointers if n > 0]

    @staticmethod
    def from_bytes(b: bytes):
        map_id, unknown_2, unknown_3, ptr_4, ptr_6, ptr_8, ptr_a = unpack(
            "<HBBHHHH", b[:12]
        )
        return ScenarioEntry(map_id, unknown_2, unknown_3, ptr_4, ptr_6, ptr_8, ptr_a)


@dataclass
class Scenario:
    entries: list[ScenarioEntry]
    names: dict[int, str]
    base: int
    start_bytecode: int
    raw: bytes

    @staticmethod
    def from_bytes(raw: bytes, base: int):
        offset = 0
        data_pointer = 0xFFFF
        entries = list[ScenarioEntry]()
        index = 0
        names = dict[int, str]()
        while (base + offset) < data_pointer:
            entry = ScenarioEntry.from_bytes(raw[offset : offset + 12])
            entries.append(entry)
            offset += ScenarioEntry.SIZE_OF

            for j, ptr in enumerate(entry.pointers):
                if ptr > 0:
                    names[ptr] = f"area{index}_{SCRIPT_NAMES[j]}"

            data_pointer = min(data_pointer, *entry.valid_pointers)
            index += 1

        return Scenario(entries, names, base, offset, raw)

    def write(self, o: TextIO):
        for area_index, e in enumerate(self.entries):
            if area_index > 0:
                o.write("\n\n")

            o.write(
                f"--- area{area_index}, M_{e.map_id:03}, {e.unknown_2}, {e.unknown_3}\n"
            )

            check = deque(e.valid_pointers)
            while len(check):
                addr = check.popleft()
                if addr in self.names:
                    o.write(f"\n{self.names[addr]}:\n")

                offset = addr - self.base
                next_block = self.raw[offset]
                offset += 1
                if next_block > 0:
                    destination = addr + next_block
                    label = f"j_{destination:4x}"
                    self.names[destination] = label
                    # o.write(f"  (next block: {label})\n")
                    check.appendleft(destination)

                run = True
                while run:
                    op, offset, run = get_next_op(self.raw, offset, get_check_op)
                    if op.type.code != 0:
                        o.write(f"  {op.format(self.base, self.raw, self.names)}\n")

                run = True
                while run:
                    op, offset, run = get_next_op(self.raw, offset, get_apply_op)
                    if op.type.code != 0:
                        o.write(f"  {op.format(self.base, self.raw, self.names)}\n")

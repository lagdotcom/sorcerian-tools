from ctypes import c_ubyte as u8
from ctypes import c_ushort as u16

from PIL import Image


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


DEFAULT_HEIGHT_SCALE = 2


def to_1bpp(
    data: bytes,
    w: int,
    tile_width: int,
    tile_height: int,
    height_scale: int = DEFAULT_HEIGHT_SCALE,
):
    h = (len(data) * 8) // w
    img = Image.new("1", (w, h * height_scale))
    tiles_across = w // tile_width
    tiles_down = h // tile_height
    f = BitIO(data)
    m = Image.new("1", (tile_width, tile_height * height_scale))
    for ty in range(tiles_down):
        for tx in range(tiles_across):
            m_data: list[int] = []
            for _ in range(tile_height):
                for _ in range(tile_width):
                    v = f.next_bit()
                    m_data.append(1 if v else 0)
                for _ in range(height_scale - 1):
                    m_data.extend(m_data[-tile_width:])

            m.putdata(m_data)  # type: ignore
            img.paste(m, (tx * m.width, ty * m.height))
    return img


def CONCAT11(a: int, b: int):
    hi = u8(a)
    lo = u8(b)
    return u16(hi.value << 8 | lo.value)


type Palette = list[tuple[int, int, int]]
# from PRNO0:13c7
# format is _X___ggg __rrrbbb
DEFAULT_PALETTE: Palette = [
    (0, 0, 0),
    (0, 0, 182),
    (218, 0, 0),
    (255, 145, 72),
    (0, 182, 0),
    (0, 182, 255),
    (255, 218, 0),
    (255, 255, 218),
]


def to_planar_fmt(
    orig: bytes,
    palette: Palette = DEFAULT_PALETTE,
    height_scale: int = DEFAULT_HEIGHT_SCALE,
):
    raw = list(orig)

    # u0 = int.from_bytes(raw[0:2], "little")
    planar_rows = u16(int.from_bytes(raw[2:4], "little"))
    row_width = u8(raw[4])
    width = row_width.value
    height = planar_rows.value // 3
    # print(
    #     f"planar_rows={planar_rows.value} rows={planar_rows.value // 3} width={row_width.value}"
    # )

    memory = [0] * 0x10000
    for o, b in enumerate(orig):
        memory[o + 0x2000] = b

    def read(src: u16):
        r = memory[src.value]
        # print(f"read ({r:02x}) from [{src.value:04x}]")
        return r

    def read_signed(src: u16):
        r = int.from_bytes(memory[src.value : src.value + 1], signed=True)
        # print(f"read s({r}) from [{src.value:04x}]")
        return r

    def write(dst: u16, v: u8):
        # print(f"[{dst.value:04x}] <-- {v.value:02x}")
        memory[dst.value] = v.value

    def copy(dst: u16, src: u16):
        v = read(src)
        # print(f"[{dst.value:04x}] <-- [{src.value:04x}] ({v:02x})")
        memory[dst.value] = v
        return v

    byte = u8()
    cVar3 = u8()
    cVar5 = u8()
    ptr = u16()
    decA = u8(0x40)
    src = u16(0x2006)
    srcNext = u16()
    bRam1282 = u8(0xFF)
    sVar4 = u16()
    bVar2 = u8()
    puVar8 = u16()
    while True:
        is_high = 0xCF < decA.value
        decA.value += 0x30
        if is_high:
            ptr.value += 0x50
            decA.value = 0x70

        srcNext.value = src.value + 1
        byte.value = read(src) & 0x7F
        cVar3.value = ptr.value >> 8
        # print(
        #     f"plane={'B' if decA.value == 0x70 else 'R' if decA.value == 0xA0 else 'G'} byte={byte.value:02x}"
        # )
        if -1 < read_signed(src):
            src = CONCAT11(decA.value + cVar3.value, ptr.value)
            cVar3.value = row_width.value

            while True:
                cVar5.value = byte.value - cVar3.value
                # print(f"cVar5 = {byte.value} - {cVar3.value} = {cVar5.value}")
                bVar2.value = read(srcNext)
                srcNext.value += 1
                while True:
                    write(src, bVar2)
                    src.value += 1
                    byte.value -= 1

                    if byte.value == 0:
                        break

                kill_run = False
                while True:
                    cVar3.value = -cVar5.value
                    # print(f"cVar5={cVar5.value} cVar3={cVar3.value}")
                    if cVar3.value == 0:
                        kill_run = True
                        break

                    bVar2.value = read(srcNext)
                    bVar2_s = read_signed(srcNext)
                    # print(f"bVar2={bVar2.value:02x} signed={bVar2_s}")
                    srcNext.value += 1
                    byte.value = bVar2.value & 0x7F
                    if -1 < bVar2_s:
                        break

                    cVar5.value += byte.value
                    while True:
                        bVar2.value = copy(src, srcNext)
                        srcNext.value += 1
                        src.value += 1
                        byte.value -= 1

                        if byte.value == 0:
                            break

                if kill_run:
                    break
        else:
            cVar5.value = 0
            bRam1282.value = byte.value
            if 0x29 < byte.value:
                cVar5.value = 0x30
                bRam1282.value = byte.value - 0x2A
                if 0x29 < bRam1282.value:
                    cVar5.value = 0x60
                    bRam1282.value = byte.value + 0xAC
            # print(
            #     f"byte={byte.value:02x} cVar5={cVar5.value:02x} bRam1282={bRam1282.value}"
            # )

            bVar2.value = read(srcNext)
            srcNext.value = src.value + 2

            byte.value = (bVar2.value << 7) >> 1 | (bVar2.value >> 1) << 7
            uVar6 = CONCAT11(bVar2.value >> 2, byte.value)
            puVar9 = u16(
                uVar6.value
                + 0x7000
                + CONCAT11(
                    (
                        (bVar2.value >> 3 | (1 if (0x8FFF < uVar6.value) else 0) << 7)
                        >> 1
                    )
                    + cVar5.value,
                    (byte.value >> 1 | (bVar2.value >> 2) << 7) >> 1
                    | (bVar2.value >> 3) << 7,
                ).value
            )
            # print(
            #     f"puVar9={puVar9.value:04x} bVar2={bVar2.value:02x} uVar6={uVar6.value:02x} cVar5={cVar5.value:02x} byte={byte.value:02x}"
            # )
            puVar7 = CONCAT11(decA.value + cVar3.value, ptr.value)
            sVar4.value = row_width.value
            puVar8.value = puVar7.value
            while True:
                copy(puVar8, puVar9)
                puVar8.value += 1
                puVar9.value += 1
                sVar4.value -= 1

                if sVar4.value == 0:
                    break

            cVar3.value = bRam1282.value
            # print(f"puVar7={puVar7.value:04x} cVar3={cVar3.value}")
            while cVar3.value != 0:
                bVar2.value = read(srcNext)
                srcNext.value += 1

                cVar5.value = 1
                byte.value = bVar2.value
                if 0x4F < byte.value:
                    cVar5.value = 2
                    byte.value = bVar2.value + 0xB0
                    if 0x4F < byte.value:
                        cVar5.value = 3
                        byte.value = bVar2.value + 0x60

                src.value = puVar7.value + byte.value
                while True:
                    byte.value = read(srcNext)
                    srcNext.value += 1
                    write(src, byte)
                    src.value += 1
                    cVar3.value -= 1
                    cVar5.value -= 1

                    if cVar5.value == 0:
                        break

        planar_rows.value -= 1
        src.value = srcNext.value
        if planar_rows.value == 0:
            img = Image.new("P", (width * 8, height * height_scale))
            img.putpalette([n for rgb in palette for n in rgb])
            data = list[int]()
            i = 0
            for _ in range(height):
                row = list[int]()
                for _ in range(width):
                    b = memory[0x7000 + i]
                    r = memory[0xA000 + i]
                    g = memory[0xD000 + i]
                    mask = 0x80
                    for _ in range(8):
                        index = 0
                        if b & mask:
                            index += 1
                        if r & mask:
                            index += 2
                        if g & mask:
                            index += 4
                        row.append(index)
                        mask >>= 1
                    i += 1

                for _ in range(height_scale):
                    data.extend(row)
            img.putdata(data)  # type: ignore
            return img

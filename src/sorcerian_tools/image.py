from ctypes import c_ubyte as u8
from ctypes import c_ushort as u16

from PIL import Image, ImageDraw

from .contents import ContentsEntry


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
    e: ContentsEntry,
    height_scale: int = DEFAULT_HEIGHT_SCALE,
):
    if e.size is None or e.tile_size is None:
        raise ValueError(f"! {e.filename} needs size and tile_size")

    w, h = e.size
    tile_width, tile_height = e.tile_size

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
    # TODO convert this into actual python
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


def wind_xy(w: int, h: int):
    order = list[tuple[int, int]]()
    step = -1
    for x in range(w):
        for y in range(h)[::step]:
            order.append((x, y))
        step = -step
    return order


class SpriteMode:
    def __init__(self, w: int, h: int, order: list[tuple[int, int]] | None = None):
        self.width = w
        self.height = h
        self.order = order or wind_xy(w, h)


SPRITE_MODES = {
    "1x1": SpriteMode(1, 1, [(0, 0)]),
    "2x2": SpriteMode(2, 2),
    "2x3": SpriteMode(2, 3),
    "3x2": SpriteMode(3, 2, [(0, 1), (1, 1), (2, 1), (2, 0), (1, 0), (0, 0)]),
    "1x2": SpriteMode(1, 2, [(0, 0), (1, 0)]),
    "3x1": SpriteMode(3, 1),
    "6x6": SpriteMode(6, 6),
    "8x8": SpriteMode(8, 8),
}

SPRITE_MODE_INDICES = ["1x1", "2x2", "2x3", "3x2", "1x2", "3x1"]


def to_sprite_fmt(
    data: bytes,
    e: ContentsEntry,
    pat_data: bytes | None = None,
    palette: Palette = DEFAULT_PALETTE,
    height_scale: int = DEFAULT_HEIGHT_SCALE,
):
    if e.size is None or e.tile_size is None:
        raise ValueError(f"! {e.filename} needs size and tile_size")

    w, h = e.size
    tile_width, tile_height_base = e.tile_size

    parsed_palette = [n for rgb in palette for n in rgb]
    tiles_per_row = w // tile_width
    tile_rows = h // tile_height_base
    p = tile_width * tile_height_base // 8
    tile_height = tile_height_base * height_scale

    tiles: list[Image.Image] = []

    i = 0
    for _ in range(tile_rows):
        for _ in range(tiles_per_row):
            bb = BitIO(data[i : i + p])
            rb = BitIO(data[i + p : i + p * 2])
            gb = BitIO(data[i + p * 2 : i + p * 3])
            i += p * (4 if e.has_mask else 3)

            m = Image.new("P", (tile_width, tile_height))
            m.putpalette(parsed_palette)  # type: ignore
            tiles.append(m)
            m_data: list[int] = []
            for _ in range(tile_height_base):
                for _ in range(tile_width):
                    b = bb.next_bit()
                    r = rb.next_bit()
                    g = gb.next_bit()

                    ix = 0
                    if b:
                        ix += 1
                    if r:
                        ix += 2
                    if g:
                        ix += 4

                    m_data.append(ix)

                for _ in range(height_scale - 1):
                    m_data.extend(m_data[-tile_width:])

            m.putdata(m_data)  # type: ignore

    if e.patterns and pat_data:
        if e.patterns.mode == "multi":
            pat_images: list[Image.Image] = []
            big_mode = False
            total_width = 0
            total_height = 0
            i = 0
            while i < len(pat_data):
                mode_byte = pat_data[i]
                i += 1
                if mode_byte == 6 or big_mode:
                    big_mode = True
                    indices = pat_data[i : i + 36]
                    mode = SPRITE_MODES["6x6"]
                    i += 63
                else:
                    indices = pat_data[i : i + 6]
                    mode = SPRITE_MODES[SPRITE_MODE_INDICES[mode_byte]]
                    i += 7

                pat_img = Image.new(
                    "P",
                    (mode.width * tile_width, mode.height * tile_height),
                )
                total_width = max(total_width, pat_img.width)
                total_height += pat_img.height
                pat_img.putpalette(parsed_palette)  # type: ignore
                pat_images.append(pat_img)

                # print(f"-- {mode_byte} {mode} {indices}")
                for j, (c, r) in enumerate(mode.order):
                    n = indices[j]
                    # print(f"pat: {j} {c} {r}")
                    n_value = n - e.patterns.base
                    if n_value >= 0 and n_value < len(tiles):
                        pat_img.paste(tiles[n_value], (c * tile_width, r * tile_height))

            img = Image.new("P", (total_width + 16, total_height))
            img.putpalette(parsed_palette)  # type: ignore
            dr = ImageDraw.Draw(img)
            y = 0
            for pi, pat_img in enumerate(pat_images):
                dr.text((0, y), str(pi), fill=(255, 255, 255))
                img.paste(pat_img, (16, y))
                y += pat_img.height
        else:
            mode = SPRITE_MODES.get(e.patterns.mode)
            if mode is None:
                raise ValueError(f"unknown sprite pattern mode: {e.patterns.mode}")
            pat_width = mode.width * tile_width
            pat_height = mode.height * tile_height
            img = Image.new("P", (pat_width, pat_height * e.patterns.count))
            img.putpalette(parsed_palette)  # type: ignore
            i = e.patterns.offset
            x = 0
            y = 0
            # print(patterns, pat_data.hex())
            for _ in range(e.patterns.count):
                for c, r in mode.order:
                    n = pat_data[i]
                    i += 1
                    dx = x + c * tile_width
                    dy = y + r * tile_height
                    n_value = n - e.patterns.base
                    # print(f"{n_value} at {dx},{dy}")
                    if n_value >= 0 and n_value < len(tiles):
                        img.paste(tiles[n_value], (dx, dy))
                # print(f"pattern {pn}: {si} to {ei}")
                y += pat_height

    else:
        img = Image.new("P", (w, h * height_scale))
        img.putpalette(parsed_palette)  # type: ignore

        i = 0
        y = 0
        for _ in range(tile_rows):
            x = 0
            for _ in range(tiles_per_row):
                img.paste(tiles[i], (x, y))
                i += 1
                x += tile_width
            y += tile_height

    return img

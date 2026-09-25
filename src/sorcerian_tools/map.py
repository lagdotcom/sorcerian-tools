from collections.abc import Callable
from dataclasses import dataclass
from io import BytesIO

from PIL import Image, ImageDraw

from .contents import ContentsEntry
from .image import DEFAULT_HEIGHT_SCALE

ROWS = 12
COLS = 128

CELL_COUNT = ROWS * COLS
TILE_COUNT = 60
SUB_ROWS = 2
SUB_COLS = 2
TILE_PARTS = SUB_COLS * SUB_ROWS
ANIM_COUNT = 4
ANIM_FRAMES = 5

SUB_TILE_ORDER = [(0, 0), (0, 1), (1, 0), (1, 1)]

ZOOM = 16


type RGB = tuple[int, int, int]


@dataclass
class SubTileDrawer:
    tile_width: int
    tile_height: int
    draw: Callable[[Image.Image, ImageDraw.ImageDraw, int, int, int, bool], None]


def alloc(raw: bytes, size: int):
    return raw[size:], raw[:size]


class MapFile:
    def __init__(self, raw: bytes):
        b = BytesIO(raw)

        self.columns = [b.read(ROWS) for _ in range(COLS)]
        self.sub_tiles = [b.read(TILE_PARTS) for _ in range(TILE_COUNT)]
        self.anim_tiles = [
            [b.read(TILE_PARTS) for _ in range(ANIM_COUNT)] for _ in range(ANIM_FRAMES)
        ]

    def draw(self, draw_sub: SubTileDrawer):
        img = Image.new(
            "RGB",
            (
                COLS * SUB_COLS * draw_sub.tile_width,
                ROWS * SUB_ROWS * draw_sub.tile_height,
            ),
        )
        dr = ImageDraw.Draw(img)
        for tx, col in enumerate(self.columns):
            bx = tx * draw_sub.tile_width * SUB_COLS
            for ty, tile_id in enumerate(col):
                by = ty * draw_sub.tile_height * SUB_ROWS
                sub = (
                    self.sub_tiles[tile_id]
                    if tile_id < TILE_COUNT
                    else self.anim_tiles[0][tile_id - TILE_COUNT]
                )
                si = 0
                for si, (sx, sy) in enumerate(SUB_TILE_ORDER):
                    x = bx + sx * draw_sub.tile_width
                    y = by + sy * draw_sub.tile_height
                    sub_id = sub[si]
                    draw_sub.draw(img, dr, x, y, sub_id, tile_id >= TILE_COUNT)

        return img


def get_raw_sub_tile_drawer(zoom: int, c_solid: RGB, c_text: RGB, c_animated_text: RGB):
    def draw_sub_tile(
        img: Image.Image,
        dr: ImageDraw.ImageDraw,
        x: int,
        y: int,
        id: int,
        is_animated: bool,
    ):
        if id & 0x80:
            dr.rectangle((x, y, x + zoom, y + zoom), fill=c_solid)
        dr.text(
            (x + 1, y + 1),
            f"{id & 0x7F:2x}",
            fill=c_animated_text if is_animated else c_text,
        )

    return SubTileDrawer(zoom, zoom, draw_sub_tile)


def get_tile_set_drawer(
    e: ContentsEntry,
    set: Image.Image,
    height_scale: int = DEFAULT_HEIGHT_SCALE,
):
    if e.size is None or e.tile_size is None:
        raise ValueError(f"{e.filename} does not have size and tile_size")
    tw, raw_th = e.tile_size
    th = raw_th * height_scale
    tiles_per_row = e.size[0] // tw

    def draw_sub_tile(
        img: Image.Image,
        dr: ImageDraw.ImageDraw,
        x: int,
        y: int,
        id: int,
        is_animated: bool,
    ):
        row = (id & 0x7F) // tiles_per_row
        col = (id & 0x7F) % tiles_per_row
        tx = col * tw
        ty = row * th
        tile = set.crop((tx, ty, tx + tw, ty + th))
        img.paste(tile, (x, y))

    return SubTileDrawer(tw, th, draw_sub_tile)


def render_map_raw(raw: bytes, tile_set: tuple[ContentsEntry, Image.Image] | None):
    map = MapFile(raw)
    drawer = (
        get_tile_set_drawer(*tile_set)
        if tile_set
        else get_raw_sub_tile_drawer(16, (64, 64, 64), (255, 255, 255), (255, 255, 0))
    )
    return map.draw(drawer)

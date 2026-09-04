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


def to_1bpp(data: bytes, w: int, tile_width: int, tile_height: int):
    h = (len(data) * 8) // w
    img = Image.new("P", (w, h))
    img.putpalette([0, 0, 0, 255, 255, 255])
    tiles_across = w // tile_width
    tiles_down = h // tile_height
    f = BitIO(data)
    for ty in range(tiles_down):
        for tx in range(tiles_across):
            m = Image.new("P", (tile_width, tile_height))
            m.putpalette([0, 0, 0, 255, 255, 255])
            m_data: list[int] = []
            for _ in range(tile_height):
                for _ in range(tile_width):
                    v = f.next_bit()
                    m_data.append(1 if v else 0)

            m.putdata(m_data)  # type: ignore
            img.paste(m, (tx * tile_width, ty * tile_height))
    return img

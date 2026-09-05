import os
from pathlib import Path

from .contents import get_empty_contents_toml, load_content_tomls
from .d88tool import D88
from .dir import Entry, get_entries, get_entry_data
from .hash import get_all_disk_files, get_sha1
from .image import to_1bpp
from .menu import Menu
from .treasure import Treasure

if __name__ == "__main__":
    tomls = load_content_tomls()
    d88s = list(get_all_disk_files())
    out_dir = Path("out")
    for fn in d88s:
        sha1 = get_sha1(fn)
        toml = tomls.get(sha1)
        if toml:
            print(f"{fn}: {toml.disk}")
        else:
            print(f"{fn}: no hash match")
            toml = get_empty_contents_toml(fn, sha1)
        with open(fn, "rb") as f:
            dir = out_dir / toml.toml_name
            if not dir.exists():
                os.makedirs(dir)
            d88 = D88(f)

            listing = get_entries(f, toml.listing.start[0])
            lfn = dir / "listing.txt"
            print(f"> {lfn}", end="... ")
            with open(lfn, "w") as o:
                o.write(Entry.LINE_HEADER + "\n")
                o.writelines([e.as_line() + "\n" for e in listing.values()])
            print("OK")

            for e in toml.entries:
                ptr = listing.get(e.filename)
                if ptr is None:
                    print(f"! could not find {e.filename}")
                    continue

                if e.type == "text":
                    ofn = dir / (e.filename + ".txt")
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        o.write(get_entry_data(f, ptr).decode(e.encoding or "ascii"))
                    print("OK")
                elif e.type == "menu":
                    ofn = dir / (e.filename + ".txt")
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        m = Menu.from_bytes(get_entry_data(f, ptr))
                        m.write(o)
                    print("OK")
                elif e.type == "treasure":
                    ofn = dir / (e.filename + ".txt")
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        o.write(Treasure.LINE_HEADER + "\n")
                        data = get_entry_data(f, ptr)
                        for i in range(0, len(data), 32):
                            tr = Treasure.from_bytes(data[i : i + 32])
                            o.write(tr.as_line() + "\n")
                    print("OK")
                elif e.type == "image" and e.format == "1bpp":
                    if e.size is None or e.tile_size is None:
                        print(f"! {e.filename} needs size and tile_size")
                        continue
                    img = to_1bpp(
                        get_entry_data(f, ptr),
                        e.size[0],
                        e.tile_size[0],
                        e.tile_size[1],
                    )
                    ifn = dir / (e.filename + ".png")
                    print(f"> {ifn}", end="... ")
                    img.save(ifn)
                    print("OK")
                else:
                    ofn = dir / (e.filename + ".bin")
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "wb") as o:
                        o.write(get_entry_data(f, ptr))
                    print("OK")

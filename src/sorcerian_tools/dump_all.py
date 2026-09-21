import os
from pathlib import Path

from .contents import get_empty_contents_toml, load_content_tomls
from .d88tool import D88
from .dir import Entry, get_entries, get_entry_data
from .hash import get_all_disk_files, get_sha1
from .image import to_1bpp, to_planar_fmt, to_sprite_fmt
from .menu import Menu
from .treasure import Treasure

if __name__ == "__main__":
    tomls = load_content_tomls()
    d88s = list(get_all_disk_files())
    out_dir = Path("out")
    complete_listing = dict[str, dict[str, Entry]]()
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
            complete_listing[fn] = listing

            for e in toml.entries:
                ptr = listing.get(e.filename)
                if ptr is None:
                    print(f"! could not find {e.filename}")
                    continue

                ofn = dir / e.get_write_filename()
                if e.type == "text":
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        o.write(get_entry_data(f, ptr).decode(e.encoding or "ascii"))
                    print("OK")
                elif e.type == "menu":
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        m = Menu.from_bytes(get_entry_data(f, ptr))
                        m.write(o)
                    print("OK")
                elif e.type == "treasure":
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "w", encoding="utf-8") as o:
                        o.write(Treasure.LINE_HEADER + "\n")
                        data = get_entry_data(f, ptr)
                        for i in range(0, len(data), 32):
                            tr = Treasure.from_bytes(data[i : i + 32])
                            o.write(tr.as_line() + "\n")
                    print("OK")
                elif e.type == "image" and e.format == "1bpp":
                    img = to_1bpp(get_entry_data(f, ptr), e)
                    print(f"> {ofn}", end="... ")
                    img.save(ofn)
                    print("OK")
                elif e.type == "image" and e.format == "planar":
                    img = to_planar_fmt(get_entry_data(f, ptr))
                    print(f"> {ofn}", end="... ")
                    img.save(ofn)
                    print("OK")
                elif e.type == "image" and e.format == "sprite":
                    pat_data = None
                    if e.patterns:
                        pat_file = listing.get(e.patterns.filename)
                        if pat_file is None:
                            print(
                                f"! {e.filename} needs pattern file {e.patterns.filename}, not found"
                            )
                            continue
                        pat_data = get_entry_data(f, pat_file)
                    img = to_sprite_fmt(get_entry_data(f, ptr), e, pat_data)
                    print(f"> {ofn}", end="... ")
                    img.save(ofn)
                    print("OK")
                else:
                    print(f"> {ofn}", end="... ")
                    with open(ofn, "wb") as o:
                        o.write(get_entry_data(f, ptr))
                    print("OK")

    ofn = out_dir / "complete_listing.txt"
    print(f"> {ofn}", end="... ")
    with open(ofn, "w") as o:
        o.write(f"{Entry.LINE_HEADER} SOURCE FILE\n")
        for fn, listing in complete_listing.items():
            o.writelines([f"{e.as_line()} {fn}\n" for e in listing.values()])
    print("OK")

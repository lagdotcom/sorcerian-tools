from glob import glob
from typing import cast

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser("compare", description="Compare binary files")
    parser.add_argument("filenames", nargs="*")
    parser.add_argument("-s", "--start", help="start position", type=int, default=0)
    parser.add_argument("-l", "--length", help="byte length", type=int, default=32)
    parser.add_argument("-d", "--decimal", help="show as decimal", action="store_true")
    args = parser.parse_args()

    start = cast(int, args.start)
    length = cast(int, args.length)
    decimal = cast(bool, args.decimal)

    offsets = range(start, start + length)
    if decimal:
        print(" ".join([f"{n:3x}" for n in offsets]))
    else:
        print(" ".join([f"{n:2x}" for n in offsets]))

    filenames = [fn for pat in cast(list[str], args.filenames) for fn in glob(pat)]

    for fn in filenames:
        with open(fn, "rb") as f:
            f.seek(start)
            raw = f.read(length)
            if decimal:
                display = " ".join([f"{n:3}" for n in raw])
            else:
                display = raw.hex(" ")
            print(f"{display} {fn}")

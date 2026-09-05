import hashlib
import os


def get_sha1(fn: str):
    with open(fn, "rb") as f:
        raw = f.read()
        sha1 = hashlib.sha1(raw).hexdigest()
        return sha1


def get_all_disk_files():
    for root, _, files in os.walk("disks"):
        for fn in files:
            if fn.lower().endswith(".d88"):
                yield os.path.join(root, fn)


if __name__ == "__main__":
    for fn in get_all_disk_files():
        hash = get_sha1(fn)
        print(f"{hash} {fn}")

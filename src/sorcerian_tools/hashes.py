import hashlib
import os

if __name__ == "__main__":
    for root, dirs, files in os.walk("disks"):
        for fn in files:
            ffn = os.path.join(root, fn)
            with open(ffn, "rb") as f:
                raw = f.read()
                md5 = hashlib.md5(raw).hexdigest()
                sha1 = hashlib.sha1(raw).hexdigest()
                print(f"{md5} {sha1} {ffn}")

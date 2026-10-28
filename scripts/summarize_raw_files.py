
from pathlib import Path
import hashlib
from collections import defaultdict

RAW_DIR = Path("data/raw")


def get_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    files_by_hash = defaultdict(list)

    for path in sorted(RAW_DIR.glob("*.csv")):
        files_by_hash[get_hash(path)].append(path.name)

    print("Total CSV files:", sum(map(len, files_by_hash.values())))
    print("Unique file contents:", len(files_by_hash))

    for index, (digest, filenames) in enumerate(
        files_by_hash.items(), start=1
    ):
        print(f"\nGROUP {index}: {len(filenames)} file(s)")
        print("Example:", filenames[0])
        print("SHA256:", digest[:16])

        if len(filenames) > 1:
            print("Duplicate filenames:")
            for name in filenames:
                print(" ", name)


if __name__ == "__main__":
    main()

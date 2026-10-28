
from pathlib import Path
import hashlib
import pandas as pd

RAW_DIR = Path("data/raw")


def file_hash(path):
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            digest.update(chunk)

    return digest.hexdigest()


def main():
    files = sorted(RAW_DIR.glob("*.csv"))

    print("Total CSV files:", len(files))
    print("\nFIRST 15 FILES:")

    for path in files[:15]:
        df = pd.read_csv(path, low_memory=False)
        dates = (
            df["Date"].astype("string").dropna().unique().tolist()
            if "Date" in df.columns
            else ["Date column missing"]
        )

        print(
            path.name,
            "| rows:", len(df),
            "| dates:", dates[:3],
            "| SHA256:", file_hash(path)[:16],
        )

    print("\nFILE HASH SUMMARY:")
    hashes = {}

    for path in files:
        digest = file_hash(path)
        hashes.setdefault(digest, []).append(path.name)

    print("Unique file contents:", len(hashes))

    for names in list(hashes.values())[:5]:
        print("Matching files:", names[:5])


if __name__ == "__main__":
    main()


from pathlib import Path

import pandas as pd


RAW_DIR = Path("data/raw")


def main():
    if not RAW_DIR.exists():
        print(f"Folder not found: {RAW_DIR}")
        print("Create data/raw inside your AurumSpread folder.")
        return

    files = [
        path
        for path in RAW_DIR.iterdir()
        if path.is_file()
        and path.suffix.lower() in {".csv", ".txt"}
    ]

    if not files:
        print("No CSV or TXT files found in data/raw.")
        print("Download an MCX Bhavcopy file and place it there.")
        return

    for path in files:
        print("\n" + "=" * 70)
        print(f"FILE: {path.name}")
        print("=" * 70)

        try:
            df = pd.read_csv(path, nrows=5, sep=None, engine="python")

            print("\nCOLUMN NAMES:")
            print(df.columns.tolist())

            print("\nSAMPLE ROWS:")
            print(df.head().to_string(index=False))

            print("\nDATA TYPES:")
            print(df.dtypes.to_string())

        except Exception as exc:
            print(f"Could not read this file: {exc}")


if __name__ == "__main__":
    main()

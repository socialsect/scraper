import csv
import glob
import os

from utils.dedup import deduplicate_items

OUTPUT_DIR = "output"
BATCH_FILE = os.path.join(OUTPUT_DIR, "batch1.csv")


def combine_csvs():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    csv_files = sorted(
        f
        for f in glob.glob(os.path.join(OUTPUT_DIR, "*.csv"))
        if os.path.basename(f).lower() != "batch1.csv"
    )

    if not csv_files:
        print("No CSV files to combine.")
        return

    all_items: list[dict] = []

    for path in csv_files:
        with open(path, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames or "email" not in reader.fieldnames:
                print(f"Skipping invalid CSV (no email column): {path}")
                continue
            for row in reader:
                email = (row.get("email") or "").strip().lower()
                if email:
                    all_items.append(
                        {"email": email, "source": (row.get("source") or "").strip()}
                    )

    final_items = deduplicate_items(all_items)

    with open(BATCH_FILE, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["email", "source"])
        writer.writeheader()
        writer.writerows(final_items)

    for path in csv_files:
        os.remove(path)
        print(f"Deleted: {path}")

    bak_files = glob.glob(os.path.join(OUTPUT_DIR, "*.bak"))
    for path in bak_files:
        os.remove(path)
        print(f"Deleted: {path}")

    print(f"\nCombined {len(csv_files)} file(s) into {BATCH_FILE}")
    print(f"Total unique emails: {len(final_items)}")


if __name__ == "__main__":
    combine_csvs()

"""Clean, validate, and deduplicate the emails CSV."""

import csv
import os
import shutil

from config import OUTPUT_FILE
from spiders.email_spider import should_crawl
from utils.csv_output import CSV_COLUMNS, is_query_marker_row
from utils.dedup import deduplicate_items
from utils.email_regex import is_valid_email


def clean_emails_csv(path: str = OUTPUT_FILE) -> None:
    if not os.path.exists(path):
        print(f"Error: Output file not found at {path}")
        return

    backup_file = path + ".bak"
    shutil.copyfile(path, backup_file)
    print(f"Backed up original to: {backup_file}")

    cleaned_items: list[dict] = []
    removed_count = 0
    total_count = 0

    with open(path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or "email" not in reader.fieldnames:
            print("Error: Invalid CSV — missing 'email' column.")
            return

        for row in reader:
            total_count += 1
            email = (row.get("email") or "").strip().lower()
            source = (row.get("source") or "").strip()

            if is_query_marker_row(row):
                continue

            if not is_valid_email(email):
                removed_count += 1
                continue

            if not should_crawl(email) or not should_crawl(source):
                removed_count += 1
                continue

            # Carry all enrichment columns through
            cleaned_items.append({
                "email": email,
                "source": source,
                "phone": (row.get("phone") or "").strip(),
                "linkedin": (row.get("linkedin") or "").strip(),
                "twitter": (row.get("twitter") or "").strip(),
                "instagram": (row.get("instagram") or "").strip(),
                "facebook": (row.get("facebook") or "").strip(),
                "youtube": (row.get("youtube") or "").strip(),
                "mx_valid": (row.get("mx_valid") or "").strip(),
            })

    # Deduplicate on email address
    final_items = deduplicate_items(cleaned_items)
    dedup_removed = len(cleaned_items) - len(final_items)
    removed_count += dedup_removed

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
        writer.writeheader()
        writer.writerows(final_items)

    print(f"\n--- CSV Cleaning Summary ---")
    print(f"Total original rows : {total_count}")
    print(f"Removed             : {removed_count}  (invalid / blocked / duplicates)")
    print(f"Remaining           : {len(final_items)}")
    print(f"Saved to            : {path}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Clean and deduplicate an emails CSV")
    p.add_argument("--file", default=OUTPUT_FILE, help="Path to CSV file (default: output/emails.csv)")
    args = p.parse_args()
    clean_csv_path = args.file
    clean_emails_csv(clean_csv_path)

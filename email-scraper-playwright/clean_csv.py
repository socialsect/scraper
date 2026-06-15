import csv
import os
import shutil

from utils.csv_output import is_query_marker_row
from utils.email_regex import is_valid_email
from spiders.email_spider import should_crawl
from utils.dedup import deduplicate_items
from config import OUTPUT_FILE

def clean_emails_csv():
    if not os.path.exists(OUTPUT_FILE):
        print(f"Error: Output file not found at {OUTPUT_FILE}")
        return

    # Create backup first
    backup_file = OUTPUT_FILE + ".bak"
    shutil.copyfile(OUTPUT_FILE, backup_file)
    print(f"Backed up original file to: {backup_file}")

    cleaned_items = []
    removed_count = 0
    total_count = 0

    with open(OUTPUT_FILE, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames or 'email' not in reader.fieldnames:
            print("Error: Invalid CSV format. Missing 'email' column.")
            return

        for row in reader:
            total_count += 1
            email = row.get('email', '').strip().lower()
            source = row.get('source', '').strip()

            if is_query_marker_row(row):
                continue

            # Apply is_valid_email regex checks
            if not is_valid_email(email):
                removed_count += 1
                continue

            # Apply should_crawl domain blocklist rules to both the email domain and the source URL
            if not should_crawl(email) or not should_crawl(source):
                removed_count += 1
                continue

            cleaned_items.append({'email': email, 'source': source})

    # Deduplicate items
    final_items = deduplicate_items(cleaned_items)
    dedup_removed = len(cleaned_items) - len(final_items)
    removed_count += dedup_removed

    # Save cleaned file
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['email', 'source'])
        writer.writeheader()
        writer.writerows(final_items)

    print(f"\n--- CSV Cleaning Summary ---")
    print(f"Total original rows: {total_count}")
    print(f"Removed (bad/blocked/duplicates): {removed_count}")
    print(f"Remaining clean emails: {len(final_items)}")
    print(f"Cleaned output saved directly to: {OUTPUT_FILE}")

if __name__ == '__main__':
    clean_emails_csv()

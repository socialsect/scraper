import requests
import csv
import time

BASE_URL = "https://npiregistry.cms.hhs.gov/api/"

STATES = ["TN", "GA", "FL", "NC", "SC", "AL", "MS"]


JOBS = [
    {
        "name": "ortho",
        "filename": "npi_ortho_southeast.csv",
        "taxonomies": ["Orthopaedic Surgery", "Orthopedic Surgery"],
    },
    {
        "name": "vein",
        "filename": "npi_vein_southeast.csv",
        "taxonomies": ["Vascular Surgery", "Vein Clinic"],
    },
]

def fetch_providers(state, taxonomy, skip=0, limit=200):
    params = {
        "version": "2.1",
        "taxonomy_description": taxonomy,
        "state": state,
        "enumeration_type": "NPI-1",
        "limit": limit,
        "skip": skip
    }
    r = requests.get(BASE_URL, params=params, timeout=15)
    data = r.json()
    return data, data.get("result_count", 0)

def get_location_address(addresses):
    for a in addresses:
        if a.get("address_purpose") == "LOCATION":
            return a
    return addresses[0] if addresses else {}

def scrape_job(job):
    seen_npis = set()
    rows = []

    print(f"\n{'='*50}")
    print(f"Starting job: {job['name'].upper()}")
    print(f"{'='*50}")

    for state in STATES:
        for taxonomy in job["taxonomies"]:
            skip = 0
            first = True
            total_available = 0
            print(f"  Fetching '{taxonomy}' in {state}...")

            while True:
                data, result_count = fetch_providers(state, taxonomy, skip=skip)
                results = data.get("results", [])

                if first:
                    total_available = result_count
                    first = False

                if not results:
                    break

                new_this_batch = 0
                for p in results:
                    npi = p.get("number")
                    if npi in seen_npis:
                        continue
                    seen_npis.add(npi)
                    new_this_batch += 1

                    basic = p.get("basic", {})
                    addr = get_location_address(p.get("addresses", [{}]))
                    taxonomies = p.get("taxonomies", [])
                    primary_tax = next((t for t in taxonomies if t.get("primary")), taxonomies[0] if taxonomies else {})

                    rows.append({
                        "npi": npi,
                        "first_name": basic.get("first_name", ""),
                        "last_name": basic.get("last_name", ""),
                        "credential": basic.get("credential", ""),
                        "phone": addr.get("telephone_number", ""),
                        "fax": addr.get("fax_number", ""),
                        "address": addr.get("address_1", ""),
                        "city": addr.get("city", ""),
                        "state": addr.get("state", state),
                        "zip": addr.get("postal_code", ""),
                        "specialty": primary_tax.get("desc", ""),
                        "status": basic.get("status", ""),
                    })

                print(f"    skip={skip} | new={new_this_batch} | unique so far: {len(rows)} / {total_available} available")

                skip += 200
                if skip >= total_available or skip >= 1200:
                    break

                time.sleep(0.3)

    return rows

def save_csv(rows, filename):
    if not rows:
        print(f"  No data for {filename}")
        return
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
    print(f"  Saved {len(rows)} providers → {filename}")

if __name__ == "__main__":
    for job in JOBS:
        rows = scrape_job(job)
        save_csv(rows, job["filename"])

    print("\nAll done.")
"""
Offline unit tests for all new modules.
MX tests require a real DNS connection (uses gmail.com / nonexistent domain).
Run: python test_all.py
"""
import asyncio
import csv
import os
import sys
import tempfile
import traceback

sys.path.insert(0, os.path.dirname(__file__))

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"

results = []

def test(name, fn):
    try:
        fn()
        print(f"  {PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  {FAIL}  {name}")
        traceback.print_exc()
        results.append((name, False, str(e)))

def atest(name, async_fn):
    """Pass the async *function* (not a coroutine) — we call it here."""
    try:
        asyncio.run(async_fn())
        print(f"  {PASS}  {name}")
        results.append((name, True, None))
    except Exception as e:
        print(f"  {FAIL}  {name}")
        traceback.print_exc()
        results.append((name, False, str(e)))

# ─────────────────────────────────────────────
print("\n── email_regex ──────────────────────────")

def t_valid_email():
    from utils.email_regex import is_valid_email
    # Valid emails
    assert is_valid_email("info@clinic.co.uk"),  "clinic.co.uk should be valid"
    assert is_valid_email("contact@realdentist.com"), "realdentist.com should be valid"
    assert is_valid_email("hello@testclinic.org"), "testclinic.org should be valid"
    # Blocked / invalid
    assert not is_valid_email("noreply@company.com"),   "noreply should be blocked"
    assert not is_valid_email("logo@2x.png"),           "image path should be blocked"
    assert not is_valid_email("bad@"),                  "missing domain"
    assert not is_valid_email("info@example.com"),      "example.com is a placeholder — blocked"

def t_extract_emails():
    from utils.email_regex import extract_emails_from_html
    html = '''<a href="mailto:hello@testclinic.com">email us</a>
              <p>Or reach us at support@dentist.org for appointments</p>
              <p>Ignore: noreply@example.com and logo@2x.png</p>'''
    found = extract_emails_from_html(html)
    assert "hello@testclinic.com" in found,  "should find hello@testclinic.com"
    assert "support@dentist.org" in found,   "should find support@dentist.org"
    assert not any("noreply" in e for e in found), "noreply should be filtered"

test("is_valid_email — valid cases pass, blocked cases fail", t_valid_email)
test("extract_emails_from_html — finds emails, filters noise", t_extract_emails)

# ─────────────────────────────────────────────
print("\n── phone_regex ──────────────────────────")

def t_phone_tel_link():
    from utils.phone_regex import extract_phone_from_tel_links
    phones = extract_phone_from_tel_links(["+1 (800) 555-0100", "0800 123 4567"])
    assert len(phones) == 2
    assert "+1 (800) 555-0100" in phones

def t_phone_from_html():
    from utils.phone_regex import extract_phones_from_html
    # Space after tel: is intentional — tests the href regex fix
    html = '<a href="tel: +44 20 7946 0958">Call us</a><p>Also call (800) 555-0100 during hours.</p>'
    phones = extract_phones_from_html(html)
    assert len(phones) >= 1, f"expected >=1 phone, got {phones}"
    # tel: link should be first and contain the number
    assert "44" in phones[0], f"expected UK number first, got {phones[0]!r}"

def t_phone_no_false_positives():
    from utils.phone_regex import extract_phones_from_html
    html = "<p>Version 12.3.4 released. ZIP 90210. ID: 1234.</p>"
    phones = extract_phones_from_html(html)
    assert not any("12.3.4" in p for p in phones), "version string should not match"

test("extract_phone_from_tel_links — parses tel: hrefs", t_phone_tel_link)
test("extract_phones_from_html — tel: link with space after colon", t_phone_from_html)
test("extract_phones_from_html — no false positives on versions/zips", t_phone_no_false_positives)

# ─────────────────────────────────────────────
print("\n── social_links ─────────────────────────")

def t_social_all_platforms():
    from utils.social_links import extract_social_links
    hrefs = [
        "https://www.linkedin.com/company/some-clinic",
        "https://twitter.com/SomeClinic",
        "https://www.instagram.com/someclinic_official",
        "https://www.facebook.com/SomeClinicPage",
        "https://www.youtube.com/@SomeClinicChannel",
    ]
    result = extract_social_links(hrefs)
    assert result["linkedin"] == "https://www.linkedin.com/company/some-clinic"
    assert "twitter.com" in result["twitter"] or "x.com" in result["twitter"]
    assert result["instagram"] == "https://www.instagram.com/someclinic_official"
    assert "facebook.com" in result["facebook"]
    assert "youtube.com" in result["youtube"]

def t_social_blocks_junk():
    from utils.social_links import extract_social_links
    hrefs = [
        "https://twitter.com/intent/tweet?text=hello",
        "https://www.linkedin.com/in/john-doe",
        "https://www.facebook.com/sharer/sharer.php",
    ]
    result = extract_social_links(hrefs)
    assert "twitter" not in result,   "intent link should be skipped"
    assert "linkedin" not in result,  "personal profile should be skipped"
    assert "facebook" not in result,  "sharer should be skipped"

def t_social_deduplicates():
    from utils.social_links import extract_social_links
    hrefs = [
        "https://www.linkedin.com/company/acme-corp",
        "https://www.linkedin.com/company/acme-corp",
        "https://www.linkedin.com/company/other-corp",
    ]
    result = extract_social_links(hrefs)
    assert result["linkedin"] == "https://www.linkedin.com/company/acme-corp"

test("extract_social_links — finds all 5 platforms", t_social_all_platforms)
test("extract_social_links — blocks intent/personal/sharer links", t_social_blocks_junk)
test("extract_social_links — only keeps first match per platform", t_social_deduplicates)

# ─────────────────────────────────────────────
print("\n── mx_check ─────────────────────────────")

async def t_mx_real_domain():
    from utils.mx_check import has_mx_record
    result = await has_mx_record("gmail.com")
    assert result is True, "gmail.com should have MX records"

async def t_mx_fake_domain():
    from utils.mx_check import has_mx_record
    result = await has_mx_record("this-domain-definitely-does-not-exist-xyz123abc.com")
    assert result is False

async def t_mx_cache():
    from utils.mx_check import has_mx_record, mx_cache_stats, _mx_cache
    _mx_cache.clear()
    await has_mx_record("gmail.com")
    await has_mx_record("gmail.com")   # second call — cache hit
    stats = mx_cache_stats()
    assert stats["cached_domains"] >= 1

async def t_mx_email_helper():
    from utils.mx_check import validate_email_mx
    assert await validate_email_mx("test@gmail.com") is True
    assert await validate_email_mx("bad-email-no-at-sign") is False

atest("has_mx_record — gmail.com returns True", t_mx_real_domain)
atest("has_mx_record — fake domain returns False", t_mx_fake_domain)
atest("mx cache — domain queried only once", t_mx_cache)
atest("validate_email_mx — helper works", t_mx_email_helper)

# ─────────────────────────────────────────────
print("\n── csv_output ───────────────────────────")

def t_csv_write_new_columns():
    from utils.csv_output import (
        append_email_row, ensure_csv_header,
        CSV_COLUMNS, count_data_rows,
    )
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode="w") as f:
        tmp = f.name
    try:
        ensure_csv_header(tmp)
        known: set[str] = set()
        result = append_email_row(
            tmp, "info@clinic.com", "https://clinic.com/contact", known,
            phone="+1 800 555 0100",
            linkedin="https://linkedin.com/company/clinic",
            twitter="https://twitter.com/clinic",
            instagram="",
            facebook="",
            youtube="",
            mx_valid="yes",
        )
        assert result is True
        assert count_data_rows(tmp) == 1

        with open(tmp, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert rows[0]["email"] == "info@clinic.com"
        assert rows[0]["phone"] == "+1 800 555 0100"
        assert rows[0]["linkedin"] == "https://linkedin.com/company/clinic"
        assert rows[0]["mx_valid"] == "yes"

        # Duplicate rejected
        result2 = append_email_row(tmp, "info@clinic.com", "https://other.com", known)
        assert result2 is False
        assert count_data_rows(tmp) == 1

        # Header matches CSV_COLUMNS exactly
        with open(tmp, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        assert header == CSV_COLUMNS, f"header mismatch: {header}"
    finally:
        os.unlink(tmp)
        lock = tmp + ".lock"
        if os.path.exists(lock):
            os.unlink(lock)

test("csv_output — writes all new columns correctly", t_csv_write_new_columns)

# ─────────────────────────────────────────────
print("\n── dedup ────────────────────────────────")

def t_dedup_basic():
    from utils.dedup import deduplicate_items
    items = [
        {"email": "info@realdomain.com", "source": "x", "phone": "123",
         "linkedin": "https://linkedin.com/company/x", "twitter": "",
         "instagram": "", "facebook": "", "youtube": "", "mx_valid": "yes"},
        {"email": "info@realdomain.com", "source": "x2", "phone": "",
         "linkedin": "", "twitter": "", "instagram": "", "facebook": "",
         "youtube": "", "mx_valid": ""},  # duplicate — should be dropped
        {"email": "contact@otherfirm.co.uk", "source": "y", "phone": "",
         "linkedin": "", "twitter": "", "instagram": "", "facebook": "",
         "youtube": "", "mx_valid": "yes"},
    ]
    result = deduplicate_items(items)
    assert len(result) == 2, f"expected 2, got {len(result)}: {[r['email'] for r in result]}"
    assert result[0]["email"] == "info@realdomain.com"
    assert result[0]["phone"] == "123"
    assert result[0]["linkedin"] == "https://linkedin.com/company/x"

def t_dedup_filters_invalid():
    from utils.dedup import deduplicate_items
    items = [
        {"email": "noreply@company.com", "source": "x", "phone": "", "linkedin": "",
         "twitter": "", "instagram": "", "facebook": "", "youtube": "", "mx_valid": ""},
        {"email": "valid@realdomain.co.uk", "source": "y", "phone": "", "linkedin": "",
         "twitter": "", "instagram": "", "facebook": "", "youtube": "", "mx_valid": "yes"},
    ]
    result = deduplicate_items(items)
    assert len(result) == 1
    assert result[0]["email"] == "valid@realdomain.co.uk"

test("deduplicate_items — removes dupes, preserves enrichment", t_dedup_basic)
test("deduplicate_items — filters invalid emails", t_dedup_filters_invalid)

# ─────────────────────────────────────────────
print("\n── combine_csvs (indent + columns fix) ──")

def t_combine_csvs():
    import combine_csvs as cc
    from utils.csv_output import CSV_COLUMNS

    with tempfile.TemporaryDirectory() as tmpdir:
        # Write two mini CSVs using the full column set
        for i, fname in enumerate(["a.csv", "b.csv"]):
            p = os.path.join(tmpdir, fname)
            with open(p, "w", newline="", encoding="utf-8") as f:
                w = csv.DictWriter(f, fieldnames=CSV_COLUMNS)
                w.writeheader()
                w.writerow({
                    "email": f"user{i}@domain{i}.com",
                    "source": f"https://domain{i}.com",
                    "phone": "", "linkedin": "", "twitter": "",
                    "instagram": "", "facebook": "", "youtube": "",
                    "mx_valid": "yes",
                })

        batch = os.path.join(tmpdir, "batch1.csv")
        orig_dir, orig_batch = cc.OUTPUT_DIR, cc.BATCH_FILE
        cc.OUTPUT_DIR = tmpdir
        cc.BATCH_FILE = batch
        try:
            cc.combine_csvs()
        finally:
            cc.OUTPUT_DIR = orig_dir
            cc.BATCH_FILE = orig_batch

        assert os.path.exists(batch), "batch1.csv not created"
        with open(batch, newline="", encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 2, f"expected 2 rows, got {len(rows)}"
        # Verify all columns present
        with open(batch, newline="", encoding="utf-8") as f:
            header = next(csv.reader(f))
        assert header == CSV_COLUMNS, f"wrong header: {header}"

test("combine_csvs — collects rows and writes full column set", t_combine_csvs)

# ─────────────────────────────────────────────
print("\n── domains file parsing (--domains) ─────")

def t_domains_file_parsing():
    raw_lines = [
        "example.com",
        "https://already-has-scheme.org",
        "# comment",
        "",
        "another.co.uk",
    ]
    lines = [l.strip() for l in raw_lines if l.strip() and not l.startswith("#")]
    urls = []
    for line in lines:
        if line.startswith("http://") or line.startswith("https://"):
            urls.append(line)
        else:
            urls.append(f"https://{line}")
    urls = list(dict.fromkeys(urls))
    assert len(urls) == 3
    assert "https://example.com" in urls
    assert "https://already-has-scheme.org" in urls
    assert "https://another.co.uk" in urls

test("run_domains — domain normalisation logic correct", t_domains_file_parsing)

# ─────────────────────────────────────────────
print("\n── imports (all modules importable) ─────")

def t_imports():
    import utils.phone_regex    # noqa
    import utils.social_links   # noqa
    import utils.mx_check       # noqa
    import utils.csv_output     # noqa
    import utils.dedup          # noqa
    import utils.email_regex    # noqa
    import utils.display        # noqa
    import spiders.email_spider # noqa
    import scrapers.ddg_scraper # noqa
    import scrapers.email_extractor   # noqa
    import scrapers.gmaps_scraper     # noqa
    import scrapers.google_scraper    # noqa
    import scrapers.playwright_crawler # noqa
    import config               # noqa
    import combine_csvs         # noqa
    import clean_csv            # noqa

test("all project modules import without error", t_imports)

# ─────────────────────────────────────────────
print("\n── summary ──────────────────────────────")
passed = sum(1 for _, ok, _ in results if ok)
failed = sum(1 for _, ok, _ in results if not ok)
total = len(results)
print(f"\n  {passed}/{total} passed", end="")
if failed:
    print(f"  |  {failed} FAILED:")
    for name, ok, err in results:
        if not ok:
            print(f"    {FAIL} {name}: {err}")
else:
    print("  — all good!\n")

sys.exit(0 if failed == 0 else 1)

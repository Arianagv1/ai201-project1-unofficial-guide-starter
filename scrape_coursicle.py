"""
scrape_coursicle.py

Scrapes Coursicle (UIC) for every course in COURSES_TO_SCRAPE and saves
all results to a single coursicle_data.json, keyed as "coursicle_CS251" etc.

Usage:
    python scrape_coursicle.py

Dependencies:
    pip install playwright
    playwright install chromium
"""

import json
import re
import time
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

# ── Target courses (mirror of scrape_catalog_direct.py) ──────────────────────

COURSES_TO_SCRAPE = {
    "cs":   [111, 112, 113, 141, 151, 211, 251, 342, 377, 412, 418, 421, 424, 480],
    "ids":  [312, 410, 435, 472],
    "stat": [381, 382, 481],
    "ie":   [342],
    "ece":  [341],
    "engr": [100, 101],
    "math": [180, 181, 210, 218],
}

SCHOOL = "uic"
DELAY_BETWEEN_COURSES = 2  # seconds — be polite to Coursicle

# ── Helpers ───────────────────────────────────────────────────────────────────

def safe_text(locator) -> str:
    try:
        return locator.first.inner_text().strip() if locator.count() else ""
    except Exception:
        return ""


def scrape_one(page, dept: str, num: int) -> dict | None:
    """Navigate to a single course page and extract all data."""
    course_code = f"{dept.upper()} {num}"
    course_url  = f"https://www.coursicle.com/{SCHOOL}/courses/{dept.upper()}/{num}/"

    print(f"   → {course_url}")
    try:
        page.goto(course_url, wait_until="networkidle", timeout=30_000)
    except PWTimeout:
        print(f"   ⚠️  Timeout loading {course_url}")
        return None

    time.sleep(0.5)  # let lazy JS settle

    # ── Sub-item key/value fields ─────────────────────────────────────────────
    fields = {}
    sub_items = page.locator(".subItem")
    for i in range(sub_items.count()):
        label_el   = sub_items.nth(i).locator(".subItemLabel").first
        content_el = sub_items.nth(i).locator(".subItemContent").first
        try:
            label   = label_el.inner_text().strip() if label_el.count() else ""
            content = content_el.inner_text().strip() if content_el.count() else ""
            if label and content and label not in ("Professor Reviews",):
                fields[label] = content
        except Exception:
            continue

    # Bail out if the page is empty / course doesn't exist on Coursicle
    if not fields:
        print(f"   ⚠️  No data found for {course_code} — skipping")
        return None

    # ── Avg professor rating ──────────────────────────────────────────────────
    rating_el  = page.locator(".avgRating, .professorRating, .ratingCircle")
    avg_rating = safe_text(rating_el)

    # ── Professor reviews ─────────────────────────────────────────────────────
    reviews = []
    comment_els = page.locator("#subItemReviews .comment.topLevel")
    for i in range(comment_els.count()):
        c = comment_els.nth(i)
        reviews.append({
            "author":    safe_text(c.locator(".comment-metadata")),
            "timestamp": safe_text(c.locator(".comment-timestamp")),
            "year":      safe_text(c.locator(".userBadge.year")),
            "major":     safe_text(c.locator(".userBadge.major")),
            "body":      safe_text(c.locator(".comment-body")),
        })

    # ── Section JSON (embedded in data-klass attributes) ──────────────────────
    sections = []
    for el in page.locator(".classSearchItem").element_handles():
        raw = el.get_attribute("data-klass")
        if raw:
            try:
                sections.append(json.loads(raw))
            except json.JSONDecodeError:
                pass

    return {
        "course_code":      course_code,
        "avg_rating":       avg_rating,
        "description":      fields.get("Description", ""),
        "credits":          fields.get("Credits", ""),
        "class_size":       fields.get("Class Size", ""),
        "usually_offered":  fields.get("Usually Offered", ""),
        "attributes":       fields.get("Attributes", ""),
        "former_titles":    fields.get("Former Titles", ""),
        "recent_semesters": fields.get("Recent Semesters", ""),
        "recent_professors":fields.get("Recent Professors", ""),
        "all_fields":       fields,
        "professor_reviews":reviews,
        "sections":         sections,
        "source_url":       course_url,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_data = {}
    total    = sum(len(v) for v in COURSES_TO_SCRAPE.values())
    done     = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page    = browser.new_page(user_agent=(
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ))

        for dept, nums in COURSES_TO_SCRAPE.items():
            print(f"\n📄 Scraping {dept.upper()} ({len(nums)} courses)…")
            for num in nums:
                done += 1
                print(f"  [{done}/{total}] {dept.upper()} {num}")

                result = scrape_one(page, dept, num)
                if result:
                    key = f"coursicle_{dept.upper()}{num}"
                    all_data[key] = result
                    print(f"   ✅ {dept.upper()} {num} — "
                          f"rating={result['avg_rating'] or 'N/A'}, "
                          f"{len(result['professor_reviews'])} reviews, "
                          f"{len(result['sections'])} sections")

                time.sleep(DELAY_BETWEEN_COURSES)

        browser.close()

    print(f"\n{'='*60}")
    print(f"✅ Total scraped: {len(all_data)} / {total} courses")
    print(f"{'='*60}\n")

    with open("coursicle_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("✅ Saved to coursicle_data.json")

    # Preview first result
    if all_data:
        first_key = next(iter(all_data))
        d = all_data[first_key]
        print(f"\nSample ({first_key}):")
        print(f"  Rating:      {d['avg_rating']}")
        print(f"  Credits:     {d['credits']}")
        print(f"  Class size:  {d['class_size']}")
        print(f"  Description: {d['description'][:120]}…")
        print(f"  Reviews:     {len(d['professor_reviews'])}")
        print(f"  Sections:    {len(d['sections'])}")


if __name__ == "__main__":
    main()

"""
scrape_uloop_professors.py

Scrapes uic.uloop.com/professors for pages 1-7, filters to target
departments, then visits each professor's page to grab full review text.
Saves to uloop_professors.json keyed as "uloop_Mitchell Theys" etc.

Usage:
    python scrape_uloop_professors.py

Dependencies:
    pip install requests beautifulsoup4
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

# ── Config ────────────────────────────────────────────────────────────────────

BASE_URL    = "https://uic.uloop.com"
START_PAGE  = 1
END_PAGE    = 7
DELAY       = 2  # seconds between requests

TARGET_DEPARTMENTS = {
    "computer science",
    "statistics",
    "information and decision sciences",
}

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get(url: str) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"   ⚠️  GET failed {url}: {e}")
        return None


def count_stars(star_div) -> float:
    """Count full stars out of 5 from star img tags."""
    if not star_div:
        return None
    full = len(star_div.find_all("img", src=re.compile("star-full")))
    half = len(star_div.find_all("img", src=re.compile("star-half")))
    return full + (0.5 * half)


# ── Listing page scrape ───────────────────────────────────────────────────────

def scrape_listing_page(page_num: int) -> list[dict]:
    """Return list of {name, rating, department, profile_url} for target depts."""
    url  = f"{BASE_URL}/professors?page={page_num}"
    soup = get(url)
    if not soup:
        return []

    results = []

    # Each professor is grouped in a repeating block; find all professor_name divs
    # and walk siblings to get stars + department
    prof_name_divs = soup.find_all("div", class_="professor_name")

    for name_div in prof_name_divs:
        a_tag = name_div.find("a")
        if not a_tag:
            continue

        name        = a_tag.get_text(strip=True)
        profile_url = BASE_URL + a_tag["href"] if a_tag.get("href") else None

        star_div = name_div.find_next_sibling("div", class_="professor_stars")
        dept_div = name_div.find_next_sibling("div", class_="professor_department")

        department = dept_div.get_text(strip=True) if dept_div else ""
        rating     = count_stars(star_div)

        if department.lower() not in TARGET_DEPARTMENTS:
            continue

        results.append({
            "name":        name,
            "department":  department,
            "rating":      rating,
            "profile_url": profile_url,
        })

    return results


# ── Profile page scrape ───────────────────────────────────────────────────────

def parse_comment_text(comment_span) -> str:
    """
    Extract clean comment text from a span.comment element.
    Handles both plain text and the Pros:/Cons: bold-tag format.
    """
    if not comment_span:
        return ""

    # Replace <br> with a space before extracting text
    for br in comment_span.find_all("br"):
        br.replace_with(" ")

    # Strip bold Pros/Cons labels so RAG gets clean prose
    for b in comment_span.find_all("b", class_=re.compile("pr_c_")):
        label = b.get_text(strip=True)  # e.g. "Pros: "
        b.replace_with(label)           # keep the label text, just remove the <b>

    return re.sub(r"\s+", " ", comment_span.get_text()).strip()


def parse_rating_block(td) -> dict:
    """
    Parse a <td> containing overall_rating + separate_rating divs.
    Returns {overall, helpfulness, clarity, easiness} as floats.
    """
    ratings = {}

    overall_div = td.find("div", class_="overall_rating")
    if overall_div:
        star_div = overall_div.find("div", class_="stars")
        ratings["overall"] = count_stars(star_div)

    for sep in td.find_all("div", class_="separate_rating"):
        title_el = sep.find("div", class_="title")
        star_div  = sep.find("div", class_="stars")
        if title_el and star_div:
            key = title_el.get_text(strip=True).lower()  # helpfulness / clarity / easiness
            ratings[key] = count_stars(star_div)

    return ratings


def scrape_profile(prof: dict) -> dict:
    """Visit a professor's Uloop profile page and extract all reviews."""
    if not prof["profile_url"]:
        return prof

    soup = get(prof["profile_url"])
    if not soup:
        return prof

    reviews = []

    # ── Strategy: anchor on span.comment, then walk UP to the parent <tr>
    # to grab the sibling <td> with the ratings. This avoids any tbody/table
    # structural assumptions entirely.
    for comment_span in soup.find_all("span", class_="comment"):
        comment_text = parse_comment_text(comment_span)
        if not comment_text or len(comment_text) < 5:
            continue

        # Walk up to the enclosing <tr>
        row = comment_span.find_parent("tr")
        if not row:
            continue

        tds = row.find_all("td", recursive=False)
        if len(tds) < 2:
            continue

        rating_td = tds[0]  # first <td> always holds the star blocks
        ratings   = parse_rating_block(rating_td)

        reviews.append({
            "overall":     ratings.get("overall"),
            "helpfulness": ratings.get("helpfulness"),
            "clarity":     ratings.get("clarity"),
            "easiness":    ratings.get("easiness"),
            "comment":     comment_text,
        })

    # Course codes mentioned anywhere on the page (e.g. "CS 251")
    course_tags = list(set(
        match
        for text in soup.find_all(string=re.compile(r"\b[A-Z]{2,4}\s?\d{3}\b"))
        for match in re.findall(r"\b[A-Z]{2,4}\s?\d{3}\b", text)
    ))

    return {
        **prof,
        "reviews":     reviews,
        "course_tags": course_tags,
        "source_url":  prof["profile_url"],
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_professors = []

    # ── Pass 1: collect all matching professors from listing pages ────────────
    print(f"📄 Scanning listing pages {START_PAGE}–{END_PAGE}…\n")
    for page_num in range(START_PAGE, END_PAGE + 1):
        print(f"  Page {page_num}…", end=" ", flush=True)
        profs = scrape_listing_page(page_num)
        print(f"{len(profs)} target-dept professors found")
        all_professors.extend(profs)
        time.sleep(DELAY)

    print(f"\n  Total professors to profile: {len(all_professors)}\n")

    # ── Pass 2: visit each profile page ──────────────────────────────────────
    all_data = {}
    for i, prof in enumerate(all_professors, 1):
        print(f"  [{i}/{len(all_professors)}] {prof['name']} ({prof['department']})")
        enriched = scrape_profile(prof)
        key = f"uloop_{prof['name']}"
        all_data[key] = enriched
        print(f"   ✅ rating={enriched['rating']} — {len(enriched.get('reviews', []))} reviews")
        time.sleep(DELAY)

    print(f"\n{'='*60}")
    print(f"✅ Total scraped: {len(all_data)} professors")
    print(f"{'='*60}\n")

    with open("uloop_professors.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("✅ Saved to uloop_professors.json")

    # Preview
    if all_data:
        first_key = next(iter(all_data))
        d = all_data[first_key]
        print(f"\nSample ({first_key}):")
        print(f"  Department:  {d['department']}")
        print(f"  Rating:      {d['rating']} / 5")
        print(f"  Course tags: {d.get('course_tags', [])}")
        print(f"  Reviews:     {len(d.get('reviews', []))}")
        if d.get("reviews"):
            print(f"  First review preview: {d['reviews'][0]['comment'][:200]}")


if __name__ == "__main__":
    main()
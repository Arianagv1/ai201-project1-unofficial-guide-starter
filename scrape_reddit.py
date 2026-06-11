"""
scrape_reddit.py

Scrapes old.reddit.com/r/uic for posts mentioning each course in
COURSES_TO_SCRAPE, pulls the full comment thread, and saves everything
to reddit_data.json keyed as "reddit_CS251" etc.

Usage:
    python scrape_reddit.py

Dependencies:
    pip install requests beautifulsoup4
"""

import json
import re
import time
import requests
from bs4 import BeautifulSoup

# ── Target courses (same dict as other scrapers) ──────────────────────────────

COURSES_TO_SCRAPE = {
    "cs":   [111, 112, 113, 141, 151, 211, 251, 342, 377, 412, 418, 421, 424, 480],
    "ids":  [312, 410, 435, 472],
    "stat": [381, 382, 481],
    "ie":   [342],
    "ece":  [341],
    "engr": [100, 101],
    "math": [180, 181, 210, 218],
}

BASE_URL        = "https://old.reddit.com"
SUBREDDIT       = "uic"
MAX_POSTS       = 5      # top N posts per course
MAX_COMMENTS    = 30     # max comments to pull per post
DELAY_SEARCH    = 3      # seconds between search requests
DELAY_POST      = 2      # seconds between post/comment fetches

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/124.0.0.0 Safari/537.36"
}

# ── Helpers ───────────────────────────────────────────────────────────────────

def get(url: str, params: dict = None) -> BeautifulSoup | None:
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print(f"   ⚠️  GET failed {url}: {e}")
        return None


def search_posts(query: str) -> list[dict]:
    """Search r/uic for a query, return list of {title, url, score, num_comments}."""
    url  = f"{BASE_URL}/r/{SUBREDDIT}/search"
    soup = get(url, params={"q": query, "restrict_sr": "on", "sort": "relevance", "limit": MAX_POSTS})
    if not soup:
        return []

    posts = []
    for thing in soup.select("div.search-result-link")[:MAX_POSTS]:
        title_el = thing.select_one("a.search-title")
        if not title_el:
            continue
        post_url = title_el.get("href", "")
        if not post_url.startswith("http"):
            post_url = BASE_URL + post_url
        score_el    = thing.select_one("span.search-score")
        comments_el = thing.select_one("a.search-comments")
        posts.append({
            "title":        title_el.get_text(strip=True),
            "url":          post_url,
            "score":        score_el.get_text(strip=True) if score_el else "",
            "num_comments": comments_el.get_text(strip=True) if comments_el else "",
        })

    return posts


def scrape_comments(post_url: str) -> list[str]:
    """Fetch a post page and extract comment bodies (flat, top-level + replies)."""
    # old.reddit uses /?limit=500 to expand comments
    soup = get(post_url + "?limit=500")
    if not soup:
        return []

    comments = []
    for el in soup.select("div.usertext-body .md")[:MAX_COMMENTS]:
        text = el.get_text(separator=" ", strip=True)
        if text and len(text) > 20:  # skip empty/very short
            comments.append(text)

    return comments


# ── Per-course scrape ─────────────────────────────────────────────────────────

def scrape_one(dept: str, num: int) -> dict | None:
    course_code = f"{dept.upper()} {num}"
    # Try both "CS 251" and "CS251" as search terms
    queries = [course_code, f"{dept.upper()}{num}"]

    seen_urls = set()
    all_posts = []

    for query in queries:
        posts = search_posts(query)
        time.sleep(DELAY_SEARCH)
        for post in posts:
            if post["url"] not in seen_urls:
                seen_urls.add(post["url"])
                all_posts.append(post)

    if not all_posts:
        return None

    # Fetch comments for each post
    enriched = []
    for post in all_posts[:MAX_POSTS]:
        comments = scrape_comments(post["url"])
        time.sleep(DELAY_POST)
        enriched.append({**post, "comments": comments})
        print(f"     • \"{post['title'][:60]}\" — {len(comments)} comments")

    return {
        "course_code": course_code,
        "subreddit":   SUBREDDIT,
        "posts":       enriched,
        "source_url":  f"{BASE_URL}/r/{SUBREDDIT}/search?q={course_code}&restrict_sr=on",
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_data = {}
    total    = sum(len(v) for v in COURSES_TO_SCRAPE.values())
    done     = 0

    for dept, nums in COURSES_TO_SCRAPE.items():
        print(f"\n📄 Scraping Reddit for {dept.upper()} ({len(nums)} courses)…")
        for num in nums:
            done += 1
            print(f"  [{done}/{total}] {dept.upper()} {num}")

            result = scrape_one(dept, num)
            if result:
                key = f"reddit_{dept.upper()}{num}"
                all_data[key] = result
                print(f"   ✅ {dept.upper()} {num} — {len(result['posts'])} posts found")
            else:
                print(f"   ⚠️  No posts found for {dept.upper()} {num}")

    print(f"\n{'='*60}")
    print(f"✅ Total scraped: {len(all_data)} / {total} courses")
    print(f"{'='*60}\n")

    with open("reddit_data.json", "w", encoding="utf-8") as f:
        json.dump(all_data, f, indent=2, ensure_ascii=False)
    print("✅ Saved to reddit_data.json")

    # Preview first result
    if all_data:
        first_key = next(iter(all_data))
        d = all_data[first_key]
        print(f"\nSample ({first_key}):")
        print(f"  Posts found: {len(d['posts'])}")
        if d["posts"]:
            p = d["posts"][0]
            print(f"  First post:  {p['title']}")
            print(f"  Comments:    {len(p['comments'])}")
            if p["comments"]:
                print(f"  First comment preview: {p['comments'][0][:200]}")


if __name__ == "__main__":
    main()
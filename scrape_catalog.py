# scrape_catalog_direct.py

import requests
from bs4 import BeautifulSoup
import json
import re

# Target courses per department
COURSES_TO_SCRAPE = {
    "cs":   [111, 112, 113, 141, 151, 211, 251, 342, 377, 412, 418, 421, 424, 480],
    "ids":  [312, 410, 435, 472],
    "stat": [381, 382, 481],
    "ie":   [342],
    "ece":  [341],
    "engr": [100, 101],
    "math": [180, 181, 210, 218],
}

DEPT_URLS = {
    "cs":   "https://catalog.uic.edu/ucat/course-descriptions/cs/",
    "ids":  "https://catalog.uic.edu/ucat/course-descriptions/ids/",
    "stat": "https://catalog.uic.edu/ucat/course-descriptions/stat/",
    "ie":   "https://catalog.uic.edu/ucat/course-descriptions/ie/",
    "ece":  "https://catalog.uic.edu/ucat/course-descriptions/ece/",
    "engr": "https://catalog.uic.edu/ucat/course-descriptions/engr/",
    "math": "https://catalog.uic.edu/ucat/course-descriptions/math/",
}

def scrape_department(dept, course_nums):
    """Scrape one department catalog page and extract target courses"""
    url = DEPT_URLS[dept]
    print(f"\n📄 Scraping {dept.upper()} catalog: {url}")

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except Exception as e:
        print(f"   ❌ Failed to load {url}: {e}")
        return {}

    soup = BeautifulSoup(response.text, "html.parser")

    # UIC catalog wraps each course in a div with class "courseblock"
    course_blocks = soup.find_all("div", class_="courseblock")
    print(f"   Found {len(course_blocks)} total course blocks on page")

    found = {}
    for block in course_blocks:
        # Course title line looks like: "CS 251. Data Structures. 3 hours."
        title_tag = block.find("p", class_="courseblocktitle")
        if not title_tag:
            continue

        title_text = title_tag.get_text(separator=" ", strip=True)

        # Check if this block matches any of our target course numbers
        for num in course_nums:
            pattern = rf"{dept.upper()}\s+{num}\b"
            if re.search(pattern, title_text, re.IGNORECASE):
                # Extract full course text
                full_text = block.get_text(separator="\n", strip=True)
                clean = re.sub(r'\n{3,}', '\n\n', full_text)
                key = f"catalog_{dept.upper()}{num}"
                found[key] = clean
                print(f"   ✅ Found {dept.upper()} {num}: {title_text[:60]}")
                break

    missing = [n for n in course_nums if f"catalog_{dept.upper()}{n}" not in found]
    if missing:
        print(f"   ⚠️  Not found: {[f'{dept.upper()}{n}' for n in missing]}")

    return found


def main():
    all_courses = {}

    for dept, nums in COURSES_TO_SCRAPE.items():
        dept_courses = scrape_department(dept, nums)
        all_courses.update(dept_courses)

    print(f"\n{'='*60}")
    print(f"✅ Total scraped: {len(all_courses)} courses")
    print(f"{'='*60}\n")

    # Save to JSON
    with open("catalog_courses.json", "w", encoding="utf-8") as f:
        json.dump(all_courses, f, indent=2, ensure_ascii=False)
    print("✅ Saved to catalog_courses.json")

    # Preview sample
    if all_courses:
        first_key = list(all_courses.keys())[0]
        print(f"\nSample ({first_key}):\n")
        print(all_courses[first_key][:400])


if __name__ == "__main__":
    main()
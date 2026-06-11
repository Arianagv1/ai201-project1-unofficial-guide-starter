"""
scrape_grades.py

Scrapes uicgrades.com for FA25, SU25, and SP25 grades for all courses
in COURSES_TO_SCRAPE. Restarts Chrome between each course to avoid crashes.
Saves incrementally to uicgrades_data.json.

Usage:
    python scrape_grades.py

Dependencies:
    pip install selenium webdriver-manager beautifulsoup4
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json

# ── Config ────────────────────────────────────────────────────────────────────

TARGET_SEMESTERS = {"FA25", "SU25", "SP25"}

COURSES_TO_SCRAPE = {
    "CS":   [111, 112, 113, 141, 151, 211, 251, 342, 377, 412, 418, 421, 424, 480],
    "IDS":  [312, 410, 435, 472],
    "STAT": [381, 382, 481],
    "IE":   [342],
    "ECE":  [341],
    "ENGR": [100, 101],
    "MATH": [180, 181, 210, 218],
}

# ── Driver factory ────────────────────────────────────────────────────────────

def make_driver():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options,
    )

# ── Per-course scrape ─────────────────────────────────────────────────────────

def scrape_course(dept: str, course_num: str) -> dict:
    """Fresh driver per course, scrapes only TARGET_SEMESTERS."""
    course_code = f"{dept}{course_num}"
    grades_data = {}

    driver = make_driver()
    try:
        print(f"\n  Loading {course_code}...")
        driver.get("https://uicgrades.com/gradeDistributions.html")
        time.sleep(3)

        # Fill subject
        subject_input = None
        for selector_type, selector in [
            (By.ID,           "subject"),
            (By.NAME,         "subject"),
            (By.CSS_SELECTOR, "input[placeholder*='Subject']"),
            (By.CSS_SELECTOR, "input[type='text']:first-of-type"),
        ]:
            try:
                subject_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                break
            except Exception:
                continue

        if not subject_input:
            print(f"   Could not find subject input")
            return grades_data
        subject_input.clear()
        subject_input.send_keys(dept)
        time.sleep(1)

        # Fill course number
        course_input = None
        for selector_type, selector in [
            (By.ID,           "course"),
            (By.NAME,         "course"),
            (By.CSS_SELECTOR, "input[placeholder*='Course']"),
            (By.CSS_SELECTOR, "input[type='text']:nth-of-type(2)"),
        ]:
            try:
                course_input = WebDriverWait(driver, 3).until(
                    EC.presence_of_element_located((selector_type, selector))
                )
                break
            except Exception:
                continue

        if not course_input:
            print(f"   Could not find course input")
            return grades_data
        course_input.clear()
        course_input.send_keys(course_num)
        time.sleep(1)

        # Click search
        search_btn = None
        for selector_type, selector in [
            (By.ID,           "search-btn"),
            (By.ID,           "searchBtn"),
            (By.CSS_SELECTOR, "button[type='submit']"),
            (By.XPATH,        "//button[contains(text(), 'Search')]"),
            (By.XPATH,        "//button[contains(text(), 'search')]"),
        ]:
            try:
                search_btn = WebDriverWait(driver, 3).until(
                    EC.element_to_be_clickable((selector_type, selector))
                )
                break
            except Exception:
                continue

        if not search_btn:
            print(f"   Could not find search button")
            return grades_data
        search_btn.click()
        time.sleep(2)

        # Parse page and filter to target semesters only
        soup = BeautifulSoup(driver.page_source, "html.parser")
        all_sections = soup.find_all("div", class_="semester-section")

        target_sections = []
        for section in all_sections:
            h2 = section.find("h2")
            if h2 and h2.get_text(strip=True) in TARGET_SEMESTERS:
                target_sections.append((h2.get_text(strip=True), section))

        if not target_sections:
            print(f"   No FA25/SU25/SP25 data for {course_code}")
            grades_data[f"grades_{course_code}_NO_DATA"] = (
                f"{course_code}: No grade data available for FA25, SU25, or SP25."
            )
            return grades_data

        print(f"   Semesters found: {[s for s, _ in target_sections]}")

        # For each target semester, click each instructor button
        for semester, section in target_sections:
            instructor_buttons = section.find_all("button", class_="class-button")
            if not instructor_buttons:
                print(f"   No instructors for {course_code} {semester}")
                grades_data[f"grades_{course_code}_{semester}"] = (
                    f"{course_code} {semester}: No instructor breakdown available."
                )
                continue

            instructors = [btn.get_text(strip=True) for btn in instructor_buttons]
            print(f"   {semester} instructors: {instructors}")

            for instructor in instructors:
                print(f"   Clicking: {semester} — {instructor}")
                live_sections = driver.find_elements(By.CLASS_NAME, "semester-section")
                for live_section in live_sections:
                    h2 = live_section.find_element(By.TAG_NAME, "h2")
                    if h2.text.strip() != semester:
                        continue
                    for btn in live_section.find_elements(By.CLASS_NAME, "class-button"):
                        if instructor in btn.text:
                            driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                            btn.click()

                            WebDriverWait(driver, 10).until(
                                EC.visibility_of_element_located((By.ID, "customModal"))
                            )
                            time.sleep(1)

                            modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                            modal      = modal_soup.find(id="customModal")

                            svg_title  = modal.find("text", {"font-weight": "bold"})
                            title_text = (svg_title.get_text(strip=True) if svg_title
                                          else f"{semester}: {course_code} with {instructor}")

                            table  = modal.find("table")
                            grades = {}
                            if table:
                                for row in table.find_all("tr")[1:]:
                                    cols = row.find_all("td")
                                    if len(cols) == 2:
                                        grades[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

                            if grades:
                                grade_text = f"{title_text}\n"
                                for grade, count in grades.items():
                                    grade_text += f"  {grade}: {count} students\n"
                            else:
                                grade_text = f"{title_text}\n  No grade breakdown available.\n"

                            key = f"grades_{course_code}_{semester}_{instructor.replace(' ', '_').replace(',', '')}"
                            grades_data[key] = grade_text
                            print(f"   Saved: {grade_text.strip()[:80]}")

                            driver.find_element(By.CLASS_NAME, "custom-close-button").click()
                            time.sleep(0.5)
                            break

    except Exception as e:
        print(f"   ERROR {course_code}: {str(e)[:100]}")
    finally:
        driver.quit()

    return grades_data


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    all_grades = {}
    total      = sum(len(v) for v in COURSES_TO_SCRAPE.values())
    done       = 0

    for dept, nums in COURSES_TO_SCRAPE.items():
        print(f"\n--- {dept} ({len(nums)} courses) ---")
        for num in nums:
            done += 1
            print(f"\n[{done}/{total}] {dept} {num}")
            result = scrape_course(dept, str(num))
            all_grades.update(result)
            # Save after every course so a crash doesn't lose progress
            with open("uicgrades_data.json", "w", encoding="utf-8") as f:
                json.dump(all_grades, f, indent=2, ensure_ascii=False)
            print(f"   -> {len(result)} records saved")

    print(f"\n{'='*60}")
    print(f"Total records: {len(all_grades)}")
    print(f"Saved to uicgrades_data.json")
    print(f"{'='*60}")


if __name__ == "__main__":
    print("=" * 60)
    print(f"UIC Grades Scraper — {', '.join(sorted(TARGET_SEMESTERS))}")
    print("=" * 60 + "\n")
    main()
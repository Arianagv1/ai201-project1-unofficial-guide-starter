from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re

def scrape_uicgrades():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    courses_to_scrape = [
        ("CS", "251"), ("CS", "342"), ("CS", "480"),
        ("IDS", "435"), ("IDS", "312"),
    ]

    grades_data = {}
    
    try:
        for dept, course_num in courses_to_scrape:
            course_code = f"{dept}{course_num}"
            print(f"\n⏳ Loading {course_code}...")

            try:
                driver.get("https://uicgrades.com/gradeDistributions.html")
                time.sleep(3)
                
                # Find and fill subject
                subject_input = None
                for selector_type, selector in [
                    (By.ID, "subject"),
                    (By.NAME, "subject"),
                    (By.CSS_SELECTOR, "input[placeholder*='Subject']"),
                    (By.CSS_SELECTOR, "input[type='text']:first-of-type"),
                ]:
                    try:
                        subject_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((selector_type, selector))
                        )
                        break
                    except:
                        continue
                
                if not subject_input:
                    print(f"   ❌ Could not find subject input")
                    continue
                
                subject_input.clear()
                subject_input.send_keys(dept)
                print(f"   ✅ Entered subject: {dept}")
                time.sleep(1)
                
                # Find and fill course
                course_input = None
                for selector_type, selector in [
                    (By.ID, "course"),
                    (By.NAME, "course"),
                    (By.CSS_SELECTOR, "input[placeholder*='Course']"),
                    (By.CSS_SELECTOR, "input[type='text']:nth-of-type(2)"),
                ]:
                    try:
                        course_input = WebDriverWait(driver, 3).until(
                            EC.presence_of_element_located((selector_type, selector))
                        )
                        break
                    except:
                        continue
                
                if not course_input:
                    print(f"   ❌ Could not find course input")
                    continue
                
                course_input.clear()
                course_input.send_keys(course_num)
                print(f"   ✅ Entered course: {course_num}")
                time.sleep(1)
                
                # Click search button
                search_btn = None
                for selector_type, selector in [
                    (By.ID, "search-btn"),
                    (By.ID, "searchBtn"),
                    (By.CSS_SELECTOR, "button[type='submit']"),
                    (By.XPATH, "//button[contains(text(), 'Search')]"),
                    (By.XPATH, "//button[contains(text(), 'search')]"),
                ]:
                    try:
                        search_btn = WebDriverWait(driver, 3).until(
                            EC.element_to_be_clickable((selector_type, selector))
                        )
                        break
                    except:
                        continue
                
                if not search_btn:
                    print(f"   ❌ Could not find search button")
                    continue
                
                search_btn.click()
                print(f"   ✅ Clicked search")
                time.sleep(2)
                
                # Find FA25 section specifically
                soup = BeautifulSoup(driver.page_source, "html.parser")
                fa25_section = None
                for section in soup.find_all("div", class_="semester-section"):
                    h2 = section.find("h2")
                    if h2 and h2.get_text(strip=True) == "FA25":
                        fa25_section = section
                        break

                # No FA25 data
                if not fa25_section:
                    print(f"   ⚠️  No FA25 data found for {course_code}")
                    grades_data[f"grades_{course_code}_FA25"] = (
                        f"{course_code} FA25: Not enough information right now about this course from Fall 2025 semester."
                    )
                    continue

                # Get instructor buttons in FA25
                instructor_buttons = fa25_section.find_all("button", class_="class-button")
                if not instructor_buttons:
                    print(f"   ⚠️  No instructors listed for {course_code} FA25")
                    grades_data[f"grades_{course_code}_FA25"] = (
                        f"{course_code} FA25: Not enough information right now about this course from Fall 2025 semester."
                    )
                    continue

                instructors = [btn.get_text(strip=True) for btn in instructor_buttons]
                print(f"   📋 FA25 instructors: {instructors}")

                # Click each instructor button and extract modal data
                for instructor in instructors:
                    print(f"   👤 Clicking: {instructor}")

                    # Re-find in live DOM (soup is stale)
                    live_sections = driver.find_elements(By.CLASS_NAME, "semester-section")
                    for live_section in live_sections:
                        h2 = live_section.find_element(By.TAG_NAME, "h2")
                        if h2.text.strip() != "FA25":
                            continue

                        for btn in live_section.find_elements(By.CLASS_NAME, "class-button"):
                            if instructor in btn.text:
                                driver.execute_script("arguments[0].scrollIntoView(true);", btn)
                                btn.click()

                                # Wait for modal
                                WebDriverWait(driver, 10).until(
                                    EC.visibility_of_element_located((By.ID, "customModal"))
                                )
                                time.sleep(1)

                                # Parse modal
                                modal_soup = BeautifulSoup(driver.page_source, "html.parser")
                                modal = modal_soup.find(id="customModal")

                                # Get title from SVG bold text
                                svg_title = modal.find("text", {"font-weight": "bold"})
                                title_text = svg_title.get_text(strip=True) if svg_title else f"FA25: {course_code} with {instructor}"

                                # Get grade counts from hidden table
                                table = modal.find("table")
                                grades = {}
                                if table:
                                    for row in table.find_all("tr")[1:]:
                                        cols = row.find_all("td")
                                        if len(cols) == 2:
                                            grades[cols[0].get_text(strip=True)] = cols[1].get_text(strip=True)

                                # Format clean text for RAG
                                if grades:
                                    grade_text = f"{title_text}\n"
                                    for grade, count in grades.items():
                                        grade_text += f"  {grade}: {count} students\n"
                                else:
                                    grade_text = f"{title_text}\n  No grade breakdown available.\n"

                                key = f"grades_{course_code}_FA25_{instructor.replace(' ', '_').replace(',', '')}"
                                grades_data[key] = grade_text
                                print(f"   ✅ Saved: {grade_text.strip()}")

                                # Close modal
                                driver.find_element(By.CLASS_NAME, "custom-close-button").click()
                                time.sleep(0.5)
                                break

            except Exception as e:
                print(f"   ❌ {course_code}: {str(e)[:80]}")

    finally:
        driver.quit()

    return grades_data


if __name__ == "__main__":
    print("="*60)
    print("UIC Grades Scraper - FA25 Only")
    print("="*60 + "\n")

    grades_data = scrape_uicgrades()

    with open("uicgrades_data.json", "w", encoding="utf-8") as f:
        json.dump(grades_data, f, indent=2, ensure_ascii=False)

    print(f"\n✅ Saved {len(grades_data)} records to uicgrades_data.json")

    if grades_data:
        first_key = list(grades_data.keys())[0]
        print(f"\nSample ({first_key}):\n{grades_data[first_key]}")
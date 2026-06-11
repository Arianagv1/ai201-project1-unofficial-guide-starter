# scrape_easy_courses.py - FIXED (Click anchor links in dropdown)

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

def scrape_easy_courses():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    # Courses we care about for Data Science
    target_courses = {
        "CS": [111, 112, 113, 141, 151, 211, 251, 342, 377, 412, 418, 421, 424, 480],
        "IDS": [312, 410, 435, 472],
        "STAT": [381, 382, 481],
        "IE":   [342],
        "ECE":  [341],
        "ENGR": [100, 101],
        "MATH": [180, 181, 210, 218],       
    }

    easy_courses_data = {}
    
    try:
        for dept, course_numbers in target_courses.items():
            print(f"\n{'='*60}")
            print(f"⏳ Scraping {dept} Easy Courses...")
            print(f"{'='*60}")
            
            try:
                # Go to find easy courses page
                driver.get("https://uicgrades.com/findEasyCourses.html")
                time.sleep(3)
                
                # Click the dropdown button to open it
                print(f"   🔽 Opening dropdown menu...")
                dropdown_btn = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.CLASS_NAME, "dropDownButton"))
                )
                dropdown_btn.click()
                time.sleep(1)
                
                # Find the dropdown content div
                dropdown_content = WebDriverWait(driver, 5).until(
                    EC.visibility_of_element_located((By.ID, "dataDisplay"))
                )
                print(f"   ✅ Dropdown opened")
                
                # Find the anchor link with data-option matching our department
                print(f"   🔍 Finding {dept} link in dropdown...")
                dept_link = WebDriverWait(driver, 5).until(
                    EC.element_to_be_clickable((By.XPATH, f"//a[@data-option='{dept}']"))
                )
                print(f"   ✅ Found {dept} link")
                
                # Click the department link
                dept_link.click()
                print(f"   ✅ Clicked {dept}")
                time.sleep(2)
                
                # Page now shows all courses for this department
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Find course listings (adjust based on actual structure)
                course_items = soup.find_all(["div", "tr", "li", "article", "section"])
                
                print(f"   🔍 Searching through {len(course_items)} items for target courses...")
                
                courses_found = 0
                courses_found_list = []
                
                for item in course_items:
                    item_text = item.get_text(strip=True)
                    
                    # Check if this item contains one of our target courses
                    for course_num in course_numbers:
                        course_code = f"{dept}{course_num}"
                        
                        # Look for course code in the item text
                        if course_code in item_text or f"{dept} {course_num}" in item_text:
                            # Extract full text for this course
                            clean_text = item.get_text(separator="\n")
                            lines = [line.strip() for line in clean_text.split("\n") if line.strip()]
                            course_content = "\n".join(lines)
                            
                            if len(course_content) > 20:  # Only save if substantial content
                                key = f"easy_courses_{course_code}"
                                easy_courses_data[key] = course_content
                                courses_found += 1
                                courses_found_list.append(course_code)
                                preview = course_content[:80].replace("\n", " ")
                                print(f"      ✅ {course_code}: {preview}...")
                            break
                
                print(f"   ✅ Found {courses_found} target courses for {dept}")
                if courses_found_list:
                    print(f"      Courses: {', '.join(courses_found_list)}")
                
            except Exception as e:
                print(f"   ❌ Error scraping {dept}: {str(e)[:100]}")
                import traceback
                traceback.print_exc()
                driver.save_screenshot(f"debug_easy_{dept}.png")
    
    finally:
        driver.quit()
    
    return easy_courses_data


if __name__ == "__main__":
    print("="*60)
    print("UIC Easy Courses Scraper - DS Major Courses Only")
    print("="*60)
    
    easy_courses_data = scrape_easy_courses()
    
    # Save
    with open("easy_courses_data.json", "w", encoding="utf-8") as f:
        json.dump(easy_courses_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n{'='*60}")
    print(f"✅ Saved {len(easy_courses_data)} easy course records")
    print(f"{'='*60}")
    
    # Print sample
    if easy_courses_data:
        first_key = list(easy_courses_data.keys())[0]
        print(f"\nSample ({first_key}):")
        print(easy_courses_data[first_key][:300])
# scrape_professors.py - FIXED (Imports + syntax)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException  # ADD THIS
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import json
import re

def scrape_professors():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    professors = [
        "David Hayes",
        "Ja Yu",
        "Patrick Troy",
        "Shanon Reckinger",
        "Dale Reed",
        "Scott Reckinger",
        "Mark Hallenbeck",
        "Elena Zheleva",
    ]

    professor_data = {}
    total = 0
    success = 0
    
    try:
        for prof_name in professors:
            total += 1
            print(f"\n[{total}] ⏳ Searching for {prof_name}...")
            
            try:
                # Go to professor search page
                driver.get("https://uicgrades.com/profSearch.html")
                time.sleep(2)
                
                # Find search input
                search_input = WebDriverWait(driver, 5).until(
                    EC.presence_of_element_located((By.ID, "searchBox"))
                )
                
                # Clear and type professor name
                search_input.clear()
                search_input.send_keys(prof_name)
                print(f"   ✅ Typed: {prof_name}")
                time.sleep(1.5)
                
                # Find and click the suggestion item
                print(f"   🔍 Looking for suggestion...")
                
                try:
                    # Wait for suggestions div to be visible
                    suggestions_div = WebDriverWait(driver, 5).until(
                        EC.visibility_of_element_located((By.ID, "suggestions"))
                    )
                    print(f"   ✅ Suggestions dropdown appeared")
                    
                    # Find the suggestion item
                    suggestion_items = driver.find_elements(By.CLASS_NAME, "suggestion-item")
                    
                    if not suggestion_items:
                        print(f"   ⚠️  No suggestion items found")
                        continue
                    
                    print(f"   Found {len(suggestion_items)} suggestion(s)")
                    
                    # Click the first suggestion (or find matching name)
                    suggestion_to_click = None
                    for item in suggestion_items:
                        item_text = item.text.upper()  # CHANGE: .text instead of .get_text()
                        prof_upper = prof_name.upper()
                        
                        # Match if suggestion contains professor name or vice versa
                        if prof_upper in item_text or any(part in item_text for part in prof_upper.split()):
                            suggestion_to_click = item
                            print(f"   ✅ Found matching suggestion: {item.text}")  # CHANGE: .text
                            break
                    
                    # If no exact match, use first suggestion
                    if not suggestion_to_click:
                        suggestion_to_click = suggestion_items[0]
                        print(f"   ⚠️  Using first suggestion: {suggestion_to_click.text}")  # CHANGE: .text
                    
                    # Click the suggestion
                    driver.execute_script("arguments[0].click();", suggestion_to_click)
                    print(f"   ✅ Clicked suggestion")
                    time.sleep(2)
                    
                except TimeoutException:  # NOW IMPORTED
                    print(f"   ❌ Suggestions didn't appear (timeout)")
                    continue
                except Exception as e:
                    print(f"   ❌ Error clicking suggestion: {str(e)[:80]}")
                    continue
                
                # Extract classes
                soup = BeautifulSoup(driver.page_source, "html.parser")
                
                # Find all semester sections
                semester_sections = soup.find_all("div", class_="semester-section")
                
                print(f"   📅 Found {len(semester_sections)} semesters")
                
                # Extract classes from all semesters
                all_classes = []
                for section in semester_sections:
                    # Get semester name
                    semester_h2 = section.find("h2")
                    semester_name = semester_h2.get_text(strip=True) if semester_h2 else "Unknown"
                    
                    # Get class buttons
                    buttons = section.find_all("button", class_="class-button")
                    
                    for btn in buttons:
                        class_text = btn.get_text(strip=True)
                        all_classes.append({
                            "semester": semester_name,
                            "class": class_text
                        })
                
                print(f"   📚 Found {len(all_classes)} total class entries")
                
                # Take only first 5 classes
                classes_to_use = all_classes[:5]
                
                for i, class_info in enumerate(classes_to_use):
                    print(f"      [{i+1}] {class_info['semester']}: {class_info['class']}")
                
                # Format data
                prof_content = f"Professor: {prof_name}\n"
                prof_content += "="*60 + "\n"
                prof_content += f"Classes Taught (most recent 5):\n"
                prof_content += "-"*60 + "\n"
                
                for class_info in classes_to_use:
                    prof_content += f"• {class_info['semester']}: {class_info['class']}\n"
                
                # Add page context
                page_text = soup.get_text(separator="\n")
                lines = [line.strip() for line in page_text.split("\n") if line.strip() and len(line.strip()) > 3]
                context = "\n".join(lines[:50])
                
                prof_content += f"\n\nAdditional Info:\n"
                prof_content += context
                
                key = f"professor_{prof_name.replace(' ', '_')}"
                professor_data[key] = prof_content
                success += 1
                print(f"   ✅ Extracted data for {prof_name}")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)[:100]}")
    
    finally:
        driver.quit()
    
    print(f"\n{'='*60}")
    print(f"✅ Success: {success}/{total} professors scraped")
    print(f"{'='*60}\n")
    
    return professor_data


if __name__ == "__main__":
    print("="*60)
    print("UIC Professor Search Scraper")
    print("="*60)
    
    professor_data = scrape_professors()
    
    # Save
    with open("professor_data.json", "w", encoding="utf-8") as f:
        json.dump(professor_data, f, indent=2, ensure_ascii=False)
    
    print(f"✅ Saved to professor_data.json")
    print(f"Total records: {len(professor_data)}")
    
    # Print samples
    if professor_data:
        for key, content in list(professor_data.items())[:1]:
            print(f"\n{'='*60}")
            print(f"Sample ({key}):")
            print(f"{'='*60}")
            print(content[:600])
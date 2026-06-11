# scrape_catalog_static.py - FIXED (Proper table extraction)

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time
import json
import re

def extract_course_requirements(soup):
    """Extract all course requirements from page"""
    
    requirements = []
    
    # Find main content container
    main_content = soup.find("div", id="textcontainer")
    if not main_content:
        main_content = soup.body
    
    # Find all course tables
    tables = main_content.find_all("table", class_="sc_courselist")
    
    for table_idx, table in enumerate(tables):
        # Find the heading before this table
        heading = None
        prev = table.find_previous(["h2", "h3"])
        if prev:
            heading = prev.get_text(strip=True)
        
        section_data = {
            "heading": heading or f"Section {table_idx + 1}",
            "courses": []
        }
        
        # Extract rows
        rows = table.find_all("tr")
        for row in rows:
            cols = row.find_all(["td", "th"])
            
            if len(cols) >= 2:
                # Get course code (first column)
                code_cell = cols[0].get_text(strip=True)
                
                # Get title (second column)
                title_cell = cols[1].get_text(strip=True)
                
                # Get hours (third column if exists)
                hours_cell = cols[2].get_text(strip=True) if len(cols) >= 3 else ""
                
                # Skip header rows and empty rows
                if code_cell and title_cell and code_cell not in ["Code", ""]:
                    # Skip category headers (they don't have course codes)
                    if not code_cell.startswith(("Select", "Summary", "Total", "Foreign", "Understanding", "Analyzing", "Two", "Free", "Electives", "General and Basic", "Core Courses", "Computer Science", "The following")):
                        course_entry = {
                            "code": code_cell,
                            "title": title_cell,
                            "hours": hours_cell
                        }
                        section_data["courses"].append(course_entry)
        
        if section_data["courses"]:
            requirements.append(section_data)
    
    return requirements

def scrape_catalog_static():
    options = webdriver.ChromeOptions()
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)

    catalog_pages = {
        "DS_BS": "https://catalog.uic.edu/ucat/colleges-depts/engineering/cs/bs-data-science-computer-science/",
    }

    catalog_data = {}
    
    try:
        for page_name, url in catalog_pages.items():
            print(f"\n⏳ Loading {page_name}...")
            
            try:
                driver.get(url)
                time.sleep(3)
                
                soup = BeautifulSoup(driver.page_source, 'html.parser')
                
                # Extract course requirements
                requirements = extract_course_requirements(soup)
                
                # Format as clean text
                output_text = f"DEGREE: {page_name}\n"
                output_text += "="*80 + "\n\n"
                
                for section in requirements:
                    output_text += f"\n{section['heading']}\n"
                    output_text += "-"*60 + "\n"
                    
                    for course in section['courses']:
                        output_text += f"{course['code']}: {course['title']}"
                        if course['hours']:
                            output_text += f" ({course['hours']} hrs)"
                        output_text += "\n"
                
                if len(output_text) > 500:
                    catalog_data[f"catalog_{page_name}"] = output_text
                    print(f"   ✅ Extracted {page_name}")
                    print(f"   📊 Found {sum(len(s['courses']) for s in requirements)} courses")
                else:
                    print(f"   ⚠️  Content too short")
                
            except Exception as e:
                print(f"   ❌ Error: {str(e)}")
                import traceback
                traceback.print_exc()
    
    finally:
        driver.quit()
    
    return catalog_data


if __name__ == "__main__":
    print("="*60)
    print("UIC Catalog Static Pages Scraper")
    print("="*60)
    
    catalog_data = scrape_catalog_static()
    
    with open("catalog_static_data.json", "w", encoding="utf-8") as f:
        json.dump(catalog_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n✅ Saved to catalog_static_data.json")
    print(f"Total records: {len(catalog_data)}")
    
    if catalog_data:
        first_key = list(catalog_data.keys())[0]
        print(f"\n{'='*60}")
        print("FULL OUTPUT:")
        print(f"{'='*60}")
        print(catalog_data[first_key])
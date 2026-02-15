"""
Optional scraper: this script is useful if you want to automate fetching the DPSI weekly menu
and generate `dpsiedge_week_menu.csv`. Note: The repo currently keeps the CSV manually updated; run
this script only if you want to regenerate that CSV programmatically.

If you maintain the CSV manually and host it (e.g., GitHub Pages), the extension can read it
without needing to run this script. This script can be used by an optional CI workflow.
"""

from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd


URL = "https://dpsiedge.edu.in/menu-of-the-week"
CSV_FILE = "menu.csv"

COLUMNS = [
    "Category",
    "Subcategory",
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday"
]

import re
def scrape_menu():
    # Use Selenium to get the full page text
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=options)
    driver.get(URL)

    try:
        WebDriverWait(driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        html = driver.page_source
    finally:
        driver.quit()

    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text("\n")

    # Find the section with the menu for the week
    # We'll look for the block starting with "Menu from" and ending before "OUR SITEMAP" or similar
    menu_match = re.search(r"Menu from.*?(?=OUR SITEMAP|CONTACT US|Menu is subject|Copyright)", text, re.DOTALL|re.IGNORECASE)
    if not menu_match:
        raise RuntimeError("Menu section not found in page text")
    menu_text = menu_match.group(0)

    lines = [line.strip() for line in menu_text.splitlines() if line.strip()]

    # Helper to get a block of 5 items, or fill with 'nothing' if missing
    def get_week_block(start):
        block = []
        for j in range(5):
            if start + j < len(lines):
                val = lines[start + j].strip()
                if val == '' or val.upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"]:
                    block.append('nothing')
                else:
                    block.append(val)
            else:
                block.append('nothing')
        return block

    parsed_rows = []
    # --- BREAKFAST ---
    try:
        bidx = lines.index("BREAKFAST")
        # Morning Drink
        md_idx = lines.index("Morning Drink", bidx)
        parsed_rows.append([
            "BREAKFAST", "Morning Drink", *get_week_block(md_idx+1)
        ])
        # Fruit
        fruit_idx = lines.index("Fruit", bidx)
        parsed_rows.append([
            "BREAKFAST", "Fruit", *get_week_block(fruit_idx+1)
        ])
        # Morning Snack
        ms_idx = lines.index("Morning Snack", bidx)
        parsed_rows.append([
            "BREAKFAST", "Morning Snack", *get_week_block(ms_idx+1)
        ])
    except Exception as e:
        pass

    # --- LUNCH ---
    try:
        lidx = lines.index("LUNCH")
        # Main course - Dish 1
        mc1_idx = lines.index("Main course", lidx)
        parsed_rows.append([
            "LUNCH", "Main course - Dish 1", *get_week_block(mc1_idx+1)
        ])
        # Main course - Dish 2 (look for next after dish 1)
        # Find the next non-empty, non-category line after dish 1 block
        mc2_start = mc1_idx+6
        while mc2_start < len(lines) and (lines[mc2_start].upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"] or lines[mc2_start] == ""):
            mc2_start += 1
        parsed_rows.append([
            "LUNCH", "Main course - Dish 2", *get_week_block(mc2_start)
        ])
        # Main course - Bread
        # Find the next bread block (look for "Tawa roti" or similar)
        bread_start = mc2_start+5
        while bread_start < len(lines) and (lines[bread_start].upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"] or lines[bread_start] == ""):
            bread_start += 1
        parsed_rows.append([
            "LUNCH", "Main course - Bread", *get_week_block(bread_start)
        ])
        # Main course - Rice
        rice_start = bread_start+5
        while rice_start < len(lines) and (lines[rice_start].upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"] or lines[rice_start] == ""):
            rice_start += 1
        parsed_rows.append([
            "LUNCH", "Main course - Rice", *get_week_block(rice_start)
        ])
        # Accompaniments
        acc_start = rice_start+5
        while acc_start < len(lines) and (lines[acc_start].upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"] or lines[acc_start] == ""):
            acc_start += 1
        parsed_rows.append([
            "LUNCH", "Accompaniments", *get_week_block(acc_start)
        ])
        # Accompaniments 2
        acc2_start = acc_start+5
        while acc2_start < len(lines) and (lines[acc2_start].upper() in ["LUNCH", "BREAKFAST", "EVENING SNACK", "DESSERT", "SNACK", "MENU"] or lines[acc2_start] == ""):
            acc2_start += 1
        parsed_rows.append([
            "LUNCH", "Accompaniments 2", *get_week_block(acc2_start)
        ])
        # Dessert
        dessert_idx = None
        for idx, line in enumerate(lines):
            if line.lower() == "dessert":
                dessert_idx = idx
                break
        if dessert_idx:
            parsed_rows.append([
                "LUNCH", "Dessert", *get_week_block(dessert_idx+1)
            ])
    except Exception as e:
        pass

    # --- EVENING SNACK ---
    try:
        esidx = lines.index("EVENING SNACK")
        # Snack
        snack_idx = lines.index("Snack", esidx)
        parsed_rows.append([
            "EVENING SNACK", "Snack", *get_week_block(snack_idx+1)
        ])
        # Evening Drink
        edrink_idx = lines.index("Evening Drink", esidx)
        parsed_rows.append([
            "EVENING SNACK", "Evening Drink", *get_week_block(edrink_idx+1)
        ])
    except Exception as e:
        pass

    # If nothing parsed, raise error
    if not parsed_rows:
        raise RuntimeError("No menu rows parsed from text. The format may have changed. See debug output above.")

    return pd.DataFrame(parsed_rows, columns=COLUMNS)

def update_csv(df, overwrite=True):
    if overwrite:
        df.to_csv(CSV_FILE, index=False)
    else:
        df.to_csv(CSV_FILE, mode="a", header=False, index=False)

if __name__ == "__main__":
    menu_df = scrape_menu()
    update_csv(menu_df, overwrite=True)
    print("CSV updated in standard menu format.")

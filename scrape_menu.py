import requests
from bs4 import BeautifulSoup
import csv

URL = "https://dpsiedge.edu.in/menu-of-the-week"

def fetch_menu(url):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()  # stop if there's an error
    return resp.text

def parse_menu(html):
    soup = BeautifulSoup(html, "html.parser")

    # find the table that contains the weekly menu. Page has nested tables, choose the one with the most rows
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("Could not find any tables on page")
    table = max(tables, key=lambda t: len(t.find_all('tr')))

    # Debug: print out the raw table HTML after finding it
    print("-- Raw table snippet (truncated) --")
    print(table.prettify()[:2000])

    # get table header names (days / columns)
    # pick the row that contains day names (Monday..Friday) instead of relying on <th>
    rows_all = table.find_all("tr")
    weekday_names = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
    header = []
    header_row_index = None
    for i, tr in enumerate(rows_all):
        cells = [c.get_text(strip=True) for c in tr.find_all(["th", "td"]) if c.get_text(strip=True)]
        lower_cells = [c.lower() for c in cells]
        # require at least 3 distinct weekday name cells to match a proper header row
        weekday_cell_count = sum(1 for c in lower_cells if c in weekday_names)
        if weekday_cell_count >= 3:
            header = cells
            header_row_index = i
            break
    if not header:
        header = [th.get_text(strip=True) for th in table.find_all("th")]
    print("-- Table headers (all th text) --")
    print(header)
    print("-- Detected header row cells (from tr scan) --")
    print(header)
    print("Detected header row index:", header_row_index)

    # Determine the indices of weekday columns and the category column
    if header_row_index is None:
        header_cells = [c for c in rows_all[0].find_all(['th','td'])]
    else:
        header_cells = [c for c in rows_all[header_row_index].find_all(['th', 'td'])]
    weekday_positions = [ix for ix, c in enumerate(header_cells) if c.get_text(strip=True).lower() in weekday_names]
    if not weekday_positions:
        # fallback: take first row's th or td values
        header = [c.get_text(strip=True) for c in header_cells if c.get_text(strip=True)]
        days = header[1:]
        day_positions = list(range(1, 1 + len(days)))
        category_col_index = 0
    else:
        days = [header_cells[ix].get_text(strip=True) for ix in weekday_positions]
        day_positions = weekday_positions
        first_day_idx = min(weekday_positions)
        prior_cols = [ix for ix in range(first_day_idx) if ix not in weekday_positions]
        category_col_index = max(prior_cols) if prior_cols else 0
    print("Detected days:", days)

    # get all rows (skip the header row)
    if header_row_index is None:
        rows = rows_all[1:]
    else:
        rows = rows_all[header_row_index + 1 :]
    # Debug: rows count and preview of first row
    print(f"Table has {len(rows_all)} <tr> rows")
    if len(rows_all) > 0:
        print("First row cells (preview):", [c.get_text(strip=True) for c in rows_all[0].find_all(['th','td'])][:10])

    menu = {}  # dictionary: day -> list of meal items by category

    for day in days:
        menu[day] = {}

    # for each row, the first column is the meal category (e.g. BREAKFAST, LUNCH main course, etc.)
    for row in rows:
        cols = row.find_all(["td", "th"])
        if not cols:
            continue
        category = cols[0].get_text(strip=True)
        for i, day in enumerate(days):
            # Sometimes there may be fewer cols than days (or merged cells). Use try/except
            try:
                text = cols[i+1].get_text(strip=True)
            except IndexError:
                text = ""
            # Append to menu structure
            if category not in menu[day]:
                menu[day][category] = text
            else:
                # if already exists, maybe append (for multiple parts)
                menu[day][category] += "; " + text

    return menu

def save_to_csv(menu, filename="dpsiedge_week_menu.csv"):
    # Determine all categories (union across days)
    categories = set()
    for day in menu:
        categories.update(menu[day].keys())
    # Filter out empty categories and obvious table labels
    def is_valid_cat(c):
        if not c:
            return False
        lower = c.strip().lower()
        if lower.startswith('menu from'):
            return False
        if 'allergen' in lower or 'intolerance' in lower:
            return False
        return True
    categories = sorted([c for c in categories if is_valid_cat(c)])

    # Prepare header: Day, then categories...
    header = ["Day"] + categories

    with open(filename, mode="w", newline='', encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        for day, meals in menu.items():
            row = [day]
            for cat in categories:
                row.append(meals.get(cat, ""))
            writer.writerow(row)

if __name__ == "__main__":
    html = fetch_menu(URL)
    menu = parse_menu(html)
    save_to_csv(menu)
    print("Menu scraped and saved to CSV successfully.")
    # Optionally, print the menu
    from pprint import pprint
    pprint(menu)

import sqlite3
import requests
from bs4 import BeautifulSoup
import time
import random

# config
DB_NAME = "ufc_data.db"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

def get_event_urls(conn):
    cursor = conn.cursor()
    cursor.execute("SELECT id, url FROM events")
    return cursor.fetchall()

def scrape_fights_for_event(event_id, event_url):
    try:
        response = requests.get(event_url, headers=HEADERS)
        soup = BeautifulSoup(response.content, 'html.parser')
        rows = soup.find_all('tr', class_='b-fight-details__table-row')
        
        fights_data = []
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) < 8: continue
                
            names_col = cols[1].find_all('p')
            if len(names_col) < 2: continue
            fighter_1 = names_col[0].text.strip()
            fighter_2 = names_col[1].text.strip()
            
            win_text = list(cols[0].stripped_strings)
            winner, loser = "Draw/NC", "Draw/NC"
            
            if len(win_text) > 0:
                first_status = win_text[0].lower()
                if 'win' in first_status:
                    winner, loser = fighter_1, fighter_2
                elif 'win' not in first_status or (len(win_text) > 1 and 'win' in win_text[1].lower()):
                    winner, loser = fighter_2, fighter_1
                if 'draw' in first_status or 'nc' in first_status:
                    winner, loser = "Draw/NC", "Draw/NC"
                    
            weight_class = cols[6].text.strip() 
            method = cols[7].text.strip()
            round_num = cols[8].text.strip()
            time_val = cols[9].text.strip()
            
            fight_id = f"{event_id}_{fighter_1}_{fighter_2}".replace(" ", "")
            fights_data.append((fight_id, event_id, winner, loser, method, round_num, time_val, weight_class))
            
        return fights_data
        
    except Exception as e:
        print(f"Error scraping {event_url}: {e}")
        return []

def main():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    print("Wiping table to ensure clean schema...")
    cursor.execute("DELETE FROM fights")
    conn.commit()
    
    events = get_event_urls(conn)
    total = len(events)
    print(f"Rescraping {total} events...")
    
    for i, (event_id, url) in enumerate(events):
        fights = scrape_fights_for_event(event_id, url)
        
        if fights:
            # Added weight_class to INSERT
            cursor.executemany('''
                INSERT OR IGNORE INTO fights (fight_id, event_id, winner, loser, method, round, time, weight_class)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', fights)
            conn.commit()
            
            if i == 0:
                print(f"DEBUG: {fights[0][2]} vs {fights[0][3]} ({fights[0][7]})") # Print weight class to verify
                
            print(f"[{i+1}/{total}] Saved {len(fights)} fights.")
            
        time.sleep(random.uniform(0.4, 0.7))

    conn.close()

if __name__ == "__main__":
    main()
import requests
from bs4 import BeautifulSoup
import sqlite3
import time
import pandas as pd

# config
DB_NAME = "ufc_data.db"
BASE_URL = "http://ufcstats.com/statistics/events/completed?page=all"
HEADERS = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

# database setup
def setup_database():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS events (
            id TEXT PRIMARY KEY,
            name TEXT,
            date TEXT,
            location TEXT,
            url TEXT
        )
    ''')
    
    # Create Fights Table if not exists
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS fights (
            fight_id TEXT PRIMARY KEY,
            event_id TEXT,
            winner TEXT,
            loser TEXT,
            method TEXT,
            round INTEGER,
            time TEXT,
            weight_class TEXT,
            FOREIGN KEY(event_id) REFERENCES events(id)
        )
    ''')
    
    conn.commit()
    return conn

# scraper
def scrape_events(conn):
    print("Please wait, accessing UFC Stats...")
    response = requests.get(BASE_URL, headers=HEADERS)
    soup = BeautifulSoup(response.content, 'html.parser')
    
    # The events are in a table row format
    rows = soup.find_all('tr', class_='b-statistics__table-row')
    
    events_data = []
    
    # Skip the first row (header)
    for row in rows[1:]:
        cols = row.find_all('td')
        if len(cols) < 2:
            continue
            
        # Extract Link and Name
        link_tag = cols[0].find('a')
        if not link_tag:
            continue
            
        event_url = link_tag['href']
        event_name = link_tag.text.strip()
        
        # Extract Date
        event_date = cols[0].find('span').text.strip()
        
        # Extract Location
        event_location = cols[1].text.strip()
        event_id = event_url.split('/')[-1]
        
        events_data.append((event_id, event_name, event_date, event_location, event_url))

    print(f"Found {len(events_data)} events. Saving to database...")
    
    cursor = conn.cursor()
    cursor.executemany('''
        INSERT OR IGNORE INTO events (id, name, date, location, url)
        VALUES (?, ?, ?, ?, ?)
    ''', events_data)
    
    conn.commit()
    print("Events saved successfully.")

# main
if __name__ == "__main__":
    conn = setup_database()
    scrape_events(conn)
    
    # prints the first 5 events to prove it worked
    print("\n--- VERIFICATION: TOP 5 LATEST EVENTS ---")
    df = pd.read_sql("SELECT * FROM events LIMIT 5", conn)
    print(df)
    
    conn.close()
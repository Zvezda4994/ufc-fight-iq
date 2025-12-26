import requests
from bs4 import BeautifulSoup

url = "http://ufcstats.com/event-details/bc0f994de0521926" 
headers = {'User-Agent': 'Mozilla/5.0'}

print(f"Inspecting: {url} ...")
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.content, 'html.parser')

rows = soup.find_all('tr', class_='b-fight-details__table-row')

found = False
for i, row in enumerate(rows):
    cols = row.find_all('td')
    
   
    if len(cols) > 0:
        print(f"\n--- SUCCESS: Found Data at Row {i} ---")
        
       
        print("WIN/LOSS COLUMN (HTML):")
        print(cols[0].prettify())
        
       
        print("\nNAMES COLUMN (HTML):")
        print(cols[1].prettify())
        
        found = True
        break 

if not found:
    print("Error: No data rows found.")
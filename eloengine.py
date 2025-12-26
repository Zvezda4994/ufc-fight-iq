import sqlite3
import pandas as pd
from datetime import datetime

# thank you csci3141

# config
DB_NAME = "ufc_data.db"
STARTING_ELO = 1500
K_FACTOR_BASE = 32 # Standard volatility

# elo calculation 
def get_expected_score(rating_a, rating_b):
    """
    Returns the probability (0-1) that A beats B.
    """
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def get_k_factor(method, round_num):
    """
    Dynamic K-Factor: KOs and early finishes mean more than Decisions.
    """
    k = K_FACTOR_BASE
    
    # input processing
    method = method.lower()
    round_num = str(round_num).strip()
    
    if "ko" in method or "tko" in method:
        k *= 1.5  # boost for KOs
        if round_num == "1":
            k *= 1.2 # Extra boost for 1st round KO
    elif "submission" in method:
        k *= 1.3 # boost for Subs
        
    return k

def process_history():
    conn = sqlite3.connect(DB_NAME)
    
    print("Loading fight history...")
    # Join fights with events to get the Date
    query = """
        SELECT f.winner, f.loser, f.method, f.round, e.date 
        FROM fights f
        JOIN events e ON f.event_id = e.id
    """
    df = pd.read_sql(query, conn)
    
    # preprocessing
    # convert given date to datetime obj
    df['date_obj'] = pd.to_datetime(df['date'], format='%B %d, %Y', errors='coerce')
    
    # Drop rows where date failed to parse
    df = df.dropna(subset=['date_obj'])
    
    # sort old to new
    df = df.sort_values('date_obj')
    
    print(f"Processing {len(df)} fights chronologically...")
    
    # calculate elo
    ratings = {} # Dictionary: {"Conor McGregor": 1450, ...}
    
    def get_rating(fighter):
        return ratings.get(fighter, STARTING_ELO)
    
    history = []
    
    for index, row in df.iterrows():
        winner = row['winner'].strip()
        loser = row['loser'].strip()
        method = row['method']
        r_num = row['round']
        date = row['date_obj']
        
        # Skip draws/NC for simplicity in V1
        if winner == "Draw/NC" or loser == "Draw/NC":
            continue
            
        # get curr rating
        r_winner = get_rating(winner)
        r_loser = get_rating(loser)
        
        # get expected score
        expected_winner = get_expected_score(r_winner, r_loser)
        
        # get k
        k = get_k_factor(method, r_num)
        
        # Update Ratings
        rating_change = k * (1 - expected_winner)
        
        new_r_winner = r_winner + rating_change
        new_r_loser = r_loser - rating_change
        
        # Save to dictionary
        ratings[winner] = new_r_winner
        ratings[loser] = new_r_loser
        
        # log history
        history.append({
            'date': date,
            'winner': winner,
            'loser': loser,
            'winner_elo': new_r_winner,
            'loser_elo': new_r_loser
        })

    # save results
    # Convert current ratings to DataFrame
    results_df = pd.DataFrame(list(ratings.items()), columns=['Fighter', 'ELO'])
    results_df = results_df.sort_values('ELO', ascending=False)
    
    print("\n--- TOP 10 FIGHTERS (CURRENT ELO) ---")
    print(results_df.head(10))
    
    # save to csv
    results_df.to_csv("current_ratings.csv", index=False)
    print("\nSaved ratings to 'current_ratings.csv'")
    conn.close()

if __name__ == "__main__":
    process_history()
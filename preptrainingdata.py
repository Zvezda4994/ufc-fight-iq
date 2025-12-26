import sqlite3
import pandas as pd
from datetime import datetime
import random

# config
DB_NAME = "ufc_data.db"
STARTING_ELO = 1500
K_FACTOR_BASE = 32

def get_expected_score(rating_a, rating_b):
    return 1 / (1 + 10 ** ((rating_b - rating_a) / 400))

def get_k_factor(method, round_num):
    k = K_FACTOR_BASE
    method = method.lower()
    round_num = str(round_num).strip()
    if "ko" in method or "tko" in method:
        k *= 1.5
        if round_num == "1": k *= 1.2
    elif "submission" in method:
        k *= 1.3
    return k

def main():
    conn = sqlite3.connect(DB_NAME)
    
    print("Loading fight history...")
    query = """
        SELECT f.winner, f.loser, f.method, f.round, e.date 
        FROM fights f
        JOIN events e ON f.event_id = e.id
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    df['date_obj'] = pd.to_datetime(df['date'], format='%B %d, %Y', errors='coerce')
    df = df.dropna(subset=['date_obj']).sort_values('date_obj')
    
    elo = {}            # { "Petr Yan": 1500 }
    last_fight_date = {} # { "Petr Yan": datetime(2023, 3, 4) }
    streak = {}         # { "Petr Yan": 13 }
    total_fights = {}   # { "Petr Yan": 20 }

    training_data = []
    
    print(f"Engineering features for {len(df)} fights...")
    
    for index, row in df.iterrows():
        winner = row['winner'].strip()
        loser = row['loser'].strip()
        date = row['date_obj']
        
        if winner == "Draw/NC" or loser == "Draw/NC":
            continue
            
        # initiliase fighters
        for f in [winner, loser]:
            if f not in elo: elo[f] = STARTING_ELO
            if f not in streak: streak[f] = 0
            if f not in total_fights: total_fights[f] = 0
            # Default "last fight" to 365 days ago for debuts (neutral start)
            if f not in last_fight_date: last_fight_date[f] = date - pd.Timedelta(days=365)

        # pre-fight stats
        
        # INACTIVITY (Months since last fight)
        days_since_w = (date - last_fight_date[winner]).days
        months_since_w = max(0, days_since_w / 30)
        
        days_since_l = (date - last_fight_date[loser]).days
        months_since_l = max(0, days_since_l / 30)
        
        # ELO
        elo_w = elo[winner]
        elo_l = elo[loser]
        
        # STREAK
        streak_w = streak[winner]
        streak_l = streak[loser]
        
        # EXPERIENCE
        exp_w = total_fights[winner]
        exp_l = total_fights[loser]
        
        # make training row (randomize winner/loser order)
        if random.random() > 0.5:
            # Case: Fighter A is Winner
            row_data = {
                'elo_diff': elo_w - elo_l,
                'streak_diff': streak_w - streak_l,
                'months_since_diff': months_since_w - months_since_l, # Negative is good (less rust)
                'exp_diff': exp_w - exp_l,
                'target': 1
            }
        else:
            # Case: Fighter A is Loser
            row_data = {
                'elo_diff': elo_l - elo_w,
                'streak_diff': streak_l - streak_w,
                'months_since_diff': months_since_l - months_since_w,
                'exp_diff': exp_l - exp_w,
                'target': 0
            }
            
        training_data.append(row_data)
        
        # update fighter stats
        
        # Update ELO
        k = get_k_factor(row['method'], row['round'])
        expected_w = get_expected_score(elo_w, elo_l)
        change = k * (1 - expected_w)
        elo[winner] += change
        elo[loser] -= change
        
        # Update Dates
        last_fight_date[winner] = date
        last_fight_date[loser] = date
        
        # Update Streaks (Winner +1, Loser resets to 0)
        streak[winner] += 1
        streak[loser] = 0
        
        # Update Experience
        total_fights[winner] += 1
        total_fights[loser] += 1

    # Save
    train_df = pd.DataFrame(training_data)
    train_df.to_csv("ufc_training_data_v2.csv", index=False)
    print(f"Done. Saved 'ufc_training_data_v2.csv' with {train_df.shape[1]} columns.")
    print(train_df.head())

if __name__ == "__main__":
    main()
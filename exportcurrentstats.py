import sqlite3
import pandas as pd
from datetime import datetime

# CONFIG
DB_NAME = "ufc_data.db"

def main():
    conn = sqlite3.connect(DB_NAME)
    # Get all fights
    query = """
        SELECT f.winner, f.loser, f.weight_class, f.method, f.round, e.date 
        FROM fights f 
        JOIN events e ON f.event_id = e.id
    """
    df = pd.read_sql(query, conn)
    conn.close()
    
    df['date_obj'] = pd.to_datetime(df['date'], format='%B %d, %Y', errors='coerce')
    df = df.dropna(subset=['date_obj']).sort_values('date_obj')
    
    # trackers
    elo = {}
    streak = {}
    last_date = {}
    total_fights = {}
    current_weight = {}
    
    # strenght of schedule
    opponent_history = {} # { "Jon Jones": [1600, 1650, 1780] }

    for _, row in df.iterrows():
        w, l = row['winner'].strip(), row['loser'].strip()
        wc = row['weight_class'].strip()
        
        if w == "Draw/NC": continue
            
        # initialise fighers
        for f in [w, l]:
            if f not in elo: 
                elo[f] = 1500
                streak[f] = 0
                total_fights[f] = 0
                last_date[f] = row['date_obj'] - pd.Timedelta(days=365)
                opponent_history[f] = []
            
            if wc != "Catch Weight":
                current_weight[f] = wc
        
        # strength of schedule update (how strong their record is)
        # elo of opponent fought
        opponent_history[w].append(elo[l])
        opponent_history[l].append(elo[w])
        
        # Keep only last 3 opponents for "Recent Form"
        opponent_history[w] = opponent_history[w][-3:]
        opponent_history[l] = opponent_history[l][-3:]

        # update elo
        prob = 1 / (1 + 10 ** ((elo[l] - elo[w]) / 400))
        
        # k for finish
        k = 32
        if "ko" in row['method'].lower() or "tko" in row['method'].lower():
            k = 48 # 1.5x Bonus for KO
        elif "submission" in row['method'].lower():
            k = 42 # 1.3x Bonus for Sub
            
        elo[w] += k * (1 - prob)
        elo[l] -= k * (1 - prob)
        
        # update trackers
        streak[w] += 1
        streak[l] = 0
        total_fights[w] += 1
        total_fights[l] += 1
        last_date[w] = row['date_obj']
        last_date[l] = row['date_obj']

    # export stats
    data = []
    today = datetime.now()
    
    for f in elo:
        inactive = (today - last_date[f]).days / 30
        
        # calculate average opponent elo for Strength of Schedule
        past_opps = opponent_history[f]
        if len(past_opps) > 0:
            avg_opp_elo = sum(past_opps) / len(past_opps)
        else:
            avg_opp_elo = 1500 # Default for debutants
            
        data.append({
            'Fighter': f, 
            'ELO': round(elo[f], 2), 
            'Streak': streak[f],
            'Avg_Opp_ELO': round(avg_opp_elo, 2), 
            'Months_Inactive': round(inactive, 1),
            'Total_Fights': total_fights[f],
            'Weight_Class': current_weight.get(f, "Unknown")
        })
        
    pd.DataFrame(data).to_csv("fighter_stats.csv", index=False)
    print("Exported stats with Strength of Schedule (Avg_Opp_ELO).")

if __name__ == "__main__":
    main()
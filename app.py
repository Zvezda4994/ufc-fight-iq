import streamlit as st
import pandas as pd
import joblib

# page config
st.set_page_config(page_title="UFC FightIQ", layout="centered")

# assets
@st.cache_data
def load_data():
    return pd.read_csv("fighter_stats.csv")

@st.cache_resource
def load_model():
    return joblib.load("ufc_predictor_v2.pkl")

df = load_data()
model = load_model()

# header
st.title(" UFC FightIQ Matchup Predictor")
st.markdown("### AI Matchup Analysis")
st.write(f"Database contains **{len(df)}** fighters. Model Accuracy: **58.8%**")

# sidebar config
st.sidebar.header("Configuration")
if 'Weight_Class' in df.columns:
    weight_classes = ['All'] + sorted(df['Weight_Class'].astype(str).unique().tolist())
    selected_class = st.sidebar.selectbox("Filter by Weight Class", weight_classes, index=0)
    
    if selected_class != 'All':
        filtered_df = df[df['Weight_Class'] == selected_class]
    else:
        filtered_df = df
else:
    filtered_df = df 

# fighter selection 
col1, col2 = st.columns(2)

with col1:
    st.subheader("🔴 Red Corner")
    fighter_1 = st.selectbox("Select Fighter A", filtered_df['Fighter'].sort_values(), index=0)
    stats_1 = df[df['Fighter'] == fighter_1].iloc[0]
    
    col_a, col_b = st.columns(2)
    col_a.metric("ELO", stats_1['ELO'])
    if 'Avg_Opp_ELO' in stats_1:
        col_b.metric("SoS", stats_1['Avg_Opp_ELO'])
    
    st.text(f"Streak: {stats_1['Streak']} wins")
    st.text(f"Inactive: {stats_1['Months_Inactive']} mos")

with col2:
    st.subheader("🔵 Blue Corner")
    # Default index to 1 to avoid duplicate error on loading
    default_index = 1 if len(filtered_df) > 1 else 0
    fighter_2 = st.selectbox("Select Fighter B", filtered_df['Fighter'].sort_values(), index=default_index)
    stats_2 = df[df['Fighter'] == fighter_2].iloc[0]
    
    col_a, col_b = st.columns(2)
    col_a.metric("ELO", stats_2['ELO'])
    if 'Avg_Opp_ELO' in stats_2:
        col_b.metric("SoS", stats_2['Avg_Opp_ELO'])
        
    st.text(f"Streak: {stats_2['Streak']} wins")
    st.text(f"Inactive: {stats_2['Months_Inactive']} mos")

# prediction
if st.button("PREDICT WINNER", type="primary"):
    if fighter_1 == fighter_2:
        st.error("Please select two different fighters.")
    else:
        # prediction logic
        WEIGHT_ORDER = {
            'Flyweight': 1, 'Bantamweight': 2, 'Featherweight': 3, 'Lightweight': 4,
            'Welterweight': 5, 'Middleweight': 6, 'Light Heavyweight': 7, 'Heavyweight': 8
        }
        
        # get weight class (default 0)
        w1_class = stats_1.get('Weight_Class', 'Unknown')
        w2_class = stats_2.get('Weight_Class', 'Unknown')
        s1 = WEIGHT_ORDER.get(w1_class, 0)
        s2 = WEIGHT_ORDER.get(w2_class, 0)
        
        # get adjusted elo
        adj_elo_1 = stats_1['ELO']
        adj_elo_2 = stats_2['ELO']
        penalty_msg = ""
        
        # size penalty depending on weightclass
        if s1 > 0 and s2 > 0:
            diff = s1 - s2
            
            # If Fighter 1 is bigger (Positive Diff)
            if diff > 0:
                penalty_pct = diff * 0.10
                adj_elo_2 = adj_elo_2 * (1 - penalty_pct)
                penalty_msg = f"SIZE MISMATCH: {fighter_2} loses {int(penalty_pct*100)}% effective ELO due to size difference ({diff} classes)."
            
            # If Fighter 2 is bigger (Negative Diff)
            elif diff < 0:
                penalty_pct = abs(diff) * 0.10
                adj_elo_1 = adj_elo_1 * (1 - penalty_pct)
                penalty_msg = f"SIZE MISMATCH: {fighter_1} loses {int(penalty_pct*100)}% effective ELO due to size difference ({abs(diff)} classes)."

        # prepare input data
        input_data = pd.DataFrame({
            'elo_diff': [adj_elo_1 - adj_elo_2],
            'streak_diff': [stats_1['Streak'] - stats_2['Streak']],
            'months_since_diff': [stats_1['Months_Inactive'] - stats_2['Months_Inactive']],
            'exp_diff': [stats_1['Total_Fights'] - stats_2['Total_Fights']]
        })
        
        # make the prediction
        prediction = model.predict(input_data)[0]
        probs = model.predict_proba(input_data)[0]
        
        p1_prob = probs[1]
        
        if p1_prob > 0.5:
            winner = fighter_1
            confidence = p1_prob
        else:
            winner = fighter_2
            confidence = 1.0 - p1_prob
            
        # result
        st.divider()
        st.success(f"Prediction: **{winner}** will win!")
        st.write(f"Confidence: **{confidence:.1%}**")
        st.progress(confidence)
        
        # show penalty
        if penalty_msg:
            st.warning(penalty_msg)
        
        # explanation and reasoning
        st.subheader("Key Factors")
        
        # ELO Context (Show Real vs Adjusted)
        winner_stats = stats_1 if winner == fighter_1 else stats_2
        winner_adj = adj_elo_1 if winner == fighter_1 else adj_elo_2
        loser_adj = adj_elo_2 if winner == fighter_1 else adj_elo_1
        
        elo_gap = winner_adj - loser_adj
        if elo_gap > 0:
            st.success(f"📈 Effective Skill Edge: {winner} has a higher adjusted ELO (+{int(elo_gap)}).")
        
        # Momentum
        streak_gap = winner_stats['Streak'] - (stats_2['Streak'] if winner == fighter_1 else stats_1['Streak'])
        if streak_gap >= 3:
            st.info(f"🔥 Momentum: {winner} is on a {int(winner_stats['Streak'])}-fight win streak.")
            
        # Activity
        loser_inactive = stats_2['Months_Inactive'] if winner == fighter_1 else stats_1['Months_Inactive']
        winner_inactive = winner_stats['Months_Inactive']
        if (loser_inactive - winner_inactive) > 6:
            st.info(f"⚡ Activity: {winner} has been far more active.")
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier # Adding a stronger brain
from sklearn.metrics import accuracy_score
import joblib

# load data
print("Loading V2 training data...")
df = pd.read_csv("ufc_training_data_v2.csv")

# prepare data
features = ['elo_diff', 'streak_diff', 'months_since_diff', 'exp_diff']
X = df[features]
y = df['target']

X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# train (using random forest because its better at complex patterns)
print("Training Random Forest Model...")
model = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
model.fit(X_train, y_train)

# evaluate
predictions = model.predict(X_test)
acc = accuracy_score(y_test, predictions)

print(f"\n--- UPGRADED MODEL RESULTS ---")
print(f"Accuracy: {acc:.2%}")

# feature importance
importances = model.feature_importances_
print("\n--- WHAT MATTERS MOST? ---")
for feature, importance in zip(features, importances):
    print(f"{feature}: {importance:.1%}")

joblib.dump(model, "ufc_predictor_v2.pkl")
import pandas as pd
from sklearn.linear_model import LogisticRegression
import joblib

data = {
    "rating": [4.8, 4.5, 4.0, 3.2, 2.8, 2.3, 1.9],
    "reviews": [2000, 1500, 500, 100, 50, 20, 5],
    "installs": [500000, 200000, 50000, 5000, 1000, 300, 100],
    "label": [1, 1, 1, 1, 0, 0, 0]  # 1 = Safe, 0 = Fake
}

df = pd.DataFrame(data)

X = df[["rating", "reviews", "installs"]]
y = df["label"]

model = LogisticRegression()
model.fit(X, y)

joblib.dump(model, "model.pkl")

print("✅ Model trained & saved")

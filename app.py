from flask import Flask, render_template, request, redirect, session
from google_play_scraper import app as playstore_app, reviews
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "loanshield_secret_key"

# ---------------- FILES ----------------
NBFC_FILE = "nbfc_playstore_mapping.csv"
REPORT_FILE = "reported_apps.csv"
USER_FILE = "users.csv"

# ---------------- LOAD DATA ----------------
df_nbfc = pd.read_csv(NBFC_FILE) if os.path.exists(NBFC_FILE) else pd.DataFrame(
    columns=["nbfc_name", "playstore_name", "app_id", "type"]
)

df_reports = pd.read_csv(REPORT_FILE) if os.path.exists(REPORT_FILE) else pd.DataFrame(
    columns=["email", "app_name", "reason"]
)

def load_users():
    if not os.path.exists(USER_FILE):
        return pd.DataFrame(columns=["name", "email", "password"])

    df = pd.read_csv(USER_FILE)
    df["name"] = df["name"].astype(str).str.strip()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["password"] = df["password"].astype(str).str.strip()
    return df

# ---------------- AUTH HELPERS ----------------
def is_logged_in():
    return "email" in session

def already_reported(email, app_name):
    match = df_reports[
        (df_reports["email"] == email) &
        (df_reports["app_name"].str.lower() == app_name.lower())
    ]
    return not match.empty

# ---------------- CORE HELPERS ----------------
def find_nbfc_by_app_id(app_id, app_title=""):
    app_id = str(app_id).lower()
    for _, row in df_nbfc.iterrows():
        if str(row["app_id"]).lower() == app_id:
            return True, row["nbfc_name"], row["type"]
    return False, None, None

def is_loan_app(title):
    return any(k in title.lower() for k in ["loan", "credit", "emi", "finance"])

# ---------------- REAL REVIEW ANALYSIS (ADDED) ----------------
def analyze_reviews(app_id, max_reviews=120):
    try:
        result, _ = reviews(app_id, lang="en", country="in", count=max_reviews)
    except:
        return {
            "sentiment": "Negative",
            "summary": "No user reviews available. This increases risk.",
            "negative_ratio": 1,
            "total": 0
        }

    if not result:
        return {
            "sentiment": "Negative",
            "summary": "No user reviews available. This increases risk.",
            "negative_ratio": 1,
            "total": 0
        }

    negative_keywords = [
        "scam", "fraud", "fake", "harassment", "blackmail",
        "threat", "abuse", "privacy", "cheat", "worst"
    ]

    positive = 0
    negative = 0

    for r in result:
        text = r.get("content", "").lower()
        if any(k in text for k in negative_keywords):
            negative += 1
        else:
            positive += 1

    total = positive + negative
    neg_ratio = negative / total if total else 0

    # ⭐ SENTIMENT LABEL (WHAT UI SHOWS)
    if neg_ratio >= 0.35:
        sentiment = "Negative"
    elif neg_ratio >= 0.15:
        sentiment = "Mixed"
    else:
        sentiment = "Positive"

    summary = (
        f"Based on {total} recent user reviews: "
        f"{positive} positive, {negative} negative complaints detected."
    )

    return {
        "sentiment": sentiment,
        "summary": summary,
        "negative_ratio": neg_ratio,
        "total": total
    }

# ---------------- PERMISSION RISK ----------------
def permission_risk_analysis_by_reviews(app_id, max_reviews=100):
    try:
        result, _ = reviews(app_id, lang="en", country="in", count=max_reviews)
    except:
        return "High Risk"

    keywords = ["permission", "privacy", "sms", "contacts", "location", "camera"]
    mentions = sum(any(k in r["content"].lower() for k in keywords) for r in result)
    ratio = mentions / len(result) if result else 1

    if ratio > 0.1:
        return "High Risk"
    elif ratio > 0.03:
        return "Medium Risk"
    return "Low Risk"

# ---------------- AUTH ROUTES ----------------
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        df_users = load_users()

        user = df_users[(df_users["email"] == email) & (df_users["password"] == password)]
        if not user.empty:
            session["email"] = email
            session["name"] = user.iloc[0]["name"]
            return redirect("/")
        return "Invalid credentials"

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        name = request.form["name"].strip()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
        df_users = load_users()

        if email in df_users["email"].values:
            return "User already exists"

        df_users.loc[len(df_users)] = [name, email, password]
        df_users.to_csv(USER_FILE, index=False)
        return redirect("/login")

    return render_template("register.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- MAIN ROUTES ----------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/predict", methods=["POST"])
def predict():
    if not is_logged_in():
        return redirect("/login")

    user_input = request.form.get("app_name")
    email = session["email"]

    details = playstore_app(user_input)
    app_title = details.get("title", user_input)
    app_id = details.get("appId", user_input)

    rating = details.get("score", 0)
    installs = details.get("installs", "N/A")

    review_data = analyze_reviews(app_id)
    permission_risk = permission_risk_analysis_by_reviews(app_id)
    nbfc_registered, _, _ = find_nbfc_by_app_id(app_id, app_title)

    # ---------------- FINAL STATUS LOGIC ----------------
    status = "Safe"
    reason = "No major risk indicators detected."

    if not is_loan_app(app_title):
        status = "Not a Loan App"
        reason = "This application does not provide loan services."

    elif not nbfc_registered:
        status = "Suspicious"
        reason = "Loan app without registered NBFC."

    elif rating and rating < 3.5:
        status = "Caution"
        reason = "Low Play Store rating detected."

    elif review_data["sentiment"] == "Negative":
        status = "Caution"
        reason = "User reviews indicate negative experiences."

    elif permission_risk in ["Medium Risk", "High Risk"]:
        status = "Caution"
        reason = "Permission-related risks detected."

    if already_reported(email, app_title):
        reason += " ⚠️ Reported earlier by users."

    return render_template(
        "result.html",
        name=app_title,
        rating=rating if rating else "N/A",
        installs=installs,
        nbfc_registered="Yes" if nbfc_registered else "No",
        sentiment=review_data["sentiment"],        # ⭐ ONLY WORD
        review_summary=review_data["summary"],     # ⭐ DETAILED TEXT
        permission_risk=permission_risk,
        status=status,
        reason=reason
    )

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

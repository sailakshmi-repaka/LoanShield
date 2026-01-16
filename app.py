from flask import Flask, render_template, request, redirect, session
from google_play_scraper import app as playstore_app, reviews, search
from google_play_scraper.exceptions import NotFoundError
import pandas as pd
import os

app = Flask(__name__)
app.secret_key = "loanshield_secret_key"

# ---------------- FILES ----------------
NBFC_FILE = "nbfc_playstore_mapping.csv"
REPORT_FILE = "reported_apps.csv"
USER_FILE = "users.csv"

# ---------------- ENSURE FILES EXIST (RENDER SAFE) ----------------
for file, cols in [
    (NBFC_FILE, ["nbfc_name", "playstore_name", "app_id", "type"]),
    (REPORT_FILE, ["email", "app_name", "reason"]),
    (USER_FILE, ["name", "email", "password"]),
]:
    if not os.path.exists(file):
        pd.DataFrame(columns=cols).to_csv(file, index=False)

# ---------------- LOAD DATA ----------------
df_nbfc = pd.read_csv(NBFC_FILE)
df_reports = pd.read_csv(REPORT_FILE)

def load_users():
    df = pd.read_csv(USER_FILE)
    df["name"] = df["name"].astype(str).str.strip()
    df["email"] = df["email"].astype(str).str.strip().str.lower()
    df["password"] = df["password"].astype(str).str.strip()
    return df

# ---------------- AUTH HELPERS ----------------
def is_logged_in():
    return "email" in session

def already_reported(email, app_name):
    if df_reports.empty:
        return False
    return not df_reports[
        (df_reports["email"] == email) &
        (df_reports["app_name"].str.lower() == app_name.lower())
    ].empty

def get_report_count(app_name):
    return len(df_reports[df_reports["app_name"].str.lower() == app_name.lower()])

# ---------------- CORE HELPERS ----------------
def find_nbfc_by_app_id(app_id):
    for _, row in df_nbfc.iterrows():
        if str(row["app_id"]).lower() == str(app_id).lower():
            return True, row["nbfc_name"], row["type"]
    return False, None, None

def is_loan_app(title):
    return any(k in title.lower() for k in ["loan", "credit", "emi", "finance"])

# ---------------- REVIEW ANALYSIS (UNCHANGED LOGIC) ----------------
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

    positive_words = ["good", "easy", "fast", "helpful", "smooth", "best"]
    negative_words = [ "scam", "fraud", "fake", "harassment", "privacy", "permission", "contacts", "sms", "threat", "abuse", "cheat" ] 
    positive = 0 
    negative = 0 
    permission_mentions = 0 
    for r in result: 
        text = r.get("content", "").lower() 
        if any(w in text for w in positive_words): 
         positive += 1 
        if any(w in text for w in negative_words): 
          negative += 1 
        if any(w in text for w in ["permission", "contacts", "sms", "privacy"]): 
          permission_mentions += 1 
    total = len(result) 
    # ---- Sentiment ---- 
    if negative / total > 0.25: 
        sentiment = "Mostly Negative" 
    elif positive / total > 0.5: 
        sentiment = "Mostly Positive" 
    else: sentiment = "Mixed"

    summary = f"Based on {total} recent user reviews: {positive} positive, {negative} negative complaints detected."

    return {"sentiment": sentiment, "summary": summary, "total": total}

# ---------------- PERMISSION RISK ----------------
def permission_risk_analysis_by_reviews(app_id):
    try:
        result, _ = reviews(app_id, lang="en", country="in", count=100)
    except:
        return "High Risk"

    keywords = ["permission", "privacy", "sms", "contacts", "location", "camera"]
    mentions = sum(any(k in r.get("content", "").lower() for k in keywords) for r in result)
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
        df_users = load_users()
        email = request.form["email"].strip().lower()
        password = request.form["password"].strip()
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
        df_users = load_users()
        email = request.form["email"].strip().lower()
        if email in df_users["email"].values:
            return "User already exists"
        df_users.loc[len(df_users)] = [
            request.form["name"].strip(),
            email,
            request.form["password"].strip()
        ]
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

    user_input = request.form.get("app_name").strip()

    # 🔹 Resolve app name → app id (ADDED, NOT REPLACING)
    try:
        if "." not in user_input:
            search_results = search(user_input, n_hits=1)
            if not search_results:
                raise NotFoundError
            app_id = search_results[0]["appId"]
        else:
            app_id = user_input

        details = playstore_app(app_id)
    except:
        return render_template(
            "result.html",
            name=user_input,
            rating="N/A",
            installs="N/A",
            nbfc_registered="No",
            sentiment="Unavailable",
            review_summary="Unable to fetch Play Store data at the moment.",
            permission_risk="Unavailable",
            status="Caution",
            reason="Play Store data could not be fetched. Try again later."
        )

    app_title = details.get("title", user_input)
    rating = details.get("score", 0)
    installs = details.get("installs", "N/A")

    review_data = analyze_reviews(app_id)
    permission_risk = permission_risk_analysis_by_reviews(app_id)
    nbfc_registered, _, _ = find_nbfc_by_app_id(app_id)

    # ---------------- ORIGINAL STATUS LOGIC (UNCHANGED) ----------------
    status = "Safe"
    reason = "No major risk indicators detected."

    if review_data["total"] == 0:
        status = "Caution"
        reason = "No user reviews available."

    elif not is_loan_app(app_title):
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

    # ---------------- USER REPORT OVERRIDE (ADDED) ----------------
    report_count = get_report_count(app_title)

    if report_count >= 10:
        status = "Risky"
        reason = f"This app has been reported by {report_count} users on LoanShield."

    elif report_count >= 5 and status == "Safe":
        status = "Caution"
        reason += f" ⚠️ Reported by {report_count} users on LoanShield."

    return render_template(
        "result.html",
        name=app_title,
        rating=rating if rating else "N/A",
        installs=installs,
        nbfc_registered="Yes" if nbfc_registered else "No",
        sentiment=review_data["sentiment"],
        review_summary=review_data["summary"],
        permission_risk=permission_risk,
        status=status,
        reason=reason
    )

@app.route("/report", methods=["POST"])
def report():
    if not is_logged_in():
        return "Please login to report"

    global df_reports
    app_name = request.form.get("app_name", "").strip()
    reason = request.form.get("reason", "").strip()
    email = session.get("email")

    if not app_name or not reason:
        return "Invalid report data"

    if already_reported(email, app_name):
        return "You already reported this app"

    df_reports.loc[len(df_reports)] = [email, app_name, reason]
    df_reports.to_csv(REPORT_FILE, index=False)

    return "Report submitted successfully"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

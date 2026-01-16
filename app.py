from flask import Flask, render_template, request, redirect, session
from google_play_scraper import app as playstore_app, reviews,search
from google_play_scraper.exceptions import NotFoundError
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
    if df_reports.empty:
        return False

    match = df_reports[
        (df_reports["email"] == email) &
        (df_reports["app_name"].str.lower() == app_name.lower())
    ]
    return not match.empty
def get_report_count(app_name):
    if df_reports.empty:
        return 0

    return len(
        df_reports[df_reports["app_name"].str.lower() == app_name.lower()]
    )


# ---------------- CORE HELPERS ----------------
def find_nbfc_by_app_id(app_id, app_title=""):
    app_id = str(app_id).lower()
    for _, row in df_nbfc.iterrows():
        if str(row["app_id"]).lower() == app_id:
            return True, row["nbfc_name"], row["type"]
    return False, None, None

def is_loan_app(title):
    return any(k in title.lower() for k in ["loan", "credit", "emi", "finance"])

# ---------------- REAL REVIEW ANALYSIS ----------------
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
    summary = (
        f"Based on {total} recent user reviews: "
        f"{positive} positive, {negative} negative complaints detected."
    )

    return {
        "sentiment": sentiment,
        "summary": summary,
        "negative_ratio": negative/total,
        "total": total
    }

# ---------------- PERMISSION RISK ----------------
def permission_risk_analysis_by_reviews(app_id, max_reviews=100):
    try:
        result, _ = reviews(app_id, lang="en", country="in", count=max_reviews)
    except:
        return "High Risk"

    keywords = ["permission", "privacy", "sms", "contacts", "location", "camera"]
    mentions = sum(
        any(k in r.get("content", "").lower() for k in keywords)
        for r in result
    )
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

        user = df_users[
            (df_users["email"] == email) &
            (df_users["password"] == password)
        ]
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

def resolve_app_id(user_input):
    """
    Resolves app_id using:
    1. NBFC mapping (playstore_name)
    2. Direct app_id
    3. Play Store search
    """

    user_input = user_input.strip().lower()

    # 1️⃣ Try NBFC mapping by playstore_name
    for _, row in df_nbfc.iterrows():
        if user_input == str(row["playstore_name"]).lower():
            return row["app_id"]

    # 2️⃣ Try direct app_id
    try:
        playstore_app(user_input)
        return user_input
    except:
        pass

    # 3️⃣ Fallback to Play Store search
    try:
        results = search(user_input, lang="en", country="in")
        if results:
            return results[0]["appId"]
    except:
        pass

    return None

@app.route("/predict", methods=["POST"])
def predict():
    if not is_logged_in():
        return redirect("/login")

    user_input = request.form.get("app_name")
    email = session["email"]

    resolved_app_id = resolve_app_id(user_input)

    if not resolved_app_id:
        return render_template(
            "result.html",
            name=user_input,
            rating="N/A",
            installs="N/A",
            nbfc_registered="No",
            sentiment="Negative",
            review_summary="App not found on Play Store.",
            permission_risk="High Risk",
            status="Suspicious",
            reason="App does not exist on Google Play Store."
        )

    details = playstore_app(resolved_app_id)
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

    if review_data["total"] == 0:
        status = "Caution"
        reason = "No user reviews available. This increases risk."

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

    if already_reported(email, app_title):
        reason += " ⚠️ Reported earlier by users."

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

    # 🔒 prevent duplicate reports by same user for same app
    # ---------------- USER REPORT COUNT ----------------
    report_count = get_report_count(app_name)

# Keep existing info
    if already_reported(email, app_name):
            reason += " ⚠️ Reported earlier by users."

# ---------------- USER REPORT BASED OVERRIDE ----------------
    if report_count >= 10:
     status = "Risky"
     reason = (
        f"This app has been reported by {report_count} users on LoanShield. "
        "Multiple scam reports indicate high risk."
    )

    elif report_count >= 5 and status == "Safe":
      status = "Caution"
      reason += (
        f" ⚠️ This app has been reported by {report_count} users on LoanShield."
    )

    # ✅ save report
    df_reports.loc[len(df_reports)] = [email, app_name, reason]
    df_reports.to_csv(REPORT_FILE, index=False)

    return "Report submitted successfully"

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

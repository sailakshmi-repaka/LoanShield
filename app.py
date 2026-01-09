from flask import Flask, render_template, request
from google_play_scraper import app as playstore_app, reviews
import pandas as pd
import os

app = Flask(__name__)

# ---------------- FILES ----------------
NBFC_FILE = "nbfc_playstore_mapping.csv"
REPORT_FILE = "reported_apps.csv"

# ---------------- LOAD NBFC DATA ----------------
if os.path.exists(NBFC_FILE):
    df_nbfc = pd.read_csv(NBFC_FILE)
    df_nbfc.columns = df_nbfc.columns.str.strip().str.lower()
else:
    df_nbfc = pd.DataFrame(columns=["nbfc_name", "playstore_name", "app_id", "type"])

# ---------------- LOAD USER REPORTS ----------------
if os.path.exists(REPORT_FILE):
    df_reports = pd.read_csv(REPORT_FILE)
    df_reports.columns = df_reports.columns.str.strip().str.lower()
else:
    df_reports = pd.DataFrame(columns=["app_name", "reason"])


# ---------------- HELPER FUNCTIONS ----------------

def find_nbfc_by_app_id(app_id, app_title=""):
    app_id = str(app_id).strip().lower()
    app_title = str(app_title).lower()

    for _, row in df_nbfc.iterrows():
        csv_app_id = str(row["app_id"]).strip().lower()
        csv_title = str(row["playstore_name"]).lower()

        if csv_app_id == app_id:
            return True, row["nbfc_name"], row["type"]

        if csv_title and csv_title in app_title:
            return True, row["nbfc_name"], row["type"]

    return False, None, None


def is_loan_app(title):
    keywords = ["loan", "credit", "emi", "lending", "finance"]
    return any(k in title.lower() for k in keywords)


def review_sentiment(rating, review_count):
    if rating == "N/A":
        return "Unavailable"
    if rating >= 4.2 and review_count >= 5000:
        return "Mostly Positive"
    elif rating >= 3.6:
        return "Mixed"
    else:
        return "Mostly Negative"


def permission_risk_analysis_by_reviews(app_id, max_reviews=150):
    try:
        result, _ = reviews(
            app_id,
            lang="en",
            country="in",
            count=max_reviews
        )
    except Exception:
        return "Unavailable"

    keywords = [
        "permission", "privacy", "contacts", "sms",
        "location", "camera", "data misuse", "scam"
    ]

    mentions = 0
    total = len(result)

    for r in result:
        text = r.get("content", "").lower()
        if any(k in text for k in keywords):
            mentions += 1

    if total == 0:
        return "No review data available"

    ratio = mentions / total

    if ratio > 0.1:
        return "High Risk – Users report privacy/permission issues"
    elif ratio > 0.03:
        return "Medium Risk – Some users report permission concerns"
    else:
        return "No high-risk permission issues reported"


def get_user_report(app_title):
    matches = df_reports[df_reports["app_name"].str.lower() == app_title.lower()]
    if not matches.empty:
        return matches.iloc[0]["reason"]
    return None


# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/predict", methods=["POST"])
def predict():
    user_input = request.form.get("app_name")

    if not user_input:
        return render_template(
            "result.html",
            status="Error",
            reason="No application name or ID provided."
        )

    # Defaults
    app_title = user_input
    app_id = user_input
    rating = "N/A"
    installs = "N/A"
    review_count = 0
    sentiment = "Unavailable"
    permission_risk = "Unavailable"
    playstore_status = "Unavailable"

    # ---------------- PLAY STORE FETCH ----------------
    try:
        details = playstore_app(user_input)

        app_title = details.get("title", user_input)
        app_id = details.get("appId", user_input)
        rating = details.get("score", "N/A")
        installs = details.get("installs", "N/A")
        review_count = details.get("reviews", 0)

        sentiment = review_sentiment(rating, review_count)
        permission_risk = permission_risk_analysis_by_reviews(app_id)
        playstore_status = "Available"

    except Exception:
        pass

    # ---------------- NBFC CHECK ----------------
    nbfc_registered, nbfc_name, nbfc_type = find_nbfc_by_app_id(app_id, app_title)

    # ---------------- USER REPORT CHECK ----------------
    reported_reason = get_user_report(app_title)
    caution_note = ""
    if reported_reason:
        caution_note = (
            f" ⚠️ This app has been reported by users for the following reason: "
            f"{reported_reason}. Please proceed with caution."
        )

    # ---------------- FINAL DECISION ----------------

    if not is_loan_app(app_title):
        status = "Not a Loan App"
        reason = "This application does not provide loan or credit-related services."

    elif not nbfc_registered:
        status = "Suspicious"
        reason = (
            "This application provides loan-related services but is not associated "
            "with any registered NBFC or disclosed NBFC partner."
        ) + caution_note

    else:
        if (
            sentiment == "Mostly Negative"
            or "Medium Risk" in permission_risk
            or "High Risk" in permission_risk
        ):
            status = "Caution"
            reason = (
                "This loan app is associated with a registered NBFC, but user reviews "
                "indicate negative experiences or privacy concerns."
            ) + caution_note
        else:
            status = "Safe"
            reason = (
                "Registered NBFC with strong ratings, high installs, "
                "and no major risk indicators in user reviews."
            ) + caution_note

    return render_template(
        "result.html",
        name=app_title,
        rating=rating,
        installs=installs,
        nbfc_registered="Yes" if nbfc_registered else "No",
        sentiment=sentiment,
        permission_risk=permission_risk,
        playstore_status=playstore_status,
        status=status,
        reason=reason
    )


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)

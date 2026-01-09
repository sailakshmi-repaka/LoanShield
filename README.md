
# 🛡️ LoanShield – Fake Loan App Detection System

LoanShield is a **web-based application** designed to help users identify **safe, suspicious, or potentially fake loan applications** by analyzing **Google Play Store data, user reviews, permission-related complaints, and NBFC verification**.

This project aims to raise awareness about fraudulent digital lending apps and promote **safe financial practices**.

## 🚀 Features

* 🔍 **Scan Loan Apps** using App Name or App ID
* ⭐ Fetches **Play Store data**:

  * Rating
  * Installs
  * Reviews count
* 🏦 **NBFC Verification**

  * Checks against a verified NBFC dataset
* 📝 **Review Sentiment Analysis**

  * Mostly Positive / Mixed / Mostly Negative
* 🔐 **Permission Risk Detection**

  * Detects complaints related to contacts, SMS, privacy, etc. from user reviews
* ⚠️ **Risk Classification**

  * Safe
  * Caution
  * Suspicious
* 📢 **Report Fake Loan App**

  * Users can report suspicious apps
* 🎨 Clean and user-friendly UI


## 🧠 How It Works

1. User enters an **App Name or Play Store App ID**
2. System fetches:

   * App details from **Google Play Store**
   * User reviews
3. Reviews are analyzed for:

   * Sentiment
   * Permission-related complaints
4. App is verified against **NBFC registry**
5. Final status is generated:

   * **Safe**
   * **Caution**
   * **Suspicious**

## 🛠️ Technologies Used

### Frontend

* HTML5
* CSS3
* JavaScript

### Backend

* Python
* Flask

### Libraries & Tools

* `google-play-scraper`
* `pandas`
* `Flask`
* Git & GitHub


## 📁 Project Structure

LoanShield/
│
├── app.py
├── nbfc_playstore_mapping.csv
├── requirements.txt
│
├── templates/
│   ├── index.html
│   ├── result.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   ├── js/
│   │   └── script.js
│
└── README.md


## ⚙️ Installation & Setup

### 1️⃣ Clone the Repository
### in terminal
git clone https://github.com/sailakshmi-repaka/LoanShield.git
cd LoanShield

### 2️⃣ Create Virtual Environment (Optional but Recommended)

python -m venv venv
venv\Scripts\activate

### 3️⃣ Install Dependencies

pip install -r requirements.txt

### 4️⃣ Run the Application

python app.py


Open browser and visit:

 http://127.0.0.1:5000


## 🧪 Sample App IDs for Testing

| App Name     | App ID                  |
| ------------ | ----------------------- |
| Tata Capital | com.snapwork.tcl        |
| KreditBee    | com.kreditbee.android   |
| MoneyTap     | com.mycash.moneytap.app |
| CASHe        | co.tslc.cashe.android   |
| mPokket      | com.mpokket.app         |


## ⚠️ Disclaimer

* This project is intended for **educational and awareness purposes only**
* Risk classification is based on:

  * Publicly available Play Store data
  * User reviews
  * NBFC registry references
* Final decisions should always be made by users with proper due diligence.

## 👩‍💻 Author

**Sai Lakshmi Repaka**
B.Tech – Computer Science Engineering
Final Year Project

🔗 GitHub: [https://github.com/sailakshmi-repaka](https://github.com/sailakshmi-repaka)


## ⭐ Acknowledgements

* Google Play Store
* RBI & NBFC public registries
* Open-source Python community



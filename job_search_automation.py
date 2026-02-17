#!/usr/bin/env python3
"""
Reliable Data Engineer Job Alert Automation
- Always sends email
- Handles scraping failures safely
- Works in GitHub Actions
"""

import os
import smtplib
import pandas as pd
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from bs4 import BeautifulSoup
import re
import traceback


class JobAlertAutomation:
    def __init__(self):
        self.jobs = []
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
        }

    # -------------------------
    # SCRAPE NAUKRI (SAFE MODE)
    # -------------------------
    def scrape_naukri_jobs(self):
        print("🔍 Attempting Naukri scrape...")

        url = "https://www.naukri.com/jobs-search?k=data%20engineer&exp=0,2"

        try:
            response = requests.get(url, headers=self.headers, timeout=10)

            if response.status_code != 200:
                print(f"⚠️ Naukri returned status {response.status_code}")
                return

            soup = BeautifulSoup(response.text, "lxml")

            job_cards = soup.find_all("a", href=True)

            for link in job_cards[:20]:
                text = link.get_text().lower()
                if "data engineer" in text:
                    self.jobs.append({
                        "Job Title": link.get_text().strip(),
                        "Company": "Naukri Listing",
                        "Location": "India",
                        "Salary": "Not specified",
                        "Experience": "0-2 years",
                        "Source": "Naukri",
                        "Posted Date": datetime.now().strftime("%Y-%m-%d"),
                        "Job URL": link["href"]
                    })

            print(f"✅ Naukri jobs scraped: {len(self.jobs)}")

        except Exception as e:
            print("⚠️ Naukri scraping failed")
            print(traceback.format_exc())

    # -------------------------
    # REMOVE DUPLICATES
    # -------------------------
    def remove_duplicates(self):
        if not self.jobs:
            return

        df = pd.DataFrame(self.jobs)
        df.drop_duplicates(subset=["Job Title", "Job URL"], inplace=True)
        self.jobs = df.to_dict("records")

    # -------------------------
    # GENERATE EXCEL
    # -------------------------
    def generate_excel_report(self):
        output_file = "job_alerts.xlsx"

        if not self.jobs:
            print("⚠️ No jobs found. Creating empty report.")

            df = pd.DataFrame([{
                "Message": "No Data Engineer jobs found today."
            }])
        else:
            df = pd.DataFrame(self.jobs)

        df.to_excel(output_file, index=False)

        print("📊 Excel file created.")
        return output_file

    # -------------------------
    # SEND EMAIL
    # -------------------------
    def send_email_alert(self, excel_file):
        sender = os.getenv("SENDER_EMAIL")
        password = os.getenv("EMAIL_PASSWORD")
        recipient = os.getenv("RECIPIENT_EMAIL")

        if not sender or not password or not recipient:
            print("❌ Missing email environment variables.")
            return

        try:
            print("📧 Sending email...")

            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Daily Data Engineer Jobs - {datetime.now().strftime('%d %B %Y')}"

            body = f"""
Hello,

This is your automated Data Engineer job report.

Total jobs found: {len(self.jobs)}

Generated at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC
"""

            msg.attach(MIMEText(body, "plain"))

            with open(excel_file, "rb") as f:
                part = MIMEBase("application", "octet-stream"

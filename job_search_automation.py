#!/usr/bin/env python3

import os
import smtplib
import pandas as pd
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
import xml.etree.ElementTree as ET
import re


class JobAlertAutomation:

    def __init__(self):
        self.jobs = []

    # ----------------------------------
    # INDEED RSS (ALL INDIA)
    # ----------------------------------
    def scrape_indeed_rss(self):
        print("🔍 Fetching Data Engineer jobs from Indeed RSS...")

        rss_url = "https://in.indeed.com/rss?q=data+engineer+0+2+years&l=India"

        try:
            response = requests.get(rss_url, timeout=15)
            root = ET.fromstring(response.content)

            for item in root.findall(".//item"):
                title = item.find("title").text if item.find("title") is not None else ""
                link = item.find("link").text if item.find("link") is not None else ""
                description = item.find("description").text if item.find("description") is not None else ""
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""

                # Must contain Data Engineer in title
                if "data engineer" not in title.lower():
                    continue

                # Check experience <= 2 years
                if not self.is_valid_experience(description):
                    continue

                self.jobs.append({
                    "Job Title": title.strip(),
                    "Company": "Check Indeed Posting",
                    "Location": "India",
                    "Experience": "≤ 2 years",
                    "Source": "Indeed RSS",
                    "Posted Date": pub_date,
                    "Job URL": link
                })

            print(f"✅ Jobs collected: {len(self.jobs)}")

        except Exception as e:
            print("⚠️ RSS fetch failed:", e)

    # ----------------------------------
    # EXPERIENCE FILTER (<=2 YOE)
    # ----------------------------------
    def is_valid_experience(self, text):
        text = text.lower()

        if "fresher" in text or "entry level" in text:
            return True

        numbers = re.findall(r'\d+', text)

        if numbers:
            max_exp = max([int(n) for n in numbers])
            return max_exp <= 2

        # If no experience mentioned, allow
        return True

    # ----------------------------------
    # REMOVE DUPLICATES
    # ----------------------------------
    def remove_duplicates(self):
        if not self.jobs:
            return

        df = pd.DataFrame(self.jobs)
        df.drop_duplicates(subset=["Job Title", "Job URL"], inplace=True)
        self.jobs = df.to_dict("records")

    # ----------------------------------
    # GENERATE EXCEL
    # ----------------------------------
    def generate_excel(self):
        file_name = "job_alerts.xlsx"

        if not self.jobs:
            df = pd.DataFrame([{
                "Message": "No Data Engineer (≤2 YOE) jobs found today."
            }])
        else:
            df = pd.DataFrame(self.jobs)

        df.to_excel(file_name, index=False)
        return file_name

    # ----------------------------------
    # SEND EMAIL
    # ----------------------------------
    def send_email(self, file_name):
        sender = os.getenv("SENDER_EMAIL")
        password = os.getenv("EMAIL_PASSWORD")
        recipient = os.getenv("RECIPIENT_EMAIL")

        if not sender or not password or not recipient:
            print("❌ Email secrets missing.")
            return

        try:
            msg = MIMEMultipart()
            msg["From"] = sender
            msg["To"] = recipient
            msg["Subject"] = f"Daily Data Engineer Jobs (≤2 YOE) - {datetime.now().strftime('%d %B %Y')}"

            body = f"""
Hello,

Total Data Engineer jobs (≤2 YOE) found today: {len(self.jobs)}

Please check the attached Excel file.

Generated automatically via GitHub Actions.
"""

            msg.attach(MIMEText(body, "plain"))

            with open(file_name, "rb") as f:
                part = MIMEBase("application", "octet-stream")
                part.set_payload(f.read())
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={file_name}")
                msg.attach(part)

            server = smtplib.SMTP("smtp.gmail.com", 587)
            server.starttls()
            server.login(sender, password)
            server.send_message(msg)
            server.quit()

            print("✅ Email sent successfully.")

        except Exception as e:
            print("❌ Email failed:", e)

    # ----------------------------------
    # RUN
    # ----------------------------------
    def run(self):
        print("🚀 Job Automation Started")

        self.scrape_indeed_rss()
        self.remove_duplicates()

        file_name = self.generate_excel()
        self.send_email(file_name)

        print("✅ Automation Completed")


if __name__ == "__main__":
    JobAlertAutomation().run()

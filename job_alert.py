#!/usr/bin/env python3
"""
Data Engineer Job Search Automation
Scrapes jobs from Naukri, company portals
Generates Excel report and sends daily email alerts
"""

import os
import smtplib
import pandas as pd
import requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from bs4 import BeautifulSoup
import re
import time


class JobAlertAutomation:
    def __init__(self):
        self.jobs = []
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
    def scrape_naukri_jobs(self):
        """Scrape Data Engineer jobs from Naukri.com"""
        try:
            print("🔍 Scraping Naukri.com...")
            url = "https://www.naukri.com/jobs-search?k=data%20engineer&exp=0,2&count=100"
            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for card in soup.find_all('div', class_='srp-jobtuple-wrapper')[:25]:
                try:
                    title_elem = card.find('a', class_='title')
                    company_elem = card.find('a', class_='comp-name')
                    location_elem = card.find('span', class_='location-wrapper')
                    salary_elem = card.find('span', class_='sal-wrap')
                    exp_elem = card.find('span', class_='exp-wrap')
                    
                    if not all([title_elem, company_elem, location_elem]):
                        continue
                    
                    title = title_elem.text.strip()
                    company = company_elem.text.strip()
                    location = location_elem.text.strip()
                    salary = salary_elem.text.strip() if salary_elem else 'Not Specified'
                    experience = exp_elem.text.strip() if exp_elem else 'Not Specified'
                    
                    url_href = title_elem.get('href', '')
                    job_url = f"https://www.naukri.com{url_href}" if url_href.startswith('/') else url_href
                    
                    if self.is_valid_experience(experience):
                        self.jobs.append({
                            'Job Title': title,
                            'Company': company,
                            'Location': location,
                            'Salary': salary,
                            'Experience': experience,
                            'Source': 'Naukri.com',
                            'Job URL': job_url,
                            'Posted Date': datetime.now().strftime('%Y-%m-%d')
                        })
                except Exception as e:
                    continue
                    
        except Exception as e:
            print(f"⚠️ Error scraping Naukri: {e}")
    
    def scrape_company_portals(self):
        """Scrape jobs from major tech company career portals"""
        try:
            print("🔍 Scraping Company Career Portals...")
            
            companies = {
                'Cognizant': 'https://careers.cognizant.com/search-jobs?keywords=data%20engineer&location=India',
                'TCS': 'https://www.tcs.com/careers',
                'Infosys': 'https://www.infosys.com/careers',
            }
            
            for company, portal_url in companies.items():
                try:
                    response = requests.get(portal_url, headers=self.headers, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    
                    job_links = soup.find_all('a', href=re.compile(r'data.*engineer|engineer.*data', re.IGNORECASE))
                    
                    for link in job_links[:5]:
                        href = link.get('href', '')
                        if href and ('http' in href or href.startswith('/')):
                            self.jobs.append({
                                'Job Title': 'Data Engineer',
                                'Company': company,
                                'Location': 'India',
                                'Salary': 'Check Portal',
                                'Experience': '0-2 years',
                                'Source': f'{company} Portal',
                                'Job URL': href,
                                'Posted Date': datetime.now().strftime('%Y-%m-%d')
                            })
                except Exception as e:
                    print(f"⚠️ Could not scrape {company}: {e}")
                    
        except Exception as e:
            print(f"⚠️ Error in company portal scraping: {e}")
    
    def is_valid_experience(self, exp_string):
        """Check if experience requirement is <= 2 years"""
        if not exp_string or exp_string == 'Not Specified':
            return True
        
        exp_lower = str(exp_string).lower()
        
        if 'fresher' in exp_lower or 'entry' in exp_lower:
            return True
        
        numbers = re.findall(r'\d+', exp_lower)
        if numbers:
            max_exp = max([int(n) for n in numbers])
            return max_exp <= 2
        
        return True
    
    def remove_duplicates(self):
        """Remove duplicate job listings"""
        if not self.jobs:
            return
            
        df = pd.DataFrame(self.jobs)
        df = df.drop_duplicates(subset=['Company', 'Job Title', 'Location'], keep='first')
        self.jobs = df.to_dict('records')
        print(f"✅ Deduplicated. Total unique jobs: {len(self.jobs)}")
    
    def generate_excel_report(self, output_file='job_alerts.xlsx'):
        """Generate Excel report with formatting"""
        if not self.jobs:
            print("⚠️ No jobs found today.")
            return None
        
        df = pd.DataFrame(self.jobs)
        
        column_order = ['Job Title', 'Company', 'Location', 'Salary', 'Experience', 
                       'Source', 'Posted Date', 'Job URL']
        df = df[[col for col in column_order if col in df.columns]]
        
        try:
            with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Job Alerts', index=False)
                
                workbook = writer.book
                worksheet = writer.sheets['Job Alerts']
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
            
            print(f"✅ Excel report generated: {output_file}")
            return output_file
        except Exception as e:
            print(f"❌ Error creating Excel: {e}")
            return None
    
    def send_email_alert(self, excel_file):
        """Send email with Excel attachment"""
        sender_email = os.getenv('SENDER_EMAIL')
        email_password = os.getenv('EMAIL_PASSWORD')
        recipient_email = os.getenv('RECIPIENT_EMAIL')
        
        if not sender_email or not email_password or not recipient_email:
            print("⚠️ Email credentials not configured")
            print("Please set: SENDER_EMAIL, EMAIL_PASSWORD, RECIPIENT_EMAIL")
            return False
        
        if not os.path.exists(excel_file):
            print(f"❌ Excel file not found: {excel_file}")
            return False
        
        try:
            print("📧 Sending email alert...")
            
            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = recipient_email
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"🎯 Data Engineer Job Alerts (≤2 YOE) - {datetime.now().strftime('%d %B %Y')}"
            
            body = f"""Hello Sri Charan,

Here are {len(self.jobs)} Data Engineer job opportunities matching your profile (≤2 years experience):

📊 SUMMARY:
- Total Jobs Found: {len(self.jobs)}
- Filtered For: Data Engineer roles with ≤2 YOE requirement
- Location Focus: Primarily India-based positions

WHAT'S INCLUDED:
✓ Job Title & Company Name
✓ Location & Salary Range
✓ Experience Requirements
✓ Direct Application Links

📋 HOW TO USE:
1. Open the attached Excel file
2. Review job titles that match your interest
3. Click the Job URL to apply directly on company portal or LinkedIn
4. Track your applications

YOUR PROFILE STRENGTHS:
- 2 YOE as Data Engineer
- AWS (Glue, Lambda, S3, Athena) expertise
- PySpark & Databricks experience
- ETL & Data Lake architecture knowledge
- Azure services (Data Factory, Synapse)
- Real-time & batch data pipeline expertise

Good luck with your applications! You've got strong experience for these roles. 🚀

---
Generated: {datetime.now().strftime('%d-%m-%Y at %H:%M IST')}
Automated Job Alert System"""
            
            msg.attach(MIMEText(body, 'plain'))
            
            with open(excel_file, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={excel_file}')
                msg.attach(part)
            
            print("📧 Connecting to Gmail SMTP...")
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender_email, email_password)
            server.send_message(msg)
            server.quit()
            
            print(f"✅ Email sent successfully to {recipient_email}!")
            return True
            
        except smtplib.SMTPAuthenticationError:
            print("❌ Gmail authentication failed!")
            print("Check: EMAIL_PASSWORD is correct 16-char app password")
            return False
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return False
    
    def run(self):
        """Execute the complete automation workflow"""
        print("\n" + "="*70)
        print("🚀 DATA ENGINEER JOB SEARCH AUTOMATION")
        print(f"⏰ Started at: {datetime.now().strftime('%d-%m-%Y %H:%M:%S IST')}")
        print("="*70 + "\n")
        
        start_time = time.time()
        
        self.scrape_naukri_jobs()
        time.sleep(2)
        
        self.scrape_company_portals()
        time.sleep(2)
        
        self.remove_duplicates()
        
        excel_file = self.generate_excel_report()
        
        if excel_file:
            self.send_email_alert(excel_file)
        
        elapsed_time = time.time() - start_time
        
        print("\n" + "="*70)
        print(f"✅ Automation completed in {elapsed_time:.2f} seconds")
        print(f"📈 Total unique jobs scraped: {len(self.jobs)}")
        print("="*70 + "\n")


if __name__ == "__main__":
    automation = JobAlertAutomation()
    automation.run()

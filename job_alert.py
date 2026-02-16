#!/usr/bin/env python3
import os, smtplib, pandas as pd, requests
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email.utils import formatdate
from email import encoders
from bs4 import BeautifulSoup
import re, time

class JobAlertAutomation:
    def __init__(self):
        self.jobs = []
        self.headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        
    def scrape_naukri_jobs(self):
        try:
            print("🔍 Scraping Naukri.com...")
            url = "https://www.naukri.com/jobs-search?k=data%20engineer&exp=0,2&count=100"
            response = requests.get(url, headers=self.headers, timeout=15)
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for card in soup.find_all('div', class_='srp-jobtuple-wrapper')[:20]:
                try:
                    title = card.find('a', class_='title').text.strip()
                    company = card.find('a', class_='comp-name').text.strip()
                    location = card.find('span', class_='location-wrapper').text.strip()
                    salary = card.find('span', class_='sal-wrap').text.strip()
                    url_elem = card.find('a', class_='title')
                    job_url = f"https://www.naukri.com{url_elem['href']}"
                    experience = card.find('span', class_='exp-wrap').text.strip()
                    
                    if self.is_valid_experience(experience):
                        self.jobs.append({
                            'Job Title': title, 'Company': company, 'Location': location,
                            'Salary': salary, 'Experience': experience, 'Source': 'Naukri',
                            'Job URL': job_url, 'Posted Date': datetime.now().strftime('%Y-%m-%d')
                        })
                except: pass
        except Exception as e:
            print(f"⚠️ Error: {e}")
    
    def scrape_company_portals(self):
        try:
            print("🔍 Scraping Company Portals...")
            companies = {
                'Cognizant': 'https://careers.cognizant.com/search-jobs?keywords=data%20engineer',
                'TCS': 'https://www.tcs.com/careers',
            }
            
            for company, url in companies.items():
                try:
                    response = requests.get(url, headers=self.headers, timeout=15)
                    soup = BeautifulSoup(response.content, 'html.parser')
                    links = soup.find_all('a', href=re.compile(r'data.*engineer', re.I))
                    
                    for link in links[:5]:
                        self.jobs.append({
                            'Job Title': 'Data Engineer', 'Company': company,
                            'Location': 'India', 'Salary': 'Check Portal',
                            'Experience': '0-2 yrs', 'Source': company,
                            'Job URL': link.get('href', 'N/A'),
                            'Posted Date': datetime.now().strftime('%Y-%m-%d')
                        })
                except: pass
        except: pass
    
    def is_valid_experience(self, exp_str):
        if not exp_str or 'fresher' in str(exp_str).lower(): return True
        numbers = re.findall(r'\d+', str(exp_str))
        return max([int(n) for n in numbers]) <= 2 if numbers else True
    
    def remove_duplicates(self):
        if self.jobs:
            df = pd.DataFrame(self.jobs)
            df = df.drop_duplicates(subset=['Company', 'Job Title', 'Location'], keep='first')
            self.jobs = df.to_dict('records')
            print(f"✅ {len(self.jobs)} unique jobs found")
    
    def generate_excel_report(self, file='job_alerts.xlsx'):
        if not self.jobs: return None
        df = pd.DataFrame(self.jobs)
        cols = ['Job Title', 'Company', 'Location', 'Salary', 'Experience', 'Source', 'Posted Date', 'Job URL']
        df = df[[c for c in cols if c in df.columns]]
        
        with pd.ExcelWriter(file, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Jobs', index=False)
            worksheet = writer.sheets['Jobs']
            for column in worksheet.columns:
                max_len = max(len(str(cell.value)) for cell in column)
                worksheet.column_dimensions[column[0].column_letter].width = min(max_len + 2, 50)
        print(f"✅ Excel saved: {file}")
        return file
    
    def send_email(self, excel_file):
        sender = os.getenv('SENDER_EMAIL')
        pwd = os.getenv('EMAIL_PASSWORD')
        recipient = os.getenv('RECIPIENT_EMAIL', 'sricharandasika@gmail.com')
        
        if not sender or not pwd: return False
        
        try:
            msg = MIMEMultipart()
            msg['From'], msg['To'] = sender, recipient
            msg['Date'] = formatdate(localtime=True)
            msg['Subject'] = f"🎯 Data Engineer Jobs (≤2 YOE) - {datetime.now().strftime('%d %B %Y')}"
            
            body = f"Here are {len(self.jobs)} Data Engineer jobs for you!\n\nAttached: Complete list with links."
            msg.attach(MIMEText(body, 'plain'))
            
            with open(excel_file, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition', f'attachment; filename={excel_file}')
                msg.attach(part)
            
            server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
            server.login(sender, pwd)
            server.send_message(msg)
            server.quit()
            print("✅ Email sent!")
            return True
        except Exception as e:
            print(f"❌ Email error: {e}")
            return False
    
    def run(self):
        print("\n🚀 Starting Job Alert Automation...\n")
        self.scrape_naukri_jobs()
        time.sleep(2)
        self.scrape_company_portals()
        self.remove_duplicates()
        excel = self.generate_excel_report()
        if excel and os.getenv('SENDER_EMAIL'):
            self.send_email(excel)
        print(f"\n✅ Done! {len(self.jobs)} jobs found\n")

if __name__ == "__main__":
    JobAlertAutomation().run()

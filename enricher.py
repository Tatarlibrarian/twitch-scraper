import os, requests, csv, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

GOOGLE_KEY = os.environ.get('GOOGLE_SEARCH_KEY')
GOOGLE_CX = os.environ.get('GOOGLE_SEARCH_CX')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')
CSV_FILE = "leads.csv"

def find_contact(name):
    """三层搜索逻辑：简介扫描（模拟）+ 谷歌保底"""
    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={name}+business+email+contact+Twitter&num=3"
    try:
        items = requests.get(url).json().get('items', [])
        text = " ".join([i.get('snippet', '') for i in items])
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text) #
        if emails: return f"📧 Email: {emails[0]}"
        twitter = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', text) #
        if twitter: return f"🐦 Twitter: @{twitter.group(1)}"
    except: pass
    return "⚠️ 未发现公开联系方式"

def enrich_leads():
    updated_rows = []
    report = []
    with open(CSV_FILE, "r", encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    for row in reader:
        if row["Status"] == "New":
            print(f"正在调查: {row['Name']}")
            contact = find_contact(row['Name']) #
            row["Contact"] = contact
            row["Status"] = "Enriched"
            report.append(f"👤 {row['Name']} ({row['Game']})\n   平台: {row['Platform']}\n   联系方式: {contact}\n   链接: {row['Link']}\n")
        updated_rows.append(row)

    if report:
        with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reader[0].keys())
            writer.writeheader()
            writer.writerows(updated_rows)
        send_mail("\n\n".join(report))

def send_mail(body):
    msg = MIMEMultipart()
    msg['Subject'] = "深度线索报告：博主联系方式"
    msg['From'] = msg['To'] = EMAIL_ADDR
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls(); s.login(EMAIL_ADDR, EMAIL_PASS); s.send_message(msg)

if __name__ == "__main__":
    enrich_leads()

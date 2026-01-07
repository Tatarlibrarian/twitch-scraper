import os, requests, csv, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# 配置读取
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
GOOGLE_KEY = os.environ.get('GOOGLE_SEARCH_KEY')
GOOGLE_CX = os.environ.get('GOOGLE_SEARCH_CX')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')
CSV_FILE = "leads.csv"

def get_twitch_bio(user_id):
    """直接从 Twitch API 获取简介"""
    auth = requests.post("https://id.twitch.tv/oauth2/token", data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    # 去掉 ID 中的 'tw_' 前缀
    clean_id = user_id.replace('tw_', '')
    res = requests.get(f"https://api.twitch.tv/helix/users?id={clean_id}", headers=headers).json()
    return res['data'][0].get('description', '') if res.get('data') else ""

def get_youtube_bio(channel_id):
    """直接从 YouTube API 获取简介"""
    clean_id = channel_id.replace('yt_', '')
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={clean_id}&key={YT_API_KEY}"
    res = requests.get(url).json()
    return res['items'][0]['snippet'].get('description', '') if res.get('items') else ""

def extract_email(text):
    """从文本中提取邮箱"""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return emails[0] if emails else None

def find_contact_via_google(name):
    """保底：通过谷歌搜索提取摘要"""
    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={name}+business+email+contact&num=3"
    try:
        items = requests.get(url).json().get('items', [])
        all_text = " ".join([i.get('snippet', '') for i in items])
        return extract_email(all_text)
    except: return None

def enrich_leads():
    updated_rows = []
    report = []
    with open(CSV_FILE, "r", encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    for row in reader:
        if row["Status"] == "New":
            print(f"Investigating: {row['Name']}...")
            contact = None
            
            # 1. 优先尝试直接从简介中获取 (针对 MooseTaffy 这种情况)
            bio = ""
            if row["Platform"] == "Twitch": bio = get_twitch_bio(row["ID"])
            else: bio = get_youtube_bio(row["ID"])
            
            contact = extract_email(bio)
            if contact: contact = f"📧 Email (Found in Bio): {contact}"
            
            # 2. 如果简介里没有，再用 Google 搜索
            if not contact:
                search_email = find_contact_via_google(row['Name'])
                if search_email: contact = f"📧 Email (Found via Google): {search_email}"
            
            # 3. 最终结果记录
            final_contact = contact if contact else "⚠️ 未发现公开联系方式"
            row["Contact"] = final_contact
            row["Status"] = "Enriched"
            report.append(f"👤 {row['Name']} ({row['Game']})\n   联系方式: {final_contact}\n   链接: {row['Link']}\n")
        updated_rows.append(row)

    if report:
        with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=reader[0].keys())
            writer.writeheader()
            writer.writerows(updated_rows)
        send_mail("\n\n".join(report))

def send_mail(body):
    msg = MIMEMultipart()
    msg['Subject'] = "深度线索报告：已找齐博主联系方式"
    msg['From'] = msg['To'] = EMAIL_ADDR
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls(); s.login(EMAIL_ADDR, EMAIL_PASS); s.send_message(msg)

if __name__ == "__main__":
    enrich_leads()

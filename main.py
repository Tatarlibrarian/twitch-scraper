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
    clean_id = user_id.replace('tw_', '')
    try:
        res = requests.get(f"https://api.twitch.tv/helix/users?id={clean_id}", headers=headers).json()
        return res['data'][0].get('description', '') if res.get('data') else ""
    except: return ""

def get_youtube_bio(channel_id):
    """直接从 YouTube API 获取简介"""
    clean_id = channel_id.replace('yt_', '')
    url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={clean_id}&key={YT_API_KEY}"
    try:
        res = requests.get(url).json()
        return res['items'][0]['snippet'].get('description', '') if res.get('items') else ""
    except: return ""

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
        # 优先找邮箱
        email = extract_email(all_text)
        if email: return f"📧 Email (Found via Google): {email}"
        # 次选 Twitter
        twitter = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', all_text)
        if twitter: return f"🐦 Twitter: @{twitter.group(1)}"
    except: pass
    return None

def enrich_leads():
    updated_rows = []
    report = [] # 存储有联系方式的结果
    with open(CSV_FILE, "r", encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    for row in reader:
        if row["Status"] == "New":
            print(f"正在调查: {row['Name']}...")
            contact = None
            
            # 1. 优先尝试直接从简介中获取
            bio = get_twitch_bio(row["ID"]) if row["Platform"] == "Twitch" else get_youtube_bio(row["ID"])
            found_email = extract_email(bio)
            if found_email:
                contact = f"📧 Email (Found in Bio): {found_email}"
            
            # 2. 如果简介里没有，再用 Google 搜索
            if not contact:
                contact = find_contact_via_google(row['Name'])
            
            # 3. 记录结果
            row["Contact"] = contact if contact else "⚠️ 未发现公开联系方式"
            row["Status"] = "Enriched"
            
            # --- 关键改动：只有当 contact 不为 None 时才加入邮件列表 ---
            if contact:
                report.append(f"👤 {row['Name']} ({row['Game']})\n   联系方式: {contact}\n   链接: {row['Link']}")
        
        updated_rows.append(row)

    # 保存更新后的 CSV
    with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=reader[0].keys())
        writer.writeheader()
        writer.writerows(updated_rows)

    # 只有当发现有联系方式的博主时才发邮件
    if report:
        send_mail("\n\n" + "\n\n".join(report))
        print(f"调查完成，已向邮箱发送了 {len(report)} 条有效线索。")
    else:
        print("调查完成，但本次未发现任何公开联系方式。")

def send_mail(body):
    msg = MIMEMultipart()
    count = body.count('👤')
    msg['Subject'] = f"【深度线索】已找齐 {count} 位博主的有效联系方式"
    msg['From'] = msg['To'] = EMAIL_ADDR
    msg.attach(MIMEText(body, 'plain'))
    with smtplib.SMTP("smtp.gmail.com", 587) as s:
        s.starttls()
        s.login(EMAIL_ADDR, EMAIL_PASS)
        s.send_message(msg)

if __name__ == "__main__":
    enrich_leads()

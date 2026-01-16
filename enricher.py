import os, requests, csv, re, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# --- 1. 配置读取 (从 GitHub Secrets) ---
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
GOOGLE_KEY = os.environ.get('GOOGLE_SEARCH_KEY')
GOOGLE_CX = os.environ.get('GOOGLE_SEARCH_CX')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')
CSV_FILE = "leads.csv"

# --- 2. 挖掘配额控制 ---
MAX_LIMIT = 500  # 每次运行最多处理 50 个新博主，防止耗尽 Google 100次/天的免费配额

def get_twitch_bio(user_id):
    """直接从 Twitch API 获取博主最新的简介"""
    try:
        auth = requests.post("https://id.twitch.tv/oauth2/token", 
                             data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
        token = auth.get('access_token')
        headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
        clean_id = user_id.replace('tw_', '')
        res = requests.get(f"https://api.twitch.tv/helix/users?id={clean_id}", headers=headers).json()
        return res['data'][0].get('description', '') if res.get('data') else ""
    except: return ""

def get_youtube_bio(channel_id):
    """直接从 YouTube API 获取频道简介"""
    try:
        clean_id = channel_id.replace('yt_', '')
        url = f"https://www.googleapis.com/youtube/v3/channels?part=snippet&id={clean_id}&key={YT_API_KEY}"
        res = requests.get(url).json()
        return res['items'][0]['snippet'].get('description', '') if res.get('items') else ""
    except: return ""

def extract_email(text):
    """利用正则表达式从文本中提取邮箱"""
    emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', text)
    return emails[0] if emails else None

def find_contact_via_google(name):
    """保底方案：通过谷歌搜索提取线索"""
    url = f"https://www.googleapis.com/customsearch/v1?key={GOOGLE_KEY}&cx={GOOGLE_CX}&q={name}+business+email+contact&num=3"
    try:
        items = requests.get(url).json().get('items', [])
        all_text = " ".join([i.get('snippet', '') for i in items])
        # 优先提取邮箱
        email = extract_email(all_text)
        if email: return f"📧 Email (Via Google): {email}"
        # 次选提取 Twitter
        twitter = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', all_text)
        if twitter: return f"🐦 Twitter: @{twitter.group(1)}"
    except: pass
    return None

def enrich_leads():
    updated_rows = []
    report = []
    new_processed_count = 0
    
    if not os.path.exists(CSV_FILE):
        print("leads.csv 不存在，请先运行采集脚本。")
        return

    with open(CSV_FILE, "r", encoding='utf-8') as f:
        reader = list(csv.DictReader(f))
    
    for row in reader:
        # 只有状态为 New 且 未超过单次运行限额时才进行调查
        if row["Status"] == "New" and new_processed_count < MAX_LIMIT:
            print(f"[{new_processed_count+1}/{MAX_LIMIT}] 正在调查: {row['Name']}...")
            contact = None
            
            # 步骤 1: 优先扫描原生简介 (最准、不占搜索配额)
            bio = get_twitch_bio(row["ID"]) if row["Platform"] == "Twitch" else get_youtube_bio(row["ID"])
            found_email = extract_email(bio)
            if found_email:
                contact = f"📧 Email (Found in Bio): {found_email}"
            
            # 步骤 2: 简介里没有，再启用 Google 搜索
            if not contact:
                contact = find_contact_via_google(row['Name'])
            
            # 更新状态和联系方式
            row["Contact"] = contact if contact else "⚠️ 未发现公开联系方式"
            row["Status"] = "Enriched"
            new_processed_count += 1
            
            # 只有找到有效联系方式的才加入邮件报告
            if contact:
                report.append(f"👤 {row['Name']} ({row['Game']})\n   联系方式: {contact}\n   链接: {row['Link']}")
        
        updated_rows.append(row)

    # 将更新后的数据写回 CSV
    with open(CSV_FILE, "w", newline='', encoding='utf-8') as f:
        if updated_rows:
            writer = csv.DictWriter(f, fieldnames=updated_rows[0].keys())
            writer.writeheader()
            writer.writerows(updated_rows)

    # 发送报告
    if report:
        send_mail("\n\n" + "\n\n".join(report))
        print(f"成功！本次处理了 {new_processed_count} 个新目标，找到 {len(report)} 条有效联系方式。")
    else:
        print(f"本次调查了 {new_processed_count} 个博主，但未发现新的有效联系方式。")

def send_mail(body):
    msg = MIMEMultipart()
    count = body.count('👤')
    msg['Subject'] = f"【深度线索报告】已为您找齐 {count} 位博主的有效联系方式"
    msg['From'] = msg['To'] = EMAIL_ADDR
    msg.attach(MIMEText(body, 'plain'))
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as s:
            s.starttls()
            s.login(EMAIL_ADDR, EMAIL_PASS)
            s.send_message(msg)
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    enrich_leads()

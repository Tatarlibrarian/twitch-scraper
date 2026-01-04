import os, requests, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# 配置信息（从 GitHub Secrets 读取）
CLIENT_ID = os.environ.get('TWITCH_CLIENT_ID')
CLIENT_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')

def get_access_token():
    url = "https://id.twitch.tv/oauth2/token"
    data = {"client_id": CLIENT_ID, "client_secret": CLIENT_SECRET, "grant_type": "client_credentials"}
    return requests.post(url, data=data).json().get('access_token')

def get_streamers(token):
    url = "https://api.twitch.tv/helix/streams"
    headers = {"Client-ID": CLIENT_ID, "Authorization": f"Bearer {token}"}
    params = {"game_id": "32982", "language": "en", "first": 100} # GTA V
    
    qualified = []
    streams = requests.get(url, headers=headers, params=params).json().get('data', [])
    for s in streams:
        if 50 <= s['viewer_count'] <= 200:
            qualified.append(f"- 主播: {s['user_name']} | 人数: {s['viewer_count']} | 链接: https://www.twitch.tv/{s['user_login']}")
    return qualified

def send_mail(content):
    if not content: return
    msg = MIMEMultipart()
    msg['Subject'] = f"Twitch GTA 筛选报告 - {datetime.now().strftime('%Y-%m-%d')}"
    msg['From'], msg['To'] = EMAIL_ADDR, EMAIL_ADDR
    msg.attach(MIMEText("\n".join(content), 'plain'))
    
    with smtplib.SMTP("smtp.gmail.com", 587) as server:
        server.starttls()
        server.login(EMAIL_ADDR, EMAIL_PASS)
        server.send_message(msg)

if __name__ == "__main__":
    token = get_access_token()
    if token:
        results = get_streamers(token)
        send_mail(results)
        print(f"任务完成，找到 {len(results)} 个博主。")

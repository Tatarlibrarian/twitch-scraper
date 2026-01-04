import os, requests, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 配置读取 (从 GitHub Secrets) ---
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
GOOGLE_KEY = os.environ.get('GOOGLE_SEARCH_KEY')
GOOGLE_CX = os.environ.get('GOOGLE_SEARCH_CX')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')

HISTORY_FILE = "history.txt"

def load_history():
    """读取已处理过的博主 ID"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(id_to_save):
    """将新博主 ID 追加到本地文件"""
    with open(HISTORY_FILE, "a") as f:
        f.write(id_to_save + "\n")

def get_contact_from_google(name):
    """仅对新博主调用 Google 搜索，优先提取邮箱"""
    query = f'"{name}" business email contact'
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_KEY, "cx": GOOGLE_CX, "q": query, "num": 3}
    try:
        items = requests.get(url, params=params).json().get('items', [])
        all_text = " ".join([i.get('snippet', '') + i.get('title', '') for i in items])
        # 使用正则表达式匹配邮箱
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_text)
        if emails: return f"📧 {emails[0]}"
        # 次选 Twitter
        twitter = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', all_text)
        if twitter: return f"🐦 @{twitter.group(1)}"
        return "⚠️ 未发现公开联系方式"
    except:
        return "❌ 搜索配额已耗尽或请求失败"

def get_twitch_results(history):
    auth_res = requests.post("https://id.twitch.tv/oauth2/token", 
                             data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth_res.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    params = {"game_id": "32982", "language": "en", "first": 30} # 获取 GTA V 频道前 30 名
    
    streams = requests.get("https://api.twitch.tv/helix/streams", headers=headers, params=params).json().get('data', [])
    new_bloggers = []
    for s in streams:
        uid = f"twitch_{s['user_id']}"
        # --- 去重逻辑 ---
        if uid in history: continue 
        
        if 50 <= s['viewer_count'] <= 200:
            name = s['user_name']
            contact = get_contact_from_google(name)
            save_to_history(uid)
            new_bloggers.append(f"🎮 [Twitch] {name} ({s['viewer_count']}人)\n   联系: {contact}\n   链接: https://www.twitch.tv/{s['user_login']}")
    return new_bloggers

def get_youtube_results(history):
    search_params = {"part": "snippet", "q": "Grand Theft Auto V", "type": "video", "eventType": "live", "relevanceLanguage": "en", "key": YT_API_KEY, "maxResults": 20}
    search_res = requests.get("https://www.googleapis.com/youtube/v3/search", params=search_params).json()
    video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
    
    if not video_ids: return []
    detail_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "liveStreamingDetails,snippet", "id": ",".join(video_ids), "key": YT_API_KEY}).json()
    
    new_bloggers = []
    for v in detail_res.get('items', []):
        cid = f"yt_{v['snippet']['channelId']}"
        # --- 去重逻辑 ---
        if cid in history: continue
        
        viewers = int(v.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
        if 50 <= viewers <= 200:
            name = v['snippet']['channelTitle']
            contact = get_contact_from_google(name)
            save_to_history(cid)
            new_bloggers.append(f"📺 [YouTube] {name} ({viewers}人)\n   联系: {contact}\n   链接: https://www.youtube.com/watch?v={v['id']}")
    return new_bloggers

if __name__ == "__main__":
    history_data = load_history()
    final_report = get_twitch_results(history_data) + get_youtube_results(history_data)
    
    if final_report:
        msg = MIMEMultipart()
        msg['Subject'] = f"【发现新目标】GTA 深度线索 - {datetime.now().strftime('%m-%d %H:%M')}"
        msg['From'], msg['To'] = EMAIL_ADDR, EMAIL_ADDR
        msg.attach(MIMEText("\n\n".join(final_report), 'plain'))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PASS)
            server.send_message(msg)
        print(f"成功。发现并推送了 {len(final_report)} 个新博主。")
    else:
        print("未发现新的符合条件的博主。")

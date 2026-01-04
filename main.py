import os, requests, smtplib, re
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 配置读取 ---
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
GOOGLE_KEY = os.environ.get('GOOGLE_SEARCH_KEY')
GOOGLE_CX = os.environ.get('GOOGLE_SEARCH_CX')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')

HISTORY_FILE = "history.txt"

def load_history():
    """加载已处理过的博主 ID"""
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f:
            return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(new_id):
    """保存新的博主 ID"""
    with open(HISTORY_FILE, "a") as f:
        f.write(new_id + "\n")

def get_contact_from_google(name):
    """搜索博主联系方式"""
    query = f'"{name}" business email contact'
    url = "https://www.googleapis.com/customsearch/v1"
    params = {"key": GOOGLE_KEY, "cx": GOOGLE_CX, "q": query, "num": 3}
    try:
        items = requests.get(url, params=params).json().get('items', [])
        all_text = " ".join([i.get('snippet', '') + i.get('title', '') for i in items])
        emails = re.findall(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', all_text)
        if emails: return f"📧 {emails[0]}"
        twitter = re.search(r'twitter\.com/([a-zA-Z0-9_]+)', all_text)
        if twitter: return f"🐦 @{twitter.group(1)}"
        return "⚠️ 未发现公开联系方式"
    except:
        return "❌ 搜索失败"

def get_twitch_results(history):
    auth_res = requests.post("https://id.twitch.tv/oauth2/token", 
                             data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth_res.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    params = {"game_id": "32982", "language": "en", "first": 20}
    
    streams = requests.get("https://api.twitch.tv/helix/streams", headers=headers, params=params).json().get('data', [])
    results = []
    for s in streams:
        user_id = f"twitch_{s['user_id']}"
        if user_id in history: continue # --- 去重：已存在则跳过 ---
        
        if 50 <= s['viewer_count'] <= 200:
            name = s['user_name']
            contact = get_contact_from_google(name)
            save_to_history(user_id) # 标记为已处理
            results.append(f"🎮 [Twitch] {name} ({s['viewer_count']}人)\n   联系: {contact}\n   链接: https://www.twitch.tv/{s['user_login']}")
    return results

def get_youtube_results(history):
    search_params = {"part": "snippet", "q": "Grand Theft Auto V", "type": "video", "eventType": "live", "relevanceLanguage": "en", "key": YT_API_KEY, "maxResults": 20}
    search_res = requests.get("https://www.googleapis.com/youtube/v3/search", params=search_params).json()
    video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
    
    if not video_ids: return []
    detail_res = requests.get("https://www.googleapis.com/youtube/v3/videos", params={"part": "liveStreamingDetails,snippet", "id": ",".join(video_ids), "key": YT_API_KEY}).json()
    
    results = []
    for v in detail_res.get('items', []):
        channel_id = f"yt_{v['snippet']['channelId']}"
        if channel_id in history: continue # --- 去重：已存在则跳过 ---
        
        viewers = int(v.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
        if 50 <= viewers <= 200:
            name = v['snippet']['channelTitle']
            contact = get_contact_from_google(name)
            save_to_history(channel_id) # 标记为已处理
            results.append(f"📺 [YouTube] {name} ({viewers}人)\n   联系: {contact}\n   链接: https://www.youtube.com/watch?v={v['id']}")
    return results

if __name__ == "__main__":
    history = load_history()
    combined_data = get_twitch_results(history) + get_youtube_results(history)
    
    if combined_data:
        msg = MIMEMultipart()
        msg['Subject'] = f"新增博主名单 - {datetime.now().strftime('%m-%d %H:%M')}"
        msg['From'], msg['To'] = EMAIL_ADDR, EMAIL_ADDR
        msg.attach(MIMEText("\n\n".join(combined_data), 'plain'))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PASS)
            server.send_message(msg)
        print(f"成功推送到邮箱，共 {len(combined_data)} 个新目标。")
    else:
        print("本次未发现新的博主。")

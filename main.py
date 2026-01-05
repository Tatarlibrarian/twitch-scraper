import os, requests, smtplib, re, time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 配置 ---
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')
HISTORY_FILE = "history.txt"

# --- 扩展游戏库 ---
GAMES = {
    "GTA V": {"tw_id": "32982", "yt_q": "Grand Theft Auto V"},
    "Warzone": {"tw_id": "512710", "yt_q": "Call of Duty: Warzone"},
    "TFT": {"tw_id": "513143", "yt_q": "Teamfight Tactics"},
    "Tarkov": {"tw_id": "491931", "yt_q": "Escape from Tarkov"},
    "BlazBlue": {"tw_id": "499507", "yt_q": "BlazBlue: Cross Tag Battle"},
    "Path of Exile": {"tw_id": "29307", "yt_q": "Path of Exile"},
    "Project Zomboid": {"tw_id": "31331", "yt_q": "Project Zomboid"},
    "CS2": {"tw_id": "32399", "yt_q": "Counter-Strike"},
    "Warframe": {"tw_id": "66170", "yt_q": "Warframe"},
    "Minecraft": {"tw_id": "27471", "yt_q": "Minecraft"},
    "Fortnite": {"tw_id": "33214", "yt_q": "Fortnite"}
}

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r") as f: return set(line.strip() for line in f if line.strip())
    return set()

def save_to_history(uid):
    with open(HISTORY_FILE, "a") as f: f.write(uid + "\n")

# --- YouTube 社交孤立度分析 ---
def is_yt_chat_lonely(chat_id):
    """分析聊天室是否存在互动循环"""
    if not chat_id: return True
    url = f"https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId={chat_id}&part=snippet&maxResults=15&key={YT_API_KEY}"
    try:
        res = requests.get(url).json()
        messages = res.get('items', [])
        if not messages: return True # 完全没人说话也算冷清
        
        # 统计含有 '@' 或 'Replying to' 特征的消息
        interaction_count = 0
        for m in messages:
            text = m['snippet']['displayMessage']
            if '@' in text or 'Replying to' in text:
                interaction_count += 1
        
        # 互动占比低于 10%，判定为冷清（孤立型评论区）
        return (interaction_count / len(messages)) < 0.1
    except:
        return True

def get_twitch_results(history):
    auth = requests.post("https://id.twitch.tv/oauth2/token", data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    
    results = []
    for g_name, g_info in GAMES.items():
        params = {"game_id": g_info['tw_id'], "language": "en", "first": 20}
        streams = requests.get("https://api.twitch.tv/helix/streams", headers=headers, params=params).json().get('data', [])
        for s in streams:
            uid = f"tw_{s['user_id']}"
            if uid in history: continue
            if 50 <= s['viewer_count'] <= 200:
                save_to_history(uid)
                results.append(f"🎮 [Twitch-{g_name}] {s['user_name']} ({s['viewer_count']}人)\n   链接: https://www.twitch.tv/{s['user_login']}")
    return results

def get_youtube_results(history):
    results = []
    for g_name, g_info in GAMES.items():
        search_url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={g_info['yt_q']}&type=video&eventType=live&relevanceLanguage=en&key={YT_API_KEY}&maxResults=15"
        vids = requests.get(search_url).json().get('items', [])
        video_ids = [v['id']['videoId'] for v in vids]
        
        if not video_ids: continue
        details = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails,snippet&id={','.join(video_ids)}&key={YT_API_KEY}").json().get('items', [])
        
        for d in details:
            cid = f"yt_{d['snippet']['channelId']}"
            if cid in history: continue
            
            viewers = int(d.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
            if 50 <= viewers <= 200:
                chat_id = d.get('liveStreamingDetails', {}).get('activeLiveChatId')
                # 核心过滤：只有评论区冷清的主播才加入名单
                if is_yt_chat_lonely(chat_id):
                    save_to_history(cid)
                    results.append(f"📺 [YouTube-{g_name}] {d['snippet']['channelTitle']} ({viewers}人)\n   链接: https://www.youtube.com/watch?v={d['id']}")
    return results

if __name__ == "__main__":
    h = load_history()
    data = get_twitch_results(h) + get_youtube_results(h)
    if data:
        msg = MIMEMultipart()
        msg['Subject'] = f"【冷清评论区目标】双平台报告 - {datetime.now().strftime('%m-%d %H:%M')}"
        msg['From'], msg['To'] = EMAIL_ADDR, EMAIL_ADDR
        msg.attach(MIMEText("\n\n".join(data), 'plain'))
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PASS)
            server.send_message(msg)

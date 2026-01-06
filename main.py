import os, requests, csv, re
from datetime import datetime

# 配置
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
CSV_FILE = "leads.csv"

# 11款目标游戏
GAMES = {
    "GTA V": {"tw_id": "32982", "yt_q": "Grand Theft Auto V"},
    "Warzone": {"tw_id": "512710", "yt_q": "Call of Duty: Warzone"},
    "TFT": {"tw_id": "513143", "yt_q": "Teamfight Tactics"},
    "Tarkov": {"tw_id": "491931", "yt_q": "Escape from Tarkov"},
    "BlazBlue": {"tw_id": "499507", "yt_q": "BlazBlue: Cross Tag Battle"},
    "Path of Exile": {"tw_id": "29307", "yt_q": "Path of Exile"},
    "Project Zomboid": {"tw_id": "31331", "yt_q": "Project Zomboid"},
    "CS2": {"tw_id": "32399", "yt_q": "Counter-Strike 2"},
    "Warframe": {"tw_id": "66170", "yt_q": "Warframe"},
    "Minecraft": {"tw_id": "27471", "yt_q": "Minecraft"},
    "Fortnite": {"tw_id": "33214", "yt_q": "Fortnite"}
}

def load_processed_ids():
    if not os.path.exists(CSV_FILE): return set()
    with open(CSV_FILE, "r", encoding='utf-8') as f:
        return {row["ID"] for row in csv.DictReader(f) if row.get("ID")}

def is_yt_chat_lonely(chat_id):
    """分析聊天室是否存在互动循环 (社交孤立度算法)"""
    if not chat_id: return True
    url = f"https://www.googleapis.com/youtube/v3/liveChat/messages?liveChatId={chat_id}&part=snippet&maxResults=15&key={YT_API_KEY}"
    try:
        res = requests.get(url).json()
        messages = res.get('items', [])
        if not messages: return True
        interactions = sum(1 for m in messages if '@' in m['snippet'].get('displayMessage', ''))
        return (interactions / len(messages)) < 0.1
    except: return True

def get_twitch_results(history):
    auth = requests.post("https://id.twitch.tv/oauth2/token", data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    rows = []
    for g_name, g_info in GAMES.items():
        try:
            streams = requests.get(f"https://api.twitch.tv/helix/streams?game_id={g_info['tw_id']}&language=en&first=30", headers=headers).json().get('data', [])
            for s in streams:
                uid = f"tw_{s['user_id']}"
                if uid not in history and 50 <= s['viewer_count'] <= 200:
                    rows.append([uid, s['user_name'], "Twitch", g_name, f"https://www.twitch.tv/{s['user_login']}", "New", "", datetime.now().strftime("%Y-%m-%d")])
        except: continue
    return rows

def get_youtube_results(history):
    rows = []
    for g_name, g_info in GAMES.items():
        try:
            vids = requests.get(f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={g_info['yt_q']}&type=video&eventType=live&key={YT_API_KEY}&maxResults=15").json().get('items', [])
            ids = [v.get('id', {}).get('videoId') for v in vids if v.get('id', {}).get('videoId')]
            if not ids: continue
            details = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails,snippet&id={','.join(ids)}&key={YT_API_KEY}").json().get('items', [])
            for d in details:
                cid = f"yt_{d['snippet']['channelId']}"
                viewers = int(d.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
                if cid not in history and 50 <= viewers <= 200:
                    if is_yt_chat_lonely(d.get('liveStreamingDetails', {}).get('activeLiveChatId')):
                        rows.append([cid, d['snippet']['channelTitle'], "YouTube", g_name, f"https://www.youtube.com/watch?v={d['id']}", "New", "", datetime.now().strftime("%Y-%m-%d")])
        except: continue
    return rows

if __name__ == "__main__":
    processed = load_processed_ids()
    all_new = get_twitch_results(processed) + get_youtube_results(processed)
    with open(CSV_FILE, "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(all_new)

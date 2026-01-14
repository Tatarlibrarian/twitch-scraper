import os, requests, csv
from datetime import datetime

# 配置从 GitHub Secrets 读取
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
CSV_FILE = "leads.csv"

# 全球 40 大高流量游戏类目 (Twitch ID & YouTube 搜索词)
GAMES = {
    # 竞技 FPS/TPS
    "VALORANT": {"tw_id": "516575", "yt_q": "VALORANT"},
    "CS2": {"tw_id": "32399", "yt_q": "Counter-Strike 2"},
    "Apex Legends": {"tw_id": "511224", "yt_q": "Apex Legends"},
    "Warzone": {"tw_id": "512710", "yt_q": "Call of Duty: Warzone"},
    "Fortnite": {"tw_id": "33214", "yt_q": "Fortnite"},
    "Rainbow Six Siege": {"tw_id": "460630", "yt_q": "Rainbow Six Siege"},
    "Overwatch 2": {"tw_id": "515025", "yt_q": "Overwatch 2"},
    "PUBG": {"tw_id": "493051", "yt_q": "PUBG: BATTLEGROUNDS"},
    "Deadlock": {"tw_id": "136934891", "yt_q": "Deadlock Valve"},
    
    # MOBA 与 战术
    "League of Legends": {"tw_id": "21779", "yt_q": "League of Legends"},
    "Dota 2": {"tw_id": "29595", "yt_q": "Dota 2"},
    "TFT": {"tw_id": "513143", "yt_q": "Teamfight Tactics"},
    
    # 生存与开放世界 (博主忠诚度极高)
    "GTA V": {"tw_id": "32982", "yt_q": "Grand Theft Auto V"},
    "Rust": {"tw_id": "263490", "yt_q": "Rust"},
    "DayZ": {"tw_id": "65632", "yt_q": "DayZ"},
    "Tarkov": {"tw_id": "491931", "yt_q": "Escape from Tarkov"},
    "Ark: Ascended": {"tw_id": "1016641571", "yt_q": "ARK: Survival Ascended"},
    "Minecraft": {"tw_id": "27471", "yt_q": "Minecraft"},
    "Roblox": {"tw_id": "27471", "yt_q": "Roblox"},
    "Project Zomboid": {"tw_id": "31331", "yt_q": "Project Zomboid"},
    "7 Days to Die": {"tw_id": "25936", "yt_q": "7 Days to Die"},
    
    # MMORPG (土豪与肝帝聚集地)
    "World of Warcraft": {"tw_id": "18122", "yt_q": "World of Warcraft"},
    "FFXIV": {"tw_id": "24241", "yt_q": "Final Fantasy XIV"},
    "Path of Exile": {"tw_id": "29307", "yt_q": "Path of Exile"},
    "Old School RuneScape": {"tw_id": "313558", "yt_q": "Old School RuneScape"},
    "Black Desert": {"tw_id": "386686", "yt_q": "Black Desert"},
    
    # 二次元与 ARPG
    "Genshin Impact": {"tw_id": "518184", "yt_q": "Genshin Impact"},
    "Honkai: Star Rail": {"tw_id": "1195672923", "yt_q": "Honkai: Star Rail"},
    "Elden Ring": {"tw_id": "512953", "yt_q": "Elden Ring"},
    "Monster Hunter": {"tw_id": "518381", "yt_q": "Monster Hunter Wilds"},
    "Warframe": {"tw_id": "66170", "yt_q": "Warframe"},
    
    # 体育、赛车与互动
    "EA Sports FC": {"tw_id": "2106331932", "yt_q": "EA Sports FC 25"},
    "Rocket League": {"tw_id": "30921", "yt_q": "Rocket League"},
    "F1 24": {"tw_id": "1675271926", "yt_q": "F1 24"},
    "Dead by Daylight": {"tw_id": "493051", "yt_q": "Dead by Daylight"},
    "Street Fighter 6": {"tw_id": "55453844", "yt_q": "Street Fighter 6"},
    "BlazBlue": {"tw_id": "499507", "yt_q": "BlazBlue: Cross Tag Battle"},
    
    # 其他大热
    "Manor Lords": {"tw_id": "518388", "yt_q": "Manor Lords"},
    "Total War: WH3": {"tw_id": "518868", "yt_q": "Total War: Warhammer III"},
    "Terraria": {"tw_id": "31376", "yt_q": "Terraria"}
}

def load_processed_ids():
    if not os.path.exists(CSV_FILE): return set()
    with open(CSV_FILE, "r", encoding='utf-8') as f:
        return {row["ID"] for row in csv.DictReader(f) if row.get("ID")} #

def get_twitch_results(history):
    auth = requests.post("https://id.twitch.tv/oauth2/token", data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth.get('access_token')
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    rows = []
    for g_name, g_info in GAMES.items():
        try:
            # 移除了 language 参数，扩大到全球博主
            url = f"https://api.twitch.tv/helix/streams?game_id={g_info['tw_id']}&first=40"
            streams = requests.get(url, headers=headers).json().get('data', [])
            for s in streams:
                uid = f"tw_{s['user_id']}"
                if uid not in history and 50 <= s['viewer_count'] <= 250:
                    rows.append([uid, s['user_name'], "Twitch", g_name, f"https://www.twitch.tv/{s['user_login']}", "New", "", datetime.now().strftime("%Y-%m-%d")])
        except: continue
    return rows

def get_youtube_results(history):
    rows = []
    for g_name, g_info in GAMES.items():
        try:
            # 移除了 relevanceLanguage 参数，获取全球直播内容
            url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&q={g_info['yt_q']}&type=video&eventType=live&key={YT_API_KEY}&maxResults=20"
            vids = requests.get(url).json().get('items', [])
            video_ids = [v.get('id', {}).get('videoId') for v in vids if v.get('id', {}).get('videoId')]
            if not video_ids: continue
            
            details = requests.get(f"https://www.googleapis.com/youtube/v3/videos?part=liveStreamingDetails,snippet&id={','.join(video_ids)}&key={YT_API_KEY}").json().get('items', [])
            for d in details:
                cid = f"yt_{d['snippet']['channelId']}"
                viewers = int(d.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
                # 移除了社交冷清度判定，直接根据人数过滤
                if cid not in history and 50 <= viewers <= 250:
                    rows.append([cid, d['snippet']['channelTitle'], "YouTube", g_name, f"https://www.youtube.com/watch?v={d['id']}", "New", "", datetime.now().strftime("%Y-%m-%d")])
        except: continue
    return rows

if __name__ == "__main__":
    processed = load_processed_ids()
    all_new = get_twitch_results(processed) + get_youtube_results(processed)
    with open(CSV_FILE, "a", newline='', encoding='utf-8') as f:
        csv.writer(f).writerows(all_new)
    print(f"Captured {len(all_new)} leads across 40 high-traffic categories.")

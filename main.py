import os, requests, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# --- 配置读取 ---
TWITCH_ID = os.environ.get('TWITCH_CLIENT_ID')
TWITCH_SECRET = os.environ.get('TWITCH_CLIENT_SECRET')
YT_API_KEY = os.environ.get('YOUTUBE_API_KEY')
EMAIL_ADDR = os.environ.get('EMAIL_ADDRESS')
EMAIL_PASS = os.environ.get('EMAIL_PASSWORD')

# --- Twitch 逻辑 ---
def get_twitch_results():
    auth_url = "https://id.twitch.tv/oauth2/token"
    auth_res = requests.post(auth_url, data={"client_id": TWITCH_ID, "client_secret": TWITCH_SECRET, "grant_type": "client_credentials"}).json()
    token = auth_res.get('access_token')
    
    url = "https://api.twitch.tv/helix/streams"
    headers = {"Client-ID": TWITCH_ID, "Authorization": f"Bearer {token}"}
    params = {"game_id": "32982", "language": "en", "first": 100} # GTA V
    
    results = []
    streams = requests.get(url, headers=headers, params=params).json().get('data', [])
    for s in streams:
        if 50 <= s['viewer_count'] <= 200:
            results.append(f"[Twitch] {s['user_name']} | 人数: {s['viewer_count']} | https://www.twitch.tv/{s['user_login']}")
    return results

# --- YouTube 逻辑 ---
def get_youtube_results():
    results = []
    # 1. 搜索 GTA V 正在直播的视频 ID
    search_url = "https://www.googleapis.com/youtube/v3/search"
    search_params = {
        "part": "snippet",
        "q": "Grand Theft Auto V",
        "type": "video",
        "eventType": "live",
        "relevanceLanguage": "en",
        "key": YT_API_KEY,
        "maxResults": 50
    }
    search_res = requests.get(search_url, params=search_params).json()
    video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
    
    if not video_ids: return results

    # 2. 批量查询这些直播间的实时人数
    detail_url = "https://www.googleapis.com/youtube/v3/videos"
    detail_params = {
        "part": "liveStreamingDetails,snippet",
        "id": ",".join(video_ids),
        "key": YT_API_KEY
    }
    detail_res = requests.get(detail_url, params=detail_params).json()
    
    for v in detail_res.get('items', []):
        viewers = int(v.get('liveStreamingDetails', {}).get('concurrentViewers', 0))
        if 50 <= viewers <= 200:
            title = v['snippet']['channelTitle']
            vid_id = v['id']
            results.append(f"[YouTube] {title} | 人数: {viewers} | https://www.youtube.com/watch?v={vid_id}")
    return results

# --- 邮件发送逻辑 ---
def send_combined_mail(twitch_list, yt_list):
    if not twitch_list and not yt_list:
        print("两个平台均未发现目标博主。")
        return

    content = "【Twitch 符合条件的博主】\n" + ("\n".join(twitch_list) if twitch_list else "无")
    content += "\n\n" + "="*30 + "\n\n"
    content += "【YouTube 符合条件的博主】\n" + ("\n".join(yt_list) if yt_list else "无")
    
    msg = MIMEMultipart()
    msg['Subject'] = f"双平台 GTA 筛选报告 - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    msg['From'], msg['To'] = EMAIL_ADDR, EMAIL_ADDR
    msg.attach(MIMEText(content, 'plain'))
    
    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_ADDR, EMAIL_PASS)
            server.send_message(msg)
            print("双平台报告已发送！")
    except Exception as e:
        print(f"邮件发送失败: {e}")

if __name__ == "__main__":
    t_results = get_twitch_results()
    y_results = get_youtube_results()
    send_combined_mail(t_results, y_results)

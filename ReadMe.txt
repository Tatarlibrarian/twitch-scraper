# Twitch-Scraper | 主播合作线索采集机器人

## 📌 项目简介

这是一个自动化的主播合作线索采集与分析工具，专门用于从 Twitch 和 YouTube 平台上挖掘适合商业合作的中小型主播（50-250 名观众）。

**核心功能：**
- 🎮 覆盖 40 个高流量游戏类目（包括 VALORANT、League of Legends、Minecraft、Genshin Impact 等）
- 📊 自动抓取符合观众数条件的主播数据
- 📧 智能提取主播联系方式（邮箱、Twitter 等）
- 📨 自动发送汇总报告邮件

---

## 🔧 项目结构

```
twitch-scraper/
├── main.py              # 主播数据采集脚本
├── enricher.py          # 联系方式挖掘与数据增强脚本
├── leads.csv            # 采集的主播数据库
└── 主播名单X.csv         # 历史数据备份
```

---

## ⚙️ 环境要求

- Python 3.7+
- 需要安装的依赖库：
  ```bash
  pip install requests
  ```

---

## 🔐 必需配置的秘钥

> ⚠️ **重要：** 在使用本项目前，您必须重新申请并配置以下 API 秘钥。

### 1. Twitch API 凭证
用于访问 Twitch 直播数据和主播信息。

**申请地址：** https://dev.twitch.tv/console/apps

**需要配置的环境变量：**
- `TWITCH_CLIENT_ID` - Twitch 应用的 Client ID
- `TWITCH_CLIENT_SECRET` - Twitch 应用的 Client Secret

---

### 2. YouTube Data API v3
用于访问 YouTube 直播数据和频道信息。

**申请地址：** https://console.cloud.google.com/apis/credentials

**需要配置的环境变量：**
- `YOUTUBE_API_KEY` - YouTube Data API v3 密钥

**配额说明：** 免费版每天配额为 10,000 units，本项目单次运行约消耗 200-500 units。

---

### 3. Google Custom Search API
用于通过搜索引擎查找主播的公开联系方式（`enricher.py` 使用）。

**申请地址：**
- API Key: https://console.cloud.google.com/apis/credentials
- 自定义搜索引擎 ID: https://programmablesearchengine.google.com/

**需要配置的环境变量：**
- `GOOGLE_SEARCH_KEY` - Google Custom Search API 密钥
- `GOOGLE_SEARCH_CX` - 自定义搜索引擎 ID (CX)

**配额说明：** 免费版每天限制 100 次搜索，`enricher.py` 已内置保护机制（每次最多处理 500 个主播）。

---

### 4. Email 配置（可选）
用于自动发送联系方式汇总报告（`enricher.py` 使用）。

**需要配置的环境变量：**
- `EMAIL_ADDRESS` - 发件邮箱地址（建议使用 Gmail）
- `EMAIL_PASSWORD` - 邮箱应用专用密码（非登录密码）

**Gmail 应用专用密码申请：** https://myaccount.google.com/apppasswords

---

## 🚀 使用方法

### 方式一：本地运行

1. **设置环境变量**（Linux/macOS）：
   ```bash
   export TWITCH_CLIENT_ID="你的_Twitch_Client_ID"
   export TWITCH_CLIENT_SECRET="你的_Twitch_Secret"
   export YOUTUBE_API_KEY="你的_YouTube_API_Key"
   export GOOGLE_SEARCH_KEY="你的_Google_Search_Key"
   export GOOGLE_SEARCH_CX="你的_搜索引擎_CX"
   export EMAIL_ADDRESS="你的邮箱@gmail.com"
   export EMAIL_PASSWORD="你的应用专用密码"
   ```

   **Windows (PowerShell)：**
   ```powershell
   $env:TWITCH_CLIENT_ID="你的_Twitch_Client_ID"
   $env:TWITCH_CLIENT_SECRET="你的_Twitch_Secret"
   # ... 其他环境变量
   ```

2. **运行采集脚本**：
   ```bash
   python main.py
   ```
   这将扫描 40 个游戏类目，采集符合条件的主播数据到 `leads.csv`。

3. **运行增强脚本**（挖掘联系方式）：
   ```bash
   python enricher.py
   ```
   这将从主播的简介和搜索结果中提取邮箱/Twitter 等联系方式，并通过邮件发送报告。

---

### 方式二：GitHub Actions 自动化运行

如果您在 GitHub 上部署此项目，需要在仓库的 **Settings → Secrets and variables → Actions** 中配置以下 Secrets：

| Secret 名称 | 说明 |
|------------|------|
| `TWITCH_CLIENT_ID` | Twitch API Client ID |
| `TWITCH_CLIENT_SECRET` | Twitch API Client Secret |
| `YOUTUBE_API_KEY` | YouTube Data API v3 密钥 |
| `GOOGLE_SEARCH_KEY` | Google Custom Search API 密钥 |
| `GOOGLE_SEARCH_CX` | 自定义搜索引擎 ID |
| `EMAIL_ADDRESS` | 通知邮箱地址 |
| `EMAIL_PASSWORD` | 邮箱应用专用密码 |

---

## 📊 输出说明

### leads.csv 字段说明
| 字段 | 说明 |
|------|------|
| ID | 主播唯一标识（tw_xxx 或 yt_xxx） |
| Name | 主播昵称 |
| Platform | 平台（Twitch / YouTube） |
| Game | 正在直播的游戏类目 |
| Link | 主播频道链接 |
| Status | 状态（New / Enriched） |
| Contact | 联系方式（邮箱/Twitter/未发现） |
| Date | 采集日期 |

---

## ⚠️ 注意事项

1. **API 配额限制**：
   - Google Custom Search 免费版每天仅 100 次，建议谨慎使用 `enricher.py`
   - YouTube API 每天配额为 10,000 units，大量调用可能触发限制

2. **隐私与合规**：
   - 本工具仅采集主播公开资料，但请遵守相关平台的服务条款
   - 联系主播时请尊重对方意愿，避免骚扰

3. **数据持久化**：
   - `leads.csv` 会自动去重，多次运行不会重复采集同一主播
   - 建议定期备份 CSV 文件

---

## 🤝 项目移交

如果您是接手此项目的新开发者，请务必：

1. ✅ 重新申请所有 API 秘钥（**不要使用原项目的秘钥**）
2. ✅ 根据自己的需求调整游戏类目列表（`main.py` 中的 `GAMES` 字典）

---

## 📜 许可证

本项目仅供学习和商业线索挖掘使用，请勿用于非法用途。

---

**祝您顺利找到优质合作主播！🎉**

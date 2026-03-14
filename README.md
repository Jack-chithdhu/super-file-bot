<div align="center">

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=200&section=header&text=Super%20File%20Bot&fontSize=60&fontColor=fff&animation=twinkling&fontAlignY=35&desc=Advanced%20Telegram%20File%20Sharing%20Bot&descAlignY=55&descSize=18" width="100%"/>

<br>

[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-Latest-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://pyrogram.org)
[![MongoDB](https://img.shields.io/badge/MongoDB-Atlas-47A248?style=for-the-badge&logo=mongodb&logoColor=white)](https://mongodb.com)
[![License](https://img.shields.io/badge/License-GPL%203.0-blue?style=for-the-badge)](LICENSE)

<br>

> 🚀 **A powerful, feature-rich Telegram bot** that stores files in a private channel and shares them via special links — with Premium, Requests, Live Support Chat, Captcha, Announcements, and much more.

<br>

[![Deploy on Railway](https://railway.app/button.svg)](https://railway.app/new/template?template=https://github.com/Jack-chithdhu/super-file-bot)
&nbsp;&nbsp;
[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/Jack-chithdhu/super-file-bot&branch=main&name=super-file-bot)

</div>

---

## ✨ Features

<table>
<tr>
<td width="50%">

### 🗂 File Sharing
- 🔗 Share files via special links
- 📦 Batch links for multiple files
- 🔒 Admin-only file storage
- 🛡️ Optional content protection

### 💎 Premium System
- 💳 Self-service payment flow
- 🖼️ QR code payment support
- ♾️ Unlimited downloads
- 🔓 Bypass force subscribe
- 🗂 Files never auto-deleted
- 🔔 Expiry reminders (3d + 1d)
- 🎁 Multiple premium durations

### 🎬 Request System
- 🎬 Movie, 🎌 Anime & 📺 Series requests
- 🎯 Inline button UI flow
- ✅ Admin fulfill/decline
- ⏰ Auto-decline after X days
- 💬 Custom request instructions
- 📋 Manage requests from settings
- 📢 Optional public log channel

</td>
<td width="50%">

### 💬 Support Chat
- 🔄 Two-way admin ↔ user live chat
- 📋 Active sessions panel
- 🔔 Instant admin notifications

### 🤖 Captcha System
- 🎯 Emoji button captcha for new users
- 🔄 40 emojis across 5 categories
- ⏰ 60 second timeout
- 🚫 3 attempts max
- ✅ Toggle on/off from settings

### 📣 Announcements
- 📝 Compose with live preview
- 📡 Send to all users instantly
- 📊 Live progress bar
- 📈 Detailed delivery report

### ⚙️ Settings Panel
- 🎛 Full button-based settings panel
- 💎 Premium plan controls
- 💳 Payment & QR management
- 🤖 Captcha toggle
- ♻️ Auto-delete controls
- 🔒 Content protection
- 📢 Force subscribe settings
- 👋 Welcome message editor
- 📆 Daily limit quick-set

</td>
</tr>
</table>

---

## 🆚 Free vs Premium

<div align="center">

| Feature | 🆓 Free | 💎 Premium |
|:---|:---:|:---:|
| Daily Downloads | 20/day | ♾️ Unlimited |
| Auto-Delete | ✅ Yes | ❌ Never |
| Force Subscribe | ✅ Required | ❌ Bypassed |
| Expiry Reminders | ❌ | ✅ |
| Priority Delivery | ❌ | ✅ |

</div>

---

## 🚀 Deploy

<details>
<summary><b>▶️ Railway (Recommended)</b></summary>
<br>

1. Click the **Deploy on Railway** button at the top
2. Connect your GitHub account
3. Fill in all required environment variables
4. Click **Deploy** — Railway auto-restarts on crash ✅

</details>

<details>
<summary><b>▶️ Koyeb</b></summary>
<br>

1. Click the **Deploy to Koyeb** button at the top
2. Connect your GitHub repo
3. Set environment variables
4. Click **Deploy** ✅

</details>

<details>
<summary><b>▶️ VPS / Local</b></summary>
<br>

```bash
git clone https://github.com/Jack-chithdhu/super-file-bot
cd super-file-bot
pip3 install -r requirements.txt
cp .env.example .env
# Edit .env with your values
python3 main.py
```

</details>

---

## ⚙️ Environment Variables

<details>
<summary><b>🔴 Required Variables</b></summary>
<br>

| Variable | Description |
|:---|:---|
| `TG_BOT_TOKEN` | Bot token from [@BotFather](https://t.me/BotFather) |
| `APP_ID` | API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | API Hash from [my.telegram.org](https://my.telegram.org) |
| `OWNER_ID` | Your Telegram user ID |
| `CHANNEL_ID` | DB channel ID (e.g. `-100xxxxxxxxxx`) |
| `DATABASE_URL` | MongoDB Atlas connection URL |

</details>

<details>
<summary><b>🟡 Optional Variables</b></summary>
<br>

| Variable | Default | Description |
|:---|:---:|:---|
| `DATABASE_NAME` | `filesharexbot` | MongoDB database name |
| `FORCE_SUB_CHANNEL` | `0` | Force subscribe channel ID (0 = off) |
| `JOIN_REQUEST_ENABLED` | `False` | Use join requests instead of direct join |
| `REQUEST_CHANNEL_ID` | `0` | Optional public log channel for requests |
| `ADMINS` | — | Space-separated extra admin user IDs |
| `PROTECT_CONTENT` | `False` | Prevent file forwarding |
| `AUTO_DELETE_TIME` | `0` | Seconds before deleting files (0 = off) |
| `PREMIUM_DURATION_DAYS` | `30` | Default premium duration in days |
| `FREE_DAILY_LIMIT` | `20` | Free user daily download cap |
| `TG_BOT_WORKERS` | `8` | Concurrent update workers |
| `START_MESSAGE` | *(default)* | Custom start message (HTML) |
| `START_PIC` | — | Image URL for start message |
| `CUSTOM_CAPTION` | — | Custom file caption |

> 💡 Most settings can be changed anytime via the `/settings` panel — no need to redeploy!

</details>

---

## 📖 Commands

<details>
<summary><b>👤 User Commands</b></summary>
<br>

| Command | Description |
|:---|:---|
| `/start` | Start the bot / receive files |
| `/help` | Show help menu with buttons |
| `/profile` | View your profile & download stats |
| `/request` | Request a Movie, Anime or Series |
| `/mystatus` | Track your request history |
| `/premium` | Check status & subscribe to premium |
| `/support` | Open live chat with admin |
| `/closechat` | End your support session |

</details>

<details>
<summary><b>🛡️ Admin Commands</b></summary>
<br>

| Command | Description |
|:---|:---|
| `/users` | Total user count |
| `/broadcast` | Broadcast any message to all users |
| `/ban <id> [reason]` | Ban a user |
| `/unban <id>` | Unban a user |
| `/banned` | List all banned users |
| `/addpremium <id> [days]` | Grant premium to a user |
| `/removepremium <id>` | Revoke premium |
| `/listpremium` | List all premium users |
| `/allrequests [pending]` | View all requests |
| `/fulfill <id> [note]` | Fulfill a request |
| `/decline <id> <reason>` | Decline a request |
| `/filestats` | File statistics dashboard |
| `/activechats` | View active support sessions |
| `/chatto <user_id>` | Start replying to a user |
| `/endchat` | Stop replying to current user |
| `/batch` | Create batch file link |
| `/genlink` | Create single file link |
| `/stats` | Bot uptime |
| `/adminhelp` | Full admin command reference |

</details>

<details>
<summary><b>👑 Owner Only Commands</b></summary>
<br>

| Command | Description |
|:---|:---|
| `/settings` | 🎛 Open full settings panel |
| `/announce` | 📣 Send announcement to all users |
| `/addadmin <id>` | Add a bot admin |
| `/removeadmin <id>` | Remove an admin |
| `/listadmins` | List all admins |
| `/togglepremium` | Toggle premium mode on/off |
| `/setdailylimit <n>` | Set free user daily download limit |
| `/setpayment <key> <value>` | Set payment details |
| `/setqr` | Set payment QR image |

> 💡 Most of these are also available via the `/settings` panel with buttons!

</details>

---

## ⚙️ Settings Panel

Type `/settings` as owner to access the full button-based control panel:

```
⚙️ BOT SETTINGS PANEL

[💎 PREMIUM PLAN        ]
[💳 PAYMENT SETTINGS    ]
[🤖 CAPTCHA  ✅         ]
[♻️ AUTO DELETE  ❌     ]
[🔒 PROTECT CONTENT  ❌ ]
[🎬 REQUEST SYSTEM  ✅  ]
[📢 FORCE SUBSCRIBE     ]
[👋 WELCOME MESSAGE     ]
[📆 DAILY LIMIT         ]
[🔒 CLOSE               ]
```

---

## 🗄️ MongoDB Atlas Setup

<details>
<summary><b>Click to expand setup guide</b></summary>
<br>

1. Go to [mongodb.com/atlas](https://www.mongodb.com/atlas) → Sign up free
2. Create a **free M0 cluster**
3. Create a database user with a strong password
4. Under **Network Access** → Add IP → `0.0.0.0/0`
5. Click **Connect** → **Drivers** → copy the URI
6. Replace `<password>` with your password
7. Paste as `DATABASE_URL` in your environment

</details>

---

## ⚡ Setup Checklist

- [ ] Create a **private channel** → add bot as admin → copy ID as `CHANNEL_ID`
- [ ] Get `APP_ID` and `API_HASH` from [my.telegram.org](https://my.telegram.org)
- [ ] Get `TG_BOT_TOKEN` from [@BotFather](https://t.me/BotFather)
- [ ] Set up MongoDB Atlas and get `DATABASE_URL`
- [ ] Deploy on Railway or Koyeb
- [ ] Send `/settings` to configure everything with buttons
- [ ] Set payment details via `/settings` → 💳 Payment Settings
- [ ] Send your QR image and set it via `/settings` → 💳 → 🖼️ Set QR

---

## 💳 Payment Setup

After deploying, set up payment so users can subscribe to premium:

```
/setpayment upi yourname@upi
/setpayment bank "Acc: 123456789 | IFSC: SBIN0001234"
/setpayment note "Send screenshot after payment"
```

Then send your QR code image in chat and reply to it with `/setqr`

**Or use the settings panel:** `/settings` → 💳 Payment Settings

---

<div align="center">

## 🛠️ Built With

![Python](https://img.shields.io/badge/Python-3776AB?style=flat-square&logo=python&logoColor=white)
![Pyrogram](https://img.shields.io/badge/Pyrogram-2CA5E0?style=flat-square&logo=telegram&logoColor=white)
![MongoDB](https://img.shields.io/badge/MongoDB-47A248?style=flat-square&logo=mongodb&logoColor=white)
![Docker](https://img.shields.io/badge/Docker-2496ED?style=flat-square&logo=docker&logoColor=white)
![Railway](https://img.shields.io/badge/Railway-0B0D0E?style=flat-square&logo=railway&logoColor=white)

<br>

**Made with ❤️ by [Jack-chithdhu](https://github.com/Jack-chithdhu)**

<img src="https://capsule-render.vercel.app/api?type=waving&color=gradient&customColorList=6,11,20&height=100&section=footer" width="100%"/>

</div>

# 🏢 PeopleFirst HR Chatbot

An AI-powered HR Assistant chatbot built with **Python**, **Flask**, **LangChain**, **Ollama (Llama 3.2)**, and **SQLite**.

![Python](https://img.shields.io/badge/Python-3.10+-blue?logo=python)
![Flask](https://img.shields.io/badge/Flask-3.0-black?logo=flask)
![LangChain](https://img.shields.io/badge/LangChain-0.2-green)
![Ollama](https://img.shields.io/badge/Ollama-Llama_3.2-purple)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## ✨ Features

| Feature | Description |
|---|---|
| 🔐 Login | Employee ID + Password authentication |
| 🤖 AI Chat | Llama 3.2 via Ollama + LangChain with smart fallback |
| 📅 Leave Flow | 4-step guided leave application (Date → Reason → Type → DB) |
| 📊 Dashboard | Analytics, charts, leave trends, profile overview |
| 🎙️ Voice Input | Speak your queries using Web Speech API |
| 💡 Smart Chips | Context-aware follow-up suggestions after every reply |
| 🔔 Notifications | Real-time in-app notifications for leave approvals |
| 📥 Export | Download your full chat history as a .txt file |
| 📧 Email Template | Auto-generated leave email template |
| ⭐ Feedback | Rate the HR Assistant from the dashboard |

---

## 🗂️ Project Structure

```
hr-chatbot/
│
├── app.py                  # Main Flask application
│
├── templates/
│   ├── login.html          # Login page
│   ├── chat.html           # Main chat interface
│   └── dashboard.html      # Analytics dashboard
│
├── static/
│   ├── css/                # (optional custom styles)
│   ├── js/                 # (optional custom scripts)
│   └── img/                # (optional images)
│
├── requirements.txt        # Python dependencies
├── .env.example            # Environment variable template
├── .gitignore              # Git ignore rules
└── README.md               # This file
```

---

## 🚀 Setup & Run

### Step 1 — Clone the repository
```bash
git clone https://github.com/YOUR_USERNAME/hr-chatbot.git
cd hr-chatbot
```

### Step 2 — Create virtual environment
```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### Step 3 — Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4 — Set up environment variables
```bash
cp .env.example .env
# Edit .env with your values
```

### Step 5 — Install and start Ollama (for AI responses)
```bash
# Download Ollama from https://ollama.com
ollama pull llama3.2
ollama serve
```
> 💡 The app works without Ollama too — it falls back to a smart rule-based engine automatically.

### Step 6 — Run the app
```bash
python app.py
```

Visit: **http://localhost:5000**

---

## 👥 Demo Accounts

| Employee | ID | Password | Department |
|---|---|---|---|
| Arun Kumar | `EMP001` | `password123` | Engineering |
| Priya Lakshmi | `EMP002` | `priya2024` | HR (Admin) |
| Karthik Rajan | `EMP003` | `karthik@123` | Finance |

---

## 💬 Example Conversation

```
You:  I want leave on 22/06/2026
Bot:  Got it — leave for 22 Jun 2026. Could you share the reason?

You:  My grandfather passed away
Bot:  I'm so sorry for your loss 💙 Please take the time you need.
      This qualifies as Bereavement Leave.
      Choose your leave type: Annual / Sick / Casual / LOP

You:  Annual Leave
Bot:  ✅ Annual Leave approved for 22 Jun 2026!
      Balance: 5 → 4 days remaining
      📧 Email your team lead Priya Menon with this request.
      [Database updated]
```

---

## 🗄️ Database Schema

| Table | Purpose |
|---|---|
| `employees` | All employee info, balances, manager, project |
| `leave_requests` | Every leave application with type, date, reason, status |
| `chat_history` | Full conversation log per employee |
| `notifications` | In-app notification messages |
| `feedback` | Star ratings and comments |

---

## 🛠️ Tech Stack

- **Backend:** Python 3.10+, Flask 3.0, SQLAlchemy
- **Database:** SQLite (dev) — easily swappable to PostgreSQL/MySQL
- **AI:** LangChain + Ollama + Llama 3.2
- **Frontend:** Pure HTML/CSS/JS — no frameworks needed
- **Voice:** Web Speech API (Chrome/Edge)

---

## 📜 License

MIT License — free to use and modify.

---

## 🙏 Credits

Built with ❤️ using Claude AI, Python, LangChain, and Ollama.

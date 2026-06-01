# 🏢 PeopleFirst HR Chatbot

An AI-powered HR chatbot built with Python, Flask, LangChain, Ollama (Llama 3.2), and SQLite.

## ✨ Features
- 🔐 Secure employee login (Employee ID + Password)
- 🤖 AI HR Assistant powered by Llama 3.2 via Ollama
- 📅 Leave management (Annual, Sick, LOP) with real-time DB updates
- 📋 Full HR policy knowledge (leave, attendance, benefits, encashment, probation)
- 📊 Live leave balance meter in sidebar
- 🚨 Emergency leave handling with compassionate responses
- 📜 Leave history tracking
- 💡 Smart fallback if Ollama is not running

## 🚀 Setup Instructions

### 1. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 2. Install and Start Ollama
```bash
# Install Ollama from https://ollama.com
ollama pull llama3.2
ollama serve
```

### 3. Run the application
```bash
python app.py
```

Visit: http://localhost:5000

## 👥 Demo Accounts

| Name | Employee ID | Password | Dept |
|------|-------------|----------|------|
| Arun Kumar | EMP001 | password123 | Engineering |
| Priya Lakshmi | EMP002 | priya2024 | HR |
| Karthik Rajan | EMP003 | karthik@123 | Finance |

## 🗄️ Database Schema

- `employees` — All employee info, leave balances, project, manager, etc.
- `leave_requests` — All leave applications with type, date, reason, status
- `chat_history` — Full conversation history per employee

## 💬 Example Conversations

**Leave Application:**
> Me: I need leave on 19/05/2026
> Bot: What's the reason?
> Me: My grandfather passed away. It's an emergency.
> Bot: [Shows compassion, asks for leave type]
> Me: Annual Leave
> Bot: ✅ Annual Leave approved. Balance: 5 → 4 days. DB updated.

**Policy Query:**
> Me: What are the attendance rules?
> Bot: [Explains grace period, working hours, WFH policy, etc.]

## 🛠 Architecture
- **Backend:** Flask + SQLAlchemy + SQLite
- **AI:** LangChain + Ollama + Llama 3.2
- **Fallback:** Rule-based response engine (works without Ollama)
- **Frontend:** Pure HTML/CSS/JS with dark theme, glassmorphism UI

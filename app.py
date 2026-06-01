from flask import Flask, render_template, request, jsonify, session, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import json, re, hashlib

app = Flask(__name__)
app.secret_key = "hr_chatbot_secret_2024"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hr_chatbot.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# ═══ MODELS ══════════════════════════════════════════════════════

class Employee(db.Model):
    __tablename__ = 'employees'
    id                   = db.Column(db.Integer, primary_key=True)
    name                 = db.Column(db.String(100), nullable=False)
    employee_id          = db.Column(db.String(20), unique=True, nullable=False)
    password             = db.Column(db.String(100), nullable=False)
    department           = db.Column(db.String(100))
    project              = db.Column(db.String(200))
    manager_name         = db.Column(db.String(100))
    team_lead_name       = db.Column(db.String(100))
    annual_leave_balance = db.Column(db.Integer, default=12)
    annual_leave_taken   = db.Column(db.Integer, default=0)
    sick_leave_balance   = db.Column(db.Integer, default=6)
    sick_leave_taken     = db.Column(db.Integer, default=0)
    casual_leave_balance = db.Column(db.Integer, default=6)
    casual_leave_taken   = db.Column(db.Integer, default=0)
    lop_taken            = db.Column(db.Integer, default=0)
    joined_date          = db.Column(db.String(20))
    email                = db.Column(db.String(150))
    phone                = db.Column(db.String(20))
    designation          = db.Column(db.String(100))
    salary               = db.Column(db.Float, default=0.0)
    probation_end_date   = db.Column(db.String(20))
    is_admin             = db.Column(db.Boolean, default=False)
    theme_preference     = db.Column(db.String(20), default='dark')
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

class LeaveRequest(db.Model):
    __tablename__ = 'leave_requests'
    id           = db.Column(db.Integer, primary_key=True)
    employee_id  = db.Column(db.String(20), db.ForeignKey('employees.employee_id'))
    leave_type   = db.Column(db.String(50))
    leave_date   = db.Column(db.String(20))
    reason       = db.Column(db.Text)
    is_emergency = db.Column(db.Boolean, default=False)
    status       = db.Column(db.String(20), default='Approved')
    applied_on   = db.Column(db.DateTime, default=datetime.utcnow)

class ChatHistory(db.Model):
    __tablename__ = 'chat_history'
    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20))
    role        = db.Column(db.String(10))
    message     = db.Column(db.Text)
    timestamp   = db.Column(db.DateTime, default=datetime.utcnow)

class Notification(db.Model):
    __tablename__ = 'notifications'
    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20))
    message     = db.Column(db.Text)
    type        = db.Column(db.String(20), default='info')
    is_read     = db.Column(db.Boolean, default=False)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

class Feedback(db.Model):
    __tablename__ = 'feedback'
    id          = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.String(20))
    rating      = db.Column(db.Integer)
    comment     = db.Column(db.Text)
    created_at  = db.Column(db.DateTime, default=datetime.utcnow)

# ═══ HELPERS ══════════════════════════════════════════════════════

def parse_date(text):
    pats = [r'(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{2,4})',
            r'(\d{1,2})\s*(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\w*\s*(\d{2,4})']
    mo_map = {'jan':1,'feb':2,'mar':3,'apr':4,'may':5,'jun':6,
              'jul':7,'aug':8,'sep':9,'oct':10,'nov':11,'dec':12}
    for pat in pats:
        m = re.search(pat, text.lower())
        if m:
            try:
                g = m.groups()
                d_,mo,y = (int(g[0]),int(g[1]),int(g[2])) if g[1].isdigit() \
                          else (int(g[0]),mo_map[g[1][:3]],int(g[2]))
                if y < 100: y += 2000
                return date(y, mo, d_)
            except: pass
    return None

def days_until(d): return (d - date.today()).days
def fmt_date(d):   return d.strftime('%d %b %Y') if d else ''

BEREAVEMENT_KW = ['grandfather','grandmother','grandpa','grandma','father died','mother died',
    'dad died','mom died','parent died','sibling died','sister died','brother died',
    'passed away','demise','bereavement','funeral','death in family','lost my']
EMERGENCY_KW = BEREAVEMENT_KW + ['emergency','urgent','accident','hospital','icu','surgery','critical']

def is_bereavement(msg): return any(k in msg.lower() for k in BEREAVEMENT_KW)
def is_emergency(msg):   return any(k in msg.lower() for k in EMERGENCY_KW)

def emp_dict(emp):
    return {k: getattr(emp, k) for k in [
        'name','employee_id','department','designation','project',
        'manager_name','team_lead_name','annual_leave_balance','annual_leave_taken',
        'sick_leave_balance','sick_leave_taken','casual_leave_balance','casual_leave_taken',
        'lop_taken','joined_date','email','phone','probation_end_date','salary','is_admin']}

def add_notification(emp_id, message, type_='info'):
    db.session.add(Notification(employee_id=emp_id, message=message, type=type_))
    db.session.commit()

# ═══ LEAVE STATE MACHINE ══════════════════════════════════════════

def leave_machine(msg_raw, emp, pending):
    msg   = msg_raw.strip()
    name  = emp['name'].split()[0]
    stage = pending.get('stage','')

    if stage == 'awaiting_date':
        parsed = parse_date(msg)
        is_em  = is_emergency(msg) or pending.get('is_emergency', False)
        if not parsed:
            return None
        days = days_until(parsed)
        if days < 0:
            return (f"**{fmt_date(parsed)}** is in the past. Please give a future date, {name}.",
                    {**pending, 'stage':'awaiting_date'}, None)
        date_str  = parsed.strftime('%d/%m/%Y')
        date_nice = fmt_date(parsed)
        if is_em:
            return (f"Leave for **{date_nice}** noted. 💙\n\nPlease contact right now:\n"
                    f"• Manager: **{emp['manager_name']}**\n• Team Lead: **{emp['team_lead_name']}**\n\n"
                    f"Choose your leave type below:",
                    {'stage':'awaiting_type','date':date_str,'reason':pending.get('reason','Emergency'),'is_emergency':True}, None)
        notice = ''
        if 0 <= days < 7:
            notice = (f"\n\n⚠️ Only **{days} day{'s' if days!=1 else ''}** away — "
                      f"**{emp['manager_name']}**'s explicit approval is required.")
        return (f"Got it — leave for **{date_nice}**.{notice}\n\n"
                f"Could you briefly share the **reason** for your leave?\n"
                f"_(This helps your manager review the request)_",
                {'stage':'awaiting_reason','date':date_str,'is_emergency':False}, None)

    if stage == 'awaiting_reason':
        raw = msg.strip()
        date_str  = pending.get('date','')
        parsed    = parse_date(date_str)
        date_nice = fmt_date(parsed) if parsed else date_str
        days      = days_until(parsed) if parsed else 99
        is_em     = is_emergency(raw) or pending.get('is_emergency', False)
        is_berv   = is_bereavement(raw)
        trivial   = ['no reason','none','nothing','na','n/a','idk','just want','nope']
        reason    = 'Personal reason' if (not raw or len(raw)<2 or any(t in raw.lower() for t in trivial)) else raw

        if is_berv:
            reply = (f"I'm so sorry for your loss, {name}. 💙\n\nPlease take all the time you need.\n\n"
                     f"This qualifies as **Bereavement Leave**. When you can, please inform "
                     f"**{emp['manager_name']}**.\n\nChoose your leave type for **{date_nice}**:")
        elif is_em:
            reply = (f"I hope things improve soon, {name}. Stay strong. 💙\n\n"
                     f"Emergency leave is approved. Please inform **{emp['manager_name']}** "
                     f"and **{emp['team_lead_name']}** as soon as possible.\n\nChoose leave type for **{date_nice}**:")
        elif days < 7:
            reply = (f"Thanks for sharing that, {name}.\n\n"
                     f"Since this is short notice, **{emp['manager_name']}** will need to "
                     f"manually approve this request.\n\nSelect your leave type for **{date_nice}**:")
        else:
            reply = (f"Got it, {name}! Reason noted. Almost done — select your **leave type** for **{date_nice}**:")

        return (reply, {'stage':'awaiting_type','date':date_str,'reason':reason,'is_emergency':is_em}, None)

    if stage == 'awaiting_type':
        ml = msg.lower()
        date_str  = pending.get('date','')
        reason    = pending.get('reason','Personal reason')
        is_em     = pending.get('is_emergency', False)
        parsed    = parse_date(date_str)
        date_nice = fmt_date(parsed) if parsed else date_str
        if 'annual' in ml:    chosen = 'annual'
        elif 'sick' in ml:    chosen = 'sick'
        elif 'casual' in ml:  chosen = 'casual'
        elif 'lop' in ml or 'loss' in ml: chosen = 'lop'
        else:
            return ("Please tap one of the options: **Annual**, **Sick**, **Casual**, or **LOP**.", pending, None)
        bal_map   = {'annual':emp['annual_leave_balance'],'sick':emp['sick_leave_balance'],
                     'casual':emp['casual_leave_balance'],'lop':None}
        label_map = {'annual':'Annual Leave','sick':'Sick Leave','casual':'Casual Leave','lop':'Loss of Pay (LOP)'}
        bal = bal_map[chosen]
        if chosen != 'lop' and bal == 0:
            others = [v for k,v in label_map.items() if k != chosen and k != 'lop']
            return (f"Sorry, **0 {label_map[chosen]}** days left. Choose: {', '.join(others)} or LOP.", pending, None)
        new_bal = (bal - 1) if chosen != 'lop' else emp['lop_taken'] + 1
        approval = (f"📧 Email **{emp['manager_name']}** and **{emp['team_lead_name']}**." if is_em
                    else f"📧 Email your team lead **{emp['team_lead_name']}** with this request.")
        msg_out = (f"**{label_map[chosen]} approved** for **{date_nice}**! ✅\n\n"
                   f"📝 Reason: {reason}\n"
                   + (f"📊 Balance: **{bal} → {new_bal}** day{'s' if new_bal!=1 else ''} remaining\n\n"
                      if chosen != 'lop' else f"⚠️ This day will be deducted from your salary.\n\n")
                   + approval)
        return (msg_out, None, {'type':chosen,'date':date_str,'reason':reason,'is_emergency':is_em})

    return None

# ═══ GENERAL RESPONSES ════════════════════════════════════════════

def general_response(msg, emp):
    m = msg.lower(); name = emp['name'].split()[0]
    if any(w in m for w in ['balance','how many','leave left','days left','remaining','__leave_balance__']):
        al,sl,cl,lp = emp['annual_leave_balance'],emp['sick_leave_balance'],emp['casual_leave_balance'],emp['lop_taken']
        return (f"Here's your current leave balance, {name}:\n\n"
                f"🟢 **Annual Leave:** {al} day{'s' if al!=1 else ''} remaining ({emp['annual_leave_taken']} used)\n"
                f"🔵 **Sick Leave:** {sl} day{'s' if sl!=1 else ''} remaining ({emp['sick_leave_taken']} used)\n"
                f"🟡 **Casual Leave:** {cl} day{'s' if cl!=1 else ''} remaining ({emp['casual_leave_taken']} used)\n"
                f"🔴 **LOP Taken:** {lp} day{'s' if lp!=1 else ''}\n\n"
                f"Total available: **{al+sl+cl} paid days** remaining this year.")
    if any(w in m for w in ['attendance','timing','office','wfh','work from home','late','grace','punch','biometric','__attendance__']):
        return ("**Attendance Policy:**\n\n"
                "• Working hours: **9:00 AM – 6:00 PM**, Monday to Saturday\n"
                "• 2nd and 4th Saturdays are holidays\n"
                "• Grace period: **15 minutes** — beyond = half day marked\n"
                "• WFH: manager approval **24 hours** in advance required\n"
                "• Missed biometric punch → regularise within **3 working days**\n"
                "• 3 unexplained absences = warning letter")
    if any(w in m for w in ['benefit','insurance','pf','provident','bonus','birthday','referral','allowance','__benefits__']):
        return ("**Your Employee Benefits:**\n\n"
                "• 🏥 Health Insurance: ₹3 Lakhs (employee + family)\n"
                "• 💰 PF: 12% employee + 12% employer contribution\n"
                "• 🎉 Annual Bonus: Performance-based, released in April\n"
                "• 🎂 Birthday Leave: 1 paid day on your birthday\n"
                "• 👥 Referral Bonus: ₹10,000 (after 6 months retention)\n"
                "• 📱 Mobile: ₹500/month (senior roles)\n"
                "• 🌐 Internet: ₹1,000/month (WFH-approved roles)")
    if any(w in m for w in ['encash','encashment','gratuity','settlement','fnf','final','__encashment__']):
        return ("**Leave Encashment & Settlement:**\n\n"
                "• Formula: **(Basic Salary ÷ 26) × Days**\n"
                "• AL above **30 accumulated days** can be encashed at year-end\n"
                "• Full & final settlement within **45 days** of last working day\n"
                "• Gratuity after **5 years** continuous service\n"
                "• Gratuity formula: **(15 × Last Salary × Years) ÷ 26**\n"
                "• All encashment amounts are taxable per income slab")
    if any(w in m for w in ['probation','confirm','permanent','__probation__']):
        return (f"**Probation Policy:**\n\n"
                f"• Duration: **6 months** from joining date\n"
                f"• Your probation end date: **{emp['probation_end_date']}**\n"
                f"• During probation: only **Sick** and **Casual Leave** available\n"
                f"• Annual Leave is **not available** during probation\n"
                f"• Notice period: **1 month**\n"
                f"• Extension: up to **3 months** based on performance")
    if any(w in m for w in ['payslip','salary','payroll','ctc','increment','appraisal','__payslip__']):
        return ("**Payroll & Payslip:**\n\n"
                "• Salary credited on the **1st of every month**\n"
                "• Payslip available on HR portal by the **5th**\n"
                "• Appraisal cycle: **April to March** annually\n"
                "• Ratings and increments released in **April**\n"
                "• For duplicate payslip, raise a request on the HR portal")
    if any(w in m for w in ['resign','notice','quit','exit','__resign__']):
        return ("**Resignation & Exit:**\n\n"
                "• Notice period: **60 days**\n"
                "• Submit letter to: **HR + Direct Manager**\n"
                "• Exit clearance: IT, Admin, Finance, HR\n"
                "• Full & final settlement within **45 days**\n"
                "• During probation: only **1 month** notice required")
    if any(w in m for w in ['hi','hello','hey','morning','afternoon','evening']):
        return f"Hi {name}! 👋 How can I help you today?"
    if any(w in m for w in ['who are you','what are you','your name','hrbot','bot']):
        return (f"I'm **HRBot** 🤖 — your AI-powered HR assistant at PeopleFirst!\n\n"
                f"I can help you with:\n"
                f"• 📅 Leave applications and balance\n• ⏰ Attendance and WFH policy\n"
                f"• 💰 Payroll and payslip info\n• 🎁 Employee benefits\n"
                f"• 📋 Probation and policies\n• 💵 Encashment and gratuity\n\n"
                f"I'm powered by Llama 3.2 + LangChain. What can I help you with today?")
    return (f"I can help you with, {name}:\n\n"
            f"• 📅 Leave application & balance\n• ⏰ Attendance & WFH policy\n"
            f"• 💰 Payroll & payslip\n• 🎁 Employee benefits\n"
            f"• 📋 Probation policy\n• 💵 Encashment & gratuity\n"
            f"• 📤 Resignation process\n\nWhat would you like to know?")

def try_ollama(msg, emp):
    leave_kw = ['leave','day off','time off','absent','vacation','annual','sick','casual','lop']
    if any(k in msg.lower() for k in leave_kw): return None
    try:
        from langchain_ollama import OllamaLLM
        llm = OllamaLLM(model="llama3.2", base_url="http://localhost:11434", timeout=6)
        prompt = (f"You are HRBot. Answer directly. No greeting. Max 5 lines.\n"
                  f"Employee: {emp['name']}, {emp['designation']}, {emp['department']}\n"
                  f"Question: {msg}\nAnswer:")
        resp = llm.invoke(prompt).strip()
        bad = ['welcome','how can i assist','what can i help']
        return None if any(b in resp.lower()[:100] for b in bad) else resp
    except: return None

# ═══ ROUTER ═══════════════════════════════════════════════════════

LEAVE_STARTERS = ['i want leave','i need leave','apply for leave','apply leave','request leave',
    'take leave','need a day off','want a day off','i want to take','can i take leave']
GENERAL_ESCAPE = ['attendance','benefit','payslip','salary','probation','encash','gratuity',
    'resign','insurance','pf','bonus','wfh','appraisal','policy','leave balance',
    'check balance','how many','days left','my balance']

def route(msg_raw, emp, pending):
    msg = msg_raw.strip(); mlo = msg.lower()

    # P0: Intent signals
    if msg.startswith('__') and msg.endswith('__'):
        sig = msg; name = emp['name'].split()[0]
        if sig == '__APPLY_LEAVE__':
            return (f"Of course, {name}! Which **date** do you need off?\n_(e.g. 25/06/2026)_\n\n"
                    f"📌 Planned leave needs **7 days advance notice**.",
                    {'stage':'awaiting_date','is_emergency':False}, None)
        if sig == '__EMERGENCY_LEAVE__':
            return (f"I'm here to help, {name}. 💙\n\nEmergency leave needs **no advance notice**.\n"
                    f"Please **call/email right now**:\n• Manager: **{emp['manager_name']}**\n"
                    f"• Team Lead: **{emp['team_lead_name']}**\n\nWhich **date(s)** do you need off?",
                    {'stage':'awaiting_date','is_emergency':True}, None)
        sig_kw = {'__LEAVE_BALANCE__':'balance','__ATTENDANCE__':'attendance','__BENEFITS__':'benefit',
                  '__ENCASHMENT__':'encashment','__PROBATION__':'probation','__PAYSLIP__':'payslip','__RESIGN__':'resign'}
        kw = sig_kw.get(sig, '')
        return (general_response(kw or msg, emp), None, None)

    # P1: Active leave flow
    if pending and pending.get('stage') in ('awaiting_date','awaiting_reason','awaiting_type'):
        stage = pending['stage']
        if stage == 'awaiting_date':
            if any(w in mlo for w in GENERAL_ESCAPE) and not parse_date(msg):
                return (general_response(msg,emp)+f"\n\n---\n💬 _Back to your leave — which date do you need off?_", pending, None)
        if stage == 'awaiting_reason':
            return leave_machine(msg, emp, pending)
        result = leave_machine(msg, emp, pending)
        if result: return result
        if stage == 'awaiting_type':
            return ("Please choose: **Annual Leave**, **Sick Leave**, **Casual Leave**, or **LOP**.", pending, None)
        return (f"I need a date — please share it like **25/06/2026**.", pending, None)

    # P2: Fresh leave trigger
    if any(t in mlo for t in LEAVE_STARTERS):
        parsed = parse_date(msg); em = is_emergency(msg); name = emp['name'].split()[0]
        if parsed: return leave_machine(msg, emp, {'stage':'awaiting_date','is_emergency':em})
        return (f"Of course, {name}! Which **date** do you need off? _(e.g. 25/06/2026)_\n\n"
                f"📌 Planned leave needs **7 days advance notice**.",
                {'stage':'awaiting_date','is_emergency':em}, None)

    # P3: General
    llm = try_ollama(msg, emp)
    if llm: return (llm, None, None)
    return (general_response(msg, emp), None, None)

# ═══ FLASK ROUTES ═════════════════════════════════════════════════

@app.route('/')
def index():
    return redirect(url_for('chat') if 'employee_id' in session else url_for('login'))

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        data = request.get_json()
        emp  = Employee.query.filter_by(employee_id=data.get('employee_id','').strip()).first()
        if emp and emp.password == data.get('password','').strip():
            session.permanent = True
            session['employee_id'] = emp.employee_id
            return jsonify({'success':True,'name':emp.name,'is_admin':emp.is_admin})
        return jsonify({'success':False,'message':'Invalid Employee ID or Password'})
    return render_template('login.html')

@app.route('/chat')
def chat():
    if 'employee_id' not in session: return redirect(url_for('login'))
    emp = Employee.query.filter_by(employee_id=session['employee_id']).first()
    if not emp: return redirect(url_for('login'))
    return render_template('chat.html', employee=emp)

@app.route('/dashboard')
def dashboard():
    if 'employee_id' not in session: return redirect(url_for('login'))
    emp = Employee.query.filter_by(employee_id=session['employee_id']).first()
    if not emp: return redirect(url_for('login'))
    return render_template('dashboard.html', employee=emp)

@app.route('/api/chat', methods=['POST'])
def api_chat():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}), 401
    data    = request.get_json()
    msg_raw = data.get('message','').strip()
    pending = data.get('pending_action')
    if not msg_raw: return jsonify({'error':'Empty message'}), 400
    emp = Employee.query.filter_by(employee_id=session['employee_id']).first()
    if not emp: return jsonify({'error':'Not found'}), 404
    e = emp_dict(emp)
    is_signal = msg_raw.startswith('__') and msg_raw.endswith('__')
    if not is_signal:
        db.session.add(ChatHistory(employee_id=emp.employee_id, role='user', message=msg_raw))
        db.session.commit()
    bot_text, new_pending, leave_action = route(msg_raw, e, pending)
    db_updated = False; leave_result = None
    if leave_action:
        ltype,ldate,reason,is_em = leave_action['type'],leave_action['date'],leave_action['reason'],leave_action['is_emergency']
        labels = {'annual':'Annual Leave','sick':'Sick Leave','casual':'Casual Leave','lop':'Loss of Pay (LOP)'}
        if ltype=='annual' and emp.annual_leave_balance>0:
            old=emp.annual_leave_balance; emp.annual_leave_balance-=1; emp.annual_leave_taken+=1
            leave_result={'type':labels['annual'],'old':old,'new':emp.annual_leave_balance}; db_updated=True
        elif ltype=='sick' and emp.sick_leave_balance>0:
            old=emp.sick_leave_balance; emp.sick_leave_balance-=1; emp.sick_leave_taken+=1
            leave_result={'type':labels['sick'],'old':old,'new':emp.sick_leave_balance}; db_updated=True
        elif ltype=='casual' and emp.casual_leave_balance>0:
            old=emp.casual_leave_balance; emp.casual_leave_balance-=1; emp.casual_leave_taken+=1
            leave_result={'type':labels['casual'],'old':old,'new':emp.casual_leave_balance}; db_updated=True
        elif ltype=='lop':
            old=emp.lop_taken; emp.lop_taken+=1
            leave_result={'type':labels['lop'],'old':old,'new':emp.lop_taken}; db_updated=True
        if db_updated:
            db.session.add(LeaveRequest(employee_id=emp.employee_id,leave_type=ltype,leave_date=ldate,reason=reason,is_emergency=is_em,status='Approved'))
            add_notification(emp.employee_id, f"Leave approved: {labels.get(ltype,ltype)} on {ldate}", 'success')
            db.session.commit()
    db.session.add(ChatHistory(employee_id=emp.employee_id, role='bot', message=bot_text))
    db.session.commit()
    updated = {k:getattr(emp,k) for k in ['annual_leave_balance','annual_leave_taken','sick_leave_balance',
        'sick_leave_taken','casual_leave_balance','casual_leave_taken','lop_taken']} if db_updated else None
    return jsonify({'response':bot_text,'db_updated':db_updated,'leave_result':leave_result,'updated_employee':updated,'pending_action':new_pending})

@app.route('/api/leave-history')
def api_leave_history():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    rows = LeaveRequest.query.filter_by(employee_id=session['employee_id']).order_by(LeaveRequest.applied_on.desc()).limit(20).all()
    return jsonify([{'leave_type':r.leave_type,'leave_date':r.leave_date,'reason':r.reason,
        'is_emergency':r.is_emergency,'status':r.status,'applied_on':r.applied_on.strftime('%d %b %Y')} for r in rows])

@app.route('/api/stats')
def api_stats():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    eid = session['employee_id']
    emp = Employee.query.filter_by(employee_id=eid).first()
    if not emp: return jsonify({'error':'Not found'}),404
    total_leaves = LeaveRequest.query.filter_by(employee_id=eid).count()
    total_chats  = ChatHistory.query.filter_by(employee_id=eid, role='user').count()
    joined = parse_date(emp.joined_date) if emp.joined_date else None
    days_at = (date.today()-joined).days if joined else 0
    # Monthly leave breakdown for chart
    monthly = {}
    rows = LeaveRequest.query.filter_by(employee_id=eid).all()
    for r in rows:
        try:
            mo = datetime.strptime(r.applied_on.strftime('%Y-%m'),'%Y-%m').strftime('%b %Y')
            monthly[mo] = monthly.get(mo,0)+1
        except: pass
    return jsonify({'total_leaves':total_leaves,'total_chats':total_chats,'days_at_company':days_at,
        'monthly_leaves':monthly,'total_balance':emp.annual_leave_balance+emp.sick_leave_balance+emp.casual_leave_balance})

@app.route('/api/dashboard')
def api_dashboard():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    emp = Employee.query.filter_by(employee_id=session['employee_id']).first()
    if not emp: return jsonify({'error':'Not found'}),404
    eid = emp.employee_id
    leaves = LeaveRequest.query.filter_by(employee_id=eid).all()
    by_type = {}
    for l in leaves:
        by_type[l.leave_type] = by_type.get(l.leave_type,0)+1
    monthly = {}
    for l in leaves:
        mo = l.applied_on.strftime('%b')
        monthly[mo] = monthly.get(mo,0)+1
    return jsonify({
        'employee': emp_dict(emp),
        'total_leaves': len(leaves),
        'by_type': by_type,
        'monthly': monthly,
        'recent_leaves': [{'leave_type':l.leave_type,'leave_date':l.leave_date,'reason':l.reason,'status':l.status,'applied_on':l.applied_on.strftime('%d %b %Y')} for l in leaves[:5]],
        'upcoming_events': get_upcoming_events(emp),
    })

def get_upcoming_events(emp):
    events = []
    today = date.today()
    # Birthday (simulate)
    events.append({'icon':'🎂','text':'HR Portal Annual Review — June 2026','date':'01 Jun 2026'})
    events.append({'icon':'📊','text':'Performance Appraisal Cycle Opens','date':'01 Apr 2026'})
    if emp.probation_end_date:
        pd = parse_date(emp.probation_end_date)
        if pd and pd >= today:
            events.append({'icon':'🎓','text':f'Probation ends — {fmt_date(pd)}','date':fmt_date(pd)})
    return events[:3]

@app.route('/api/notifications')
def api_notifications():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    rows = Notification.query.filter_by(employee_id=session['employee_id'],is_read=False).order_by(Notification.created_at.desc()).limit(10).all()
    return jsonify([{'id':r.id,'message':r.message,'type':r.type,'created_at':r.created_at.strftime('%d %b, %H:%M')} for r in rows])

@app.route('/api/notifications/read', methods=['POST'])
def api_notif_read():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    Notification.query.filter_by(employee_id=session['employee_id'],is_read=False).update({'is_read':True})
    db.session.commit()
    return jsonify({'ok':True})

@app.route('/api/feedback', methods=['POST'])
def api_feedback():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    data = request.get_json()
    db.session.add(Feedback(employee_id=session['employee_id'],rating=data.get('rating',5),comment=data.get('comment','')))
    db.session.commit()
    return jsonify({'ok':True})

@app.route('/api/employee')
def api_employee():
    if 'employee_id' not in session: return jsonify({'error':'Not logged in'}),401
    emp = Employee.query.filter_by(employee_id=session['employee_id']).first()
    if not emp: return jsonify({'error':'Not found'}),404
    return jsonify(emp_dict(emp))

@app.route('/logout')
def logout():
    session.clear()
    resp = make_response(redirect(url_for('login')))
    resp.set_cookie('session','',expires=0,max_age=0,path='/')
    resp.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    resp.headers['Pragma'] = 'no-cache'
    resp.headers['Expires'] = '0'
    return resp

# ═══ INIT DB ══════════════════════════════════════════════════════

def init_db():
    with app.app_context():
        db.drop_all(); db.create_all()
        emps = [
            Employee(name='Arun Kumar',employee_id='EMP001',password='password123',department='Engineering',
                designation='Software Engineer',project='Project Phoenix',manager_name='Rajesh Sharma',
                team_lead_name='Priya Menon',annual_leave_balance=5,annual_leave_taken=7,
                sick_leave_balance=2,sick_leave_taken=4,casual_leave_balance=3,casual_leave_taken=3,
                lop_taken=0,joined_date='15/01/2023',email='arun.kumar@company.com',
                phone='+91 9876543210',probation_end_date='15/07/2023',salary=65000.0),
            Employee(name='Priya Lakshmi',employee_id='EMP002',password='priya2024',department='HR',
                designation='HR Executive',project='HR Transformation',manager_name='Sunita Rao',
                team_lead_name='Vikram Singh',annual_leave_balance=10,annual_leave_taken=2,
                sick_leave_balance=5,sick_leave_taken=1,casual_leave_balance=4,casual_leave_taken=2,
                lop_taken=0,joined_date='01/03/2024',email='priya.l@company.com',
                phone='+91 9123456780',probation_end_date='01/09/2024',salary=45000.0,is_admin=True),
            Employee(name='Karthik Rajan',employee_id='EMP003',password='karthik@123',department='Finance',
                designation='Senior Analyst',project='Budget Optimization',manager_name='Deepa Nair',
                team_lead_name='Suresh Kumar',annual_leave_balance=8,annual_leave_taken=4,
                sick_leave_balance=6,sick_leave_taken=0,casual_leave_balance=5,casual_leave_taken=1,
                lop_taken=1,joined_date='10/06/2022',email='karthik.r@company.com',
                phone='+91 9988776655',probation_end_date='10/12/2022',salary=80000.0),
        ]
        for e in emps: db.session.add(e)
        db.session.commit()
        # Seed some leave history for charts
        seed_leave = [
            ('EMP001','annual','15/03/2026','Team trip',False),
            ('EMP001','sick','02/04/2026','Fever',False),
            ('EMP003','annual','10/03/2026','Family function',False),
            ('EMP003','casual','18/04/2026','Personal work',False),
        ]
        for eid,lt,ld,reason,em in seed_leave:
            db.session.add(LeaveRequest(employee_id=eid,leave_type=lt,leave_date=ld,reason=reason,is_emergency=em,status='Approved'))
        db.session.commit()
        print("✅ DB seeded — 3 employees, leave history added")

if __name__ == '__main__':
    init_db()
    print("🚀 HRBot → http://localhost:5000")
    app.run(debug=True, port=5000)

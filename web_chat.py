"""Web chat — full-featured chat UI + API (files, voice, login, AI answers)."""
import asyncio
import base64
import json
import logging
import random
import time
import uuid

from google.genai import types

from config import client, db, MODEL_NAME
from database import (
    get_knowledge_base_text, get_student_by_chat_id, get_instructor_by_chat_id,
    get_chat_language, set_chat_language,
)
from gemini_services import (
    call_gemini_with_retry, generate_answer, detect_text_language,
)
from utils import send_otp_email, extract_pdf_text

_sessions = {}
_pending_otp = {}
SESSION_TTL = 3600


def _get_session(sid):
    now = time.time()
    s = _sessions.get(sid)
    if s and now - s["last"] < SESSION_TTL:
        s["last"] = now
        return s
    _sessions.pop(sid, None)
    return None


def _ensure_session(sid):
    s = _get_session(sid)
    if s:
        return s
    sid = uuid.uuid4().hex[:16]
    _sessions[sid] = {"last": time.time()}
    return _sessions[sid]


# ─── API handlers ───────────────────────────────────────────────

def handle_chat(body):
    msg = (body.get("message") or "").strip()
    sid = body.get("session_id") or ""
    _ensure_session(sid)
    if not msg:
        return {"reply": "وضّح سؤالك أكثر؟", "session_id": sid}
    lang = detect_text_language(msg)
    s = _get_session(sid) or {}
    chat_id = s.get("chat_id", 0)
    try:
        reply = asyncio.run(generate_answer(msg, chat_id=chat_id, language=lang))
    except Exception as e:
        logging.error("Web chat error: %s", e)
        reply = "حصل خطأ تقني. جرب تاني بعد شوية."
    return {"reply": reply, "session_id": sid}

def handle_upload(body):
    try:
        file_b64 = body.get("file_data") or ""
        action = body.get("action") or ""
        name = body.get("filename") or "file"
        mime = body.get("mime") or "application/octet-stream"
        sid = body.get("session_id") or ""
        data = base64.b64decode(file_b64)
        if len(data) > 20_000_000:
            return {"reply": "الملف كبير جداً (أكبر من 20MB)."}
        if not data:
            return {"reply": "الملف فاضي."}

        if not action:
            s = _get_session(sid) or _ensure_session(sid)
            s["pending_file"] = {"data": file_b64, "name": name, "mime": mime}
            return {
                "reply": f"تم استلام الملف ({name}) ✅ اختر:",
                "actions": True,
            }

        s = _get_session(sid) or _ensure_session(sid)
        pf = s.get("pending_file") if not file_b64 else None

        if pf:
            raw = base64.b64decode(pf["data"])
            pmime = pf["mime"]
        else:
            raw = data
            pmime = mime

        if action == "summarize":
            prompt = "لخص محتوى هذا الملف في نقاط واضحة ومرتبة. اكتب الملخص بنفس لغة الملف الأصلية."
        elif action == "summarize_pdf":
            prompt = "لخص محتوى هذا الملف في نقاط واضحة ومرتبة. اكتب الملخص بنفس لغة الملف الأصلية."
        elif action == "translate":
            prompt = ("اكتشف لغة محتوى هذا الملف ثم ترجمه إلى اللغة المقابلة: "
                      "إن كان بالعربية ترجمه إلى الإنجليزية، وإن كان بالإنجليزية "
                      "ترجمه إلى العربية، مع الحفاظ على المعنى والمصطلحات.")
        elif action == "translate_pdf":
            prompt = ("اكتشف لغة محتوى هذا الملف ثم ترجمه إلى اللغة المقابلة: "
                      "إن كان بالعربية ترجمه إلى الإنجليزية، وإن كان بالإنجليزية "
                      "ترجمه إلى العربية، مع الحفاظ على المعنى والمصطلحات.")
        else:
            prompt = "لخص محتوى هذا الملف في نقاط واضحة ومرتبة. اكتب الملخص بنفس لغة الملف الأصلية."

        part = types.Part.from_bytes(data=raw, mime_type=pmime)
        response = asyncio.run(
            call_gemini_with_retry(
                client.models.generate_content,
                model=MODEL_NAME,
                contents=[prompt, part],
            )
        )
        result = (response.text or "").strip() or "تعذرت معالجة الملف."

        if action in ("summarize_pdf", "translate_pdf"):
            try:
                from pdf_utils import text_to_pdf_bytes
                title = "ترجمة الملف" if "translate" in action else "ملخص الملف"
                pdf_bytes = asyncio.run(
                    asyncio.to_thread(text_to_pdf_bytes, result, title)
                )
                import io
                pdf_b64 = base64.b64encode(pdf_bytes).decode()
                s.pop("pending_file", None)
                return {"reply": result[:4000], "pdf": pdf_b64, "pdf_name": f"{title}.pdf"}
            except Exception as e:
                logging.error("PDF generation error: %s", e)
                return {"reply": result[:4000]}

        s.pop("pending_file", None)
        return {"reply": result[:4000]}
    except Exception as e:
        logging.error("Upload error: %s", e)
        return {"reply": "تعذرت معالجة الملف. حاول تاني."}


def handle_voice(body):
    try:
        audio_b64 = body.get("audio_data") or ""
        sid = body.get("session_id") or ""
        data = base64.b64decode(audio_b64)
        if not data:
            return {"reply": "الملف الصوتي فاضي."}
        part = types.Part.from_bytes(data=data, mime_type="audio/webm")
        stt = asyncio.run(
            call_gemini_with_retry(
                client.models.generate_content,
                model=MODEL_NAME,
                contents=["استخرج النص المنطوق فقط من هذا التسجيل الصوتي.", part],
            )
        )
        text = (stt.text or "").strip()
        if not text:
            return {"reply": "ما قدرت أسمع الكلام جيداً. جرب تاني.", "transcribed": ""}
        s = _get_session(sid) or {}
        chat_id = s.get("chat_id", 0)
        lang = detect_text_language(text)
        reply = asyncio.run(generate_answer(text, chat_id=chat_id, language=lang))
        return {"reply": reply, "transcribed": text}
    except Exception as e:
        logging.error("Voice error: %s", e)
        return {"reply": "تعذرت معالجة الرسالة الصوتية."}


def handle_login_start(body):
    user_id = (body.get("user_id") or "").strip()
    sid = body.get("session_id") or ""
    if not user_id:
        return {"reply": "اكتب رقمك الجامعي أو معرف الدكتور.", "step": "ask_id"}
    for collection, role in (("students", "student"), ("instructors", "instructor")):
        doc = db.collection(collection).document(user_id).get()
        if doc.exists:
            data = doc.to_dict()
            break
    else:
        return {"reply": "الرقم غير موجود في قاعدة البيانات.", "step": "ask_id"}
    email = data.get("email", "")
    if not email:
        return {"reply": "لا يوجد بريد إلكتروني لهذا الحساب.", "step": "ask_id"}
    code = str(random.randint(100000, 999999))
    _pending_otp[sid] = {
        "code": code, "user_id": user_id, "role": role,
        "email": email, "expires": time.time() + 300,
    }
    try:
        asyncio.run(send_otp_email(email, code))
    except Exception:
        logging.exception("OTP email failed")
    return {
        "reply": f"تم إرسال رمز التحقق على بريدك ({email[:3]}***{email[email.rfind('@'):]})\nاكتب الرمز هنا:",
        "step": "ask_otp",
    }


def handle_login_verify(body):
    code = (body.get("code") or "").strip()
    sid = body.get("session_id") or ""
    pending = _pending_otp.get(sid)
    if not pending or time.time() > pending["expires"]:
        _pending_otp.pop(sid, None)
        return {"reply": "انتهت صلاحية الرمز. ابدأ تسجيل الدخول من جديد.", "step": "done"}
    if code != pending["code"]:
        return {"reply": "الرمز غير صحيح. حاول مرة أخرى:", "step": "ask_otp"}
    collection = "students" if pending["role"] == "student" else "instructors"
    db.collection(collection).document(pending["user_id"]).update({
        "chat_id": sid, "last_active": time.time(),
    })
    _pending_otp.pop(sid, None)
    s = _get_session(sid) or {}
    s["chat_id"] = int(pending["user_id"])
    s["role"] = pending["role"]
    return {"reply": "تم تسجيل الدخول بنجاح! ✅", "step": "done"}


def handle_logout(body):
    sid = body.get("session_id") or ""
    s = _get_session(sid)
    if not s or not s.get("chat_id"):
        return {"reply": "أنت غير مسجل دخول."}
    for collection in ("students", "instructors"):
        db.collection(collection).document(str(s["chat_id"])).update({
            "chat_id": None, "last_active": None,
        })
    s.pop("chat_id", None)
    s.pop("role", None)
    return {"reply": "تم تسجيل الخروج بنجاح! 👋"}


# ─── HTML ───────────────────────────────────────────────────────

CHAT_FULL_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>UST Smart Assistant</title>
<link rel="icon" href="https://ust.edu.sd/public/fornt/img/678.png">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.15.4/css/all.css"/>
<style>
:root{--b:#000067;--bl:#1a1a8a;--r:#cc0812;--g:#f0f2f5;--w:#fff}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Poppins','Cairo',sans-serif;background:var(--g);min-height:100vh;display:flex;flex-direction:column}
a{text-decoration:none}

/* topbar */
.topbar{background:var(--b);color:#fff;padding:8px 24px;display:flex;justify-content:space-between;font-size:12px}
.topbar a{color:#fff;opacity:.85}.topbar a:hover{opacity:1}
.topbar-r{display:flex;gap:16px;align-items:center}

/* navbar */
.navbar{background:#fff;padding:12px 24px;display:flex;align-items:center;justify-content:space-between;box-shadow:0 2px 8px rgba(0,0,0,.06);position:sticky;top:0;z-index:100}
.brand{display:flex;align-items:center;gap:12px}
.brand img{height:48px}
.brand-t{color:var(--b);font-weight:700;font-size:16px;line-height:1.3}
.brand-t small{display:block;color:#666;font-weight:400;font-size:11px}
.nav-links{display:flex;gap:20px}
.nav-links a{color:#333;font-size:13px;font-weight:500}.nav-links a:hover{color:var(--r)}

/* hero */
.hero{background:linear-gradient(135deg,var(--b),var(--bl) 60%,#2a2a9a);color:#fff;padding:40px 24px 28px;text-align:center}
.hero h1{font-size:26px;font-weight:700;margin-bottom:6px}
.hero p{font-size:14px;opacity:.85;max-width:560px;margin:0 auto 16px;line-height:1.6}
.hero .badge{background:var(--r);padding:6px 18px;border-radius:20px;font-size:12px;font-weight:600}

/* chat container */
.chat-main{flex:1;display:flex;justify-content:center;padding:20px 16px 36px}
.cc{width:100%;max-width:720px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,103,.1);display:flex;flex-direction:column;overflow:hidden;height:calc(100vh - 250px);min-height:460px}

/* chat header */
.ch{background:linear-gradient(135deg,var(--b),var(--bl));color:#fff;padding:14px 20px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.ch .av{width:42px;height:42px;border-radius:50%;background:rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0}
.ch .av img{width:30px;height:30px}
.ch .txt{flex:1}.ch .txt h3{font-size:14px;font-weight:600}.ch .txt p{font-size:11px;opacity:.75;margin:1px 0 0}
.ch .dot{width:8px;height:8px;border-radius:50%;background:#4caf50;animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}

/* user bar */
.user-bar{padding:6px 20px;background:#e8f0fe;display:flex;align-items:center;justify-content:space-between;font-size:12px;color:var(--b);flex-shrink:0}
.user-bar .login-btn{background:var(--r);color:#fff;border:none;padding:4px 14px;border-radius:14px;font-size:11px;cursor:pointer;font-family:inherit}
.user-bar .logout-btn{background:#666;color:#fff;border:none;padding:4px 14px;border-radius:14px;font-size:11px;cursor:pointer;font-family:inherit}

/* messages */
.msgs{flex:1;overflow-y:auto;padding:16px 20px;display:flex;flex-direction:column;gap:10px;background:#f7f8fa}
.msgs::-webkit-scrollbar{width:5px}.msgs::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}
.msg{max-width:82%;padding:12px 16px;font-size:14px;line-height:1.7;word-wrap:break-word;animation:fi .25s ease}
.msg.bot{background:#fff;color:#222;align-self:flex-start;border-radius:4px 16px 16px 16px;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.msg.user{background:var(--b);color:#fff;align-self:flex-end;border-radius:16px 4px 16px 16px}
.msg.file-info{background:#e3f2fd;color:#1565c0;align-self:center;font-size:12px;border-radius:8px;padding:8px 14px;text-align:center}
.msg.voice-info{background:#f3e5f5;color:#7b1fa2;align-self:center;font-size:12px;border-radius:8px;padding:8px 14px;text-align:center}
@keyframes fi{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* typing */
.typing{display:none;padding:10px 16px;background:#fff;border-radius:4px 16px 16px 16px;align-self:flex-start;box-shadow:0 1px 4px rgba(0,0,0,.06)}
.typing span{display:inline-block;width:7px;height:7px;border-radius:50%;background:#aaa;margin:0 2px;animation:bounce .6s infinite alternate}
.typing span:nth-child(2){animation-delay:.2s}.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{to{opacity:.2;transform:translateY(-4px)}}

/* quick replies */
.quick{padding:4px 20px 10px;display:flex;gap:8px;flex-wrap:wrap}
.quick button{padding:7px 16px;border:1.5px solid var(--b);background:#fff;color:var(--b);border-radius:22px;font-size:12.5px;cursor:pointer;font-family:inherit;transition:all .2s;white-space:nowrap}
.quick button:hover{background:var(--b);color:#fff}

/* action buttons (summarize/translate after upload) */
.action-row{display:none;padding:4px 20px 10px;gap:6px;flex-wrap:wrap}
.action-row button{padding:6px 14px;border:1.5px solid var(--r);background:#fff;color:var(--r);border-radius:18px;font-size:12px;cursor:pointer;font-family:inherit;transition:all .2s}
.action-row button:hover{background:var(--r);color:#fff}

/* input bar */
.ib{padding:10px 14px;border-top:1px solid #e8e8e8;display:flex;gap:8px;background:#fff;flex-shrink:0;align-items:center}
.ib input[type=text]{flex:1;padding:10px 14px;border:1.5px solid #ddd;border-radius:24px;font-size:14px;font-family:inherit;outline:none;transition:border .2s;background:#f9f9f9}
.ib input[type=text]:focus{border-color:var(--b);background:#fff}
.ib button{width:40px;height:40px;border:none;border-radius:50%;color:#fff;font-size:15px;cursor:pointer;transition:all .2s;flex-shrink:0;display:flex;align-items:center;justify-content:center}
.ib .send-btn{background:var(--r)}.ib .send-btn:hover{background:#b8070f}
.ib .send-btn:disabled,.ib .mic-btn:disabled{background:#ccc;cursor:default;transform:none}
.ib .mic-btn{background:var(--b)}.ib .mic-btn:hover{background:var(--bl)}
.ib .mic-btn.recording{background:#e53935;animation:pulse 1s infinite}
.ib .attach-btn{background:#555;font-size:16px}.ib .attach-btn:hover{background:#333}
.ib input[type=file]{display:none}
@keyframes pulse{0%,100%{box-shadow:0 0 0 0 rgba(229,57,53,.4)}50%{box-shadow:0 0 0 8px rgba(229,57,53,0)}}

/* login modal */
.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:999;justify-content:center;align-items:center}
.modal-overlay.show{display:flex}
.modal{background:#fff;border-radius:16px;padding:28px;width:90%;max-width:380px;box-shadow:0 12px 40px rgba(0,0,0,.2);text-align:center}
.modal h3{color:var(--b);margin-bottom:16px;font-size:18px}
.modal input{width:100%;padding:12px 14px;border:1.5px solid #ddd;border-radius:12px;font-size:14px;font-family:inherit;outline:none;margin-bottom:12px;text-align:center}
.modal input:focus{border-color:var(--b)}
.modal .modal-btn{width:100%;padding:12px;border:none;border-radius:12px;background:var(--r);color:#fff;font-size:14px;font-weight:600;cursor:pointer;font-family:inherit;transition:background .2s}
.modal .modal-btn:hover{background:#b8070f}
.modal .modal-btn:disabled{background:#ccc;cursor:default}
.modal .cancel-btn{width:100%;padding:10px;border:none;border-radius:12px;background:#f5f5f5;color:#666;font-size:13px;cursor:pointer;font-family:inherit;margin-top:8px}
.modal .step{display:none}.modal .step.active{display:block}
.modal .error{color:var(--r);font-size:12px;margin-top:4px}

/* footer */
.footer{background:var(--b);color:#fff;text-align:center;padding:14px 24px;font-size:12px;opacity:.9}

@media(max-width:600px){
  .topbar,.nav-links{display:none}
  .hero h1{font-size:20px}.chat-main{padding:10px 6px 16px}
  .cc{height:calc(100vh - 180px);border-radius:10px}
}
</style>
</head>
<body>

<div class="topbar">
  <div class="topbar-r"><a href="mailto:info@ust.edu.sd"><i class="fas fa-envelope" style="margin-left:4px"></i>info@ust.edu.sd</a></div>
  <div class="topbar-r"><a href="https://ust.edu.sd">ust.edu.sd</a><a href="https://portal.ust.edu.sd/">E-Learning</a></div>
</div>

<nav class="navbar">
  <a href="https://ust.edu.sd" class="brand">
    <img src="https://ust.edu.sd/public/fornt/img/678.png" alt="UST">
    <div class="brand-t">جامعة العلوم والتقانة<small>University of Science and Technology</small></div>
  </a>
  <div class="nav-links">
    <a href="https://ust.edu.sd">Home</a>
    <a href="https://ust.edu.sd/pages/about-university">About</a>
    <a href="https://ust.edu.sd/pages/admissions-administration">Admissions</a>
    <a href="https://portal.ust.edu.sd/">Portal</a>
  </div>
</nav>

<div class="hero">
  <h1>&#129302; مساعد الجامعة الذكي</h1>
  <p>اسألني أي سؤال عن الجامعة — ارفع ملفات للتلخيص أو الترجمة، أرسل رسائل صوتية، أو سجّل دخول لعرض مقرراتك!</p>
  <span class="badge">UST SMART ASSISTANT</span>
</div>

<div class="chat-main">
<div class="cc">
  <div class="ch">
    <div class="av"><img src="https://ust.edu.sd/public/fornt/img/678.png" alt="UST" onerror="this.outerHTML='&#127891;'"></div>
    <div class="txt"><h3>مساعد جامعة العلوم والتقانة</h3><p id="statusText">متصل الآن &bull; يرد على استفساراتك فوراً</p></div>
    <div class="dot"></div>
  </div>

  <div class="user-bar" id="userBar">
    <span id="userLabel">زائر</span>
    <button class="login-btn" id="loginBtn" onclick="showLogin()"><i class="fas fa-sign-in-alt"></i> تسجيل الدخول</button>
  </div>

  <div class="msgs" id="msgs">
    <div class="msg bot">&#1571;&#1607;&#1604;&#1575;&#1611; &#1576;&#1575;&#1603; &#1601;&#1610; &#1605;&#1587;&#1575;&#1593;&#1583; &#1580;&#1575;&#1605;&#1593;&#1577; &#1575;&#1604;&#1593;&#1604;&#1608;&#1605; &#1608;&#1575;&#1604;&#1578;&#1602;&#1575;&#1606;&#1577; &#128522;</div>
    <div class="msg bot">اسألني أي شي أو ارفع ملف للتلخيص!</div>
  </div>

  <div class="quick" id="quick">
    <button data-q="شنو كлиات الجامعة">&#127979; الكليات</button>
    <button data-q="كم رسوم التسجيل">&#128176; الرسوم</button>
    <button data-q="شروط القبول">&#128220; القبول</button>
    <button data-q="متى تأسست الجامعة">&#128218; نبذة</button>
  </div>

  <div class="action-row" id="actionRow">
    <button onclick="doFileAction('summarize')">&#128203; تلخيص كنص</button>
    <button onclick="doFileAction('summarize_pdf')">&#128211; تلخيص كـ PDF</button>
    <button onclick="doFileAction('translate')">&#128269; ترجمة كنص</button>
    <button onclick="doFileAction('translate_pdf')">&#128196; ترجمة كـ PDF</button>
  </div>

  <div class="typing" id="typing"><span></span><span></span><span></span></div>

  <div class="ib">
    <button class="attach-btn" onclick="document.getElementById('fileInput').click()" title="Upload file"><i class="fas fa-paperclip"></i></button>
    <input type="file" id="fileInput" accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg" onchange="uploadFile(this)">
    <button class="mic-btn" id="micBtn" onclick="toggleMic()" title="Record voice"><i class="fas fa-microphone"></i></button>
    <input type="text" id="inp" placeholder="اكتب سؤالك هنا..." autocomplete="off">
    <button class="send-btn" id="sendBtn" onclick="send()"><i class="fas fa-paper-plane"></i></button>
  </div>
</div>
</div>

<!-- Login Modal -->
<div class="modal-overlay" id="loginModal">
  <div class="modal">
    <h3>&#128272; تسجيل الدخول</h3>
    <div class="step active" id="step1">
      <p style="font-size:13px;color:#666;margin-bottom:12px">اكتب رقمك الجامعي أو معرف الدكتور</p>
      <input type="text" id="loginId" placeholder="مثال: 123456789" autofocus>
      <button class="modal-btn" id="loginBtn1" onclick="loginStart()"><i class="fas fa-arrow-left"></i> إرسال</button>
    </div>
    <div class="step" id="step2">
      <p style="font-size:13px;color:#666;margin-bottom:12px">تم إرسال رمز التحقق على بريدك</p>
      <input type="text" id="loginOtp" placeholder="6 أرقام" maxlength="6">
      <div class="error" id="loginError"></div>
      <button class="modal-btn" id="loginBtn2" onclick="loginVerify()"><i class="fas fa-check"></i> تحقق</button>
    </div>
    <button class="cancel-btn" onclick="hideLogin()">إلغاء</button>
  </div>
</div>

<div class="footer">University of Science and Technology &copy; 2025 &mdash; <a href="https://ust.edu.sd">ust.edu.sd</a></div>

<script>
(function(){
var msgs=document.getElementById('msgs'),inp=document.getElementById('inp'),
    sendBtn=document.getElementById('sendBtn'),typing=document.getElementById('typing'),
    quick=document.getElementById('quick'),micBtn=document.getElementById('micBtn'),
    actionRow=document.getElementById('actionRow'),userLabel=document.getElementById('userLabel'),
    userBar=document.getElementById('userBar'),loginBtn=document.getElementById('loginBtn'),
    statusText=document.getElementById('statusText');
var sid=localStorage.getItem('ust_sid');
if(!sid){sid=crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2);localStorage.setItem('ust_sid',sid)}
var pendingFile=null;
var isLoggedIn=false;

function addMsg(text,cls){
  var d=document.createElement('div');d.className='msg '+cls;d.textContent=text;
  msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
function showTyping(){typing.style.display='flex';msgs.scrollTop=msgs.scrollHeight}
function hideTyping(){typing.style.display='none'}

/* ── Text Chat ── */
window.send=function(text){
  var t=text||inp.value.trim();if(!t)return;
  inp.value='';quick.style.display='none';actionRow.style.display='none';
  addMsg(t,'user');sendBtn.disabled=true;showTyping();
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:t,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){
    if(d.logged_in){isLoggedIn=true;userLabel.innerHTML='<i class="fas fa-user-check"></i> مسجل الدخول';loginBtn.style.display='none'}
    hideTyping();addMsg(d.reply||'الآن ما أتمكّن من الإجابة.','bot');sendBtn.disabled=false;
  })
  .catch(function(){hideTyping();addMsg('حصل خطأ تقني. جرب تاني.','bot');sendBtn.disabled=false});
};
inp.addEventListener('keydown',function(e){if(e.key==='Enter')send()});
quick.addEventListener('click',function(e){if(e.target.dataset.q)send(e.target.dataset.q)});

/* ── File Upload ── */
window.uploadFile=function(el){
  var f=el.files[0];if(!f)return;
  var reader=new FileReader();
  reader.onload=function(){
    var b64=reader.result.split(',')[1];
    pendingFile={data:b64,name:f.name,mime:f.type||'application/octet-stream'};
    addMsg('جاري تحميل '+f.name+'...','file-info');
    quick.style.display='none';showTyping();
    fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},
      body:JSON.stringify({file_data:b64,filename:f.name,mime:f.type||'application/octet-stream',session_id:sid})})
    .then(function(r){return r.json()})
    .then(function(d){hideTyping();addMsg(d.reply||'تعذرت المعالجة.','bot');if(d.actions)actionRow.style.display='flex'})
    .catch(function(){hideTyping();addMsg('خطأ في رفع الملف.','bot')});
  };
  reader.readAsDataURL(f);el.value='';
};
window.doFileAction=function(act){
  if(!pendingFile)return;
  actionRow.style.display='none';
  addMsg('جاري المعالجة...','file-info');showTyping();
  fetch('/api/upload',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({file_data:pendingFile.data,filename:pendingFile.name,mime:pendingFile.mime,action:act,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){
    hideTyping();
    if(d.pdf){
      var ln=document.createElement('a');ln.href='data:application/pdf;base64,'+d.pdf;
      ln.download=d.pdf_name||'result.pdf';ln.className='msg file-info';
      ln.innerHTML='&#128196; تحميل '+d.pdf_name;msgs.appendChild(ln);msgs.scrollTop=msgs.scrollHeight;
    }
    addMsg(d.reply||'تعذرت المعالجة.','bot');pendingFile=null;
  })
  .catch(function(){hideTyping();addMsg('خطأ في المعالجة.','bot');pendingFile=null});
};

/* ── Voice Recording ── */
var mediaRecorder=null;var audioChunks=[];
window.toggleMic=function(){
  if(mediaRecorder&&mediaRecorder.state==='recording'){
    mediaRecorder.stop();micBtn.classList.remove('recording');return;
  }
  navigator.mediaDevices.getUserMedia({audio:true}).then(function(stream){
    mediaRecorder=new MediaRecorder(stream);audioChunks=[];
    micBtn.classList.add('recording');
    addMsg('&#127908; جاري التسجيل...','voice-info');
    mediaRecorder.ondataavailable=function(e){audioChunks.push(e.data)};
    mediaRecorder.onstop=function(){
      stream.getTracks().forEach(function(t){t.stop()});
      var blob=new Blob(audioChunks,{type:'audio/webm'});
      var reader=new FileReader();
      reader.onload=function(){
        var b64=reader.result.split(',')[1];
        quick.style.display='none';showTyping();
        fetch('/api/voice',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({audio_data:b64,session_id:sid})})
        .then(function(r){return r.json()})
        .then(function(d){
          hideTyping();
          if(d.transcribed)addMsg('&#127908; '+d.transcribed,'voice-info');
          addMsg(d.reply||'تعذرت معالجة الصوت.','bot');
        })
        .catch(function(){hideTyping();addMsg('خطأ في معالجة الصوت.','bot')});
      };
      reader.readAsDataURL(blob);
    };
    mediaRecorder.start();
  }).catch(function(){addMsg('ما قدرت أفتح الميكروفون. ا granting صلاحية الميكروفون.','bot')});
};

/* ── Login ── */
window.showLogin=function(){document.getElementById('loginModal').classList.add('show');document.getElementById('loginId').focus()};
window.hideLogin=function(){document.getElementById('loginModal').classList.remove('show')};
window.loginStart=function(){
  var uid=document.getElementById('loginId').value.trim();if(!uid)return;
  document.getElementById('loginBtn1').disabled=true;
  fetch('/api/login/start',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({user_id:uid,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){
    document.getElementById('loginBtn1').disabled=false;
    if(d.step==='ask_otp'){
      document.getElementById('step1').classList.remove('active');
      document.getElementById('step2').classList.add('active');
      document.getElementById('loginOtp').focus();
      addMsg(d.reply,'bot');
    }else{
      document.getElementById('loginError').textContent=d.reply;
    }
  }).catch(function(){document.getElementById('loginBtn1').disabled=false});
};
window.loginVerify=function(){
  var code=document.getElementById('loginOtp').value.trim();if(!code)return;
  document.getElementById('loginBtn2').disabled=true;
  fetch('/api/login/verify',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({code:code,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){
    document.getElementById('loginBtn2').disabled=false;
    addMsg(d.reply,'bot');
    if(d.step==='done'){
      hideLogin();
      if(d.reply.indexOf('نجاح')>-1){
        isLoggedIn=true;
        userLabel.innerHTML='<i class="fas fa-user-check"></i> مسجل الدخول';
        loginBtn.style.display='none';
      }
    }else{
      document.getElementById('loginError').textContent=d.reply;
    }
  }).catch(function(){document.getElementById('loginBtn2').disabled=false});
};
})();
</script>
</body>
</html>"""

CHAT_HTML = CHAT_FULL_HTML

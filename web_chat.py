"""Web chat widget — serves the chat UI and API for the university website."""
import asyncio
import json
import logging
import time
import uuid

from gemini_services import detect_user_intent, generate_answer, detect_text_language
from database import get_knowledge_base_text

_sessions = {}
SESSION_TTL = 1800


def _get_session(sid):
    now = time.time()
    s = _sessions.get(sid)
    if s and now - s["last"] < SESSION_TTL:
        s["last"] = now
        return s
    _sessions.pop(sid, None)
    return None


def _new_session():
    sid = uuid.uuid4().hex[:16]
    _sessions[sid] = {"last": time.time()}
    return sid


CHAT_HTML = r"""<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>بوت جامعة العلوم والتقانة</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Segoe UI',Tahoma,Arial,sans-serif;background:#f0f2f5;display:flex;justify-content:center;align-items:center;min-height:100vh}
.chat-wrap{width:420px;max-width:96vw;height:90vh;max-height:700px;background:#fff;border-radius:16px;box-shadow:0 8px 32px rgba(0,0,0,.12);display:flex;flex-direction:column;overflow:hidden}
.header{background:linear-gradient(135deg,#1a5276,#2e86c1);color:#fff;padding:16px 20px;display:flex;align-items:center;gap:12px}
.header .avatar{width:44px;height:44px;border-radius:50%;background:rgba(255,255,255,.2);display:flex;align-items:center;justify-content:center;font-size:22px}
.header .info h3{font-size:15px;font-weight:600}
.header .info span{font-size:12px;opacity:.8}
.messages{flex:1;overflow-y:auto;padding:16px;display:flex;flex-direction:column;gap:8px}
.msg{max-width:82%;padding:10px 14px;border-radius:14px;font-size:14px;line-height:1.6;word-wrap:break-word;animation:fadeIn .2s}
.msg.bot{background:#e8f0fe;color:#1a1a1a;align-self:flex-start;border-bottom-right-radius:4px}
.msg.user{background:#1a5276;color:#fff;align-self:flex-end;border-bottom-left-radius:4px}
.msg.system{background:#fff3cd;color:#856404;align-self:center;font-size:12px;border-radius:8px;text-align:center}
.typing{align-self:flex-start;padding:10px 14px;background:#e8f0fe;border-radius:14px;display:none}
.typing span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#999;margin:0 2px;animation:bounce .6s infinite alternate}
.typing span:nth-child(2){animation-delay:.2s}
.typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{to{opacity:.3;transform:translateY(-4px)}}
@keyframes fadeIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
.input-bar{padding:12px;border-top:1px solid #e5e7eb;display:flex;gap:8px}
.input-bar input{flex:1;padding:10px 14px;border:1px solid #d1d5db;border-radius:24px;font-size:14px;outline:none;direction:rtl}
.input-bar input:focus{border-color:#2e86c1}
.input-bar button{width:42px;height:42px;border:none;border-radius:50%;background:#1a5276;color:#fff;font-size:18px;cursor:pointer;transition:background .2s}
.input-bar button:hover{background:#2e86c1}
.input-bar button:disabled{background:#ccc;cursor:default}
</style>
</head>
<body>
<div class="chat-wrap">
  <div class="header">
    <div class="avatar">&#127891;</div>
    <div class="info">
      <h3>جامعة العلوم والتقانة</h3>
      <span>مساعد ذكي &mdash; اسألني أي سؤال</span>
    </div>
  </div>
  <div class="messages" id="msgs">
    <div class="msg bot">&#1608;&#1571;&#1607;&#1604;&#1575;&#1611; &#1576;&#1603;!</div>
    <div class="msg bot">asjejni an kuliaat aljamia, alstigrar, alrusuum, aw mawa'id alimtihanat.</div>
  </div>
  <div class="typing" id="typing"><span></span><span></span><span></span></div>
  <div class="input-bar">
    <button id="sendBtn" title="Send">&#10148;</button>
    <input id="inp" placeholder="اكتب سؤالك هنا..." autofocus>
  </div>
</div>
<script>
(function(){
var msgs=document.getElementById('msgs'),inp=document.getElementById('inp'),
    btn=document.getElementById('sendBtn'),typing=document.getElementById('typing');
var sid=localStorage.getItem('chat_sid');
if(!sid){sid= crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2);localStorage.setItem('chat_sid',sid)}
function addMsg(text,cls){var d=document.createElement('div');d.className='msg '+cls;d.textContent=text;msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight}
function showTyping(){typing.style.display='flex';msgs.scrollTop=msgs.scrollHeight}
function hideTyping(){typing.style.display='none'}
function send(){
  var t=inp.value.trim();if(!t)return;
  addMsg(t,'user');inp.value='';btn.disabled=true;showTyping();
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:t,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){hideTyping();addMsg(d.reply||'Ma a9der ajiwb dalwa9ti.','bot');btn.disabled=false})
  .catch(function(){hideTyping();addMsg('Hadda qalat technical. Jarib taani.','bot');btn.disabled=false})
}
btn.addEventListener('click',send);
inp.addEventListener('keydown',function(e){if(e.key==='Enter')send()});
})();
</script>
</body>
</html>"""


def handle_chat_request(body):
    msg = (body.get("message") or "").strip()
    sid = body.get("session_id") or ""
    if not msg:
        return {"reply": "Moddk tewadeh sue'alak aktar?"}
    _get_session(sid) or _new_session()
    lang = detect_text_language(msg)
    try:
        reply = asyncio.run(generate_answer(msg, chat_id=0, language=lang))
    except Exception as e:
        logging.error("Web chat error: %s", e)
        reply = "Hadda qalat technical. Jarib taani ba'd shwaya."
    return {"reply": reply, "session_id": sid}

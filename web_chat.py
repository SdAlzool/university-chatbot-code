"""Web chat widget — serves the chat UI and API for the university website."""
import asyncio
import json
import logging
import time
import uuid

from gemini_services import generate_answer, detect_text_language

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
<title>UST Chat Assistant</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;500;600;700&family=Cairo:wght@400;600;700&display=swap" rel="stylesheet">
<link rel="stylesheet" href="https://use.fontawesome.com/releases/v5.15.4/css/all.css"/>
<style>
:root{--ust-blue:#000067;--ust-red:#cc0812;--ust-white:#fff;--ust-gray:#f4f6f9;--ust-dark:#1a1a2e}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:'Poppins','Cairo',sans-serif;background:transparent;overflow:hidden}

/* ===== Floating Button ===== */
.ust-chat-fab{position:fixed;bottom:24px;right:24px;z-index:2147483647;width:60px;height:60px;border-radius:50%;background:linear-gradient(135deg,var(--ust-blue),#000080);color:#fff;border:none;font-size:26px;cursor:pointer;box-shadow:0 4px 20px rgba(0,0,103,.4);transition:all .3s ease;display:flex;align-items:center;justify-content:center}
.ust-chat-fab:hover{transform:scale(1.08);box-shadow:0 6px 28px rgba(0,0,103,.55)}
.ust-chat-fab .fab-badge{position:absolute;top:-2px;right:-2px;width:18px;height:18px;border-radius:50%;background:var(--ust-red);font-size:10px;display:flex;align-items:center;justify-content:center;font-weight:700;border:2px solid #fff}
.ust-chat-fab.open .fa-comment-dots{display:none}
.ust-chat-fab:not(.open) .fa-times{display:none}
.ust-chat-fab .ripple{position:absolute;width:100%;height:100%;border-radius:50%;background:rgba(255,255,255,.25);animation:fabPulse 2s infinite;pointer-events:none}
@keyframes fabPulse{0%{transform:scale(1);opacity:.6}100%{transform:scale(1.8);opacity:0}}

/* ===== Chat Window ===== */
.ust-chat-window{position:fixed;bottom:96px;right:24px;z-index:2147483646;width:380px;max-width:calc(100vw - 32px);height:540px;max-height:calc(100vh - 140px);background:#fff;border-radius:16px;box-shadow:0 12px 48px rgba(0,0,103,.18);display:flex;flex-direction:column;overflow:hidden;opacity:0;transform:translateY(20px) scale(.95);pointer-events:none;transition:all .3s cubic-bezier(.4,0,.2,1)}
.ust-chat-window.open{opacity:1;transform:translateY(0) scale(1);pointer-events:auto}

/* ===== Header ===== */
.ust-header{background:linear-gradient(135deg,var(--ust-blue) 0%,#000080 100%);color:#fff;padding:16px 18px;display:flex;align-items:center;gap:12px;flex-shrink:0}
.ust-header .logo-wrap{width:46px;height:46px;border-radius:50%;background:rgba(255,255,255,.15);display:flex;align-items:center;justify-content:center;overflow:hidden;flex-shrink:0}
.ust-header .logo-wrap img{width:32px;height:32px;object-fit:contain}
.ust-header .logo-wrap .fallback-icon{font-size:22px;display:none}
.ust-header .info{flex:1;min-width:0}
.ust-header .info h3{font-size:14px;font-weight:600;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.ust-header .info p{font-size:11px;opacity:.8;margin:2px 0 0}
.ust-header .online-dot{width:8px;height:8px;border-radius:50%;background:#4caf50;flex-shrink:0;animation:blink 1.5s infinite}
@keyframes blink{0%,100%{opacity:1}50%{opacity:.4}}

/* ===== Messages ===== */
.ust-messages{flex:1;overflow-y:auto;padding:14px;display:flex;flex-direction:column;gap:8px;background:var(--ust-gray)}
.ust-messages::-webkit-scrollbar{width:4px}
.ust-messages::-webkit-scrollbar-thumb{background:#ccc;border-radius:4px}
.ust-msg{max-width:85%;padding:10px 14px;font-size:13.5px;line-height:1.65;word-wrap:break-word;animation:msgIn .25s ease}
.ust-msg.bot{background:#fff;color:#222;align-self:flex-start;border-radius:4px 14px 14px 14px;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.ust-msg.user{background:var(--ust-blue);color:#fff;align-self:flex-end;border-radius:14px 4px 14px 14px}
.ust-msg.system{background:#fff3cd;color:#856404;align-self:center;font-size:11px;border-radius:8px;text-align:center;padding:6px 12px}
@keyframes msgIn{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}

/* ===== Typing Indicator ===== */
.ust-typing{align-self:flex-start;padding:10px 16px;background:#fff;border-radius:4px 14px 14px 14px;display:none;box-shadow:0 1px 3px rgba(0,0,0,.06)}
.ust-typing span{display:inline-block;width:7px;height:7px;border-radius:50%;background:#bbb;margin:0 2px;animation:bounce .6s infinite alternate}
.ust-typing span:nth-child(2){animation-delay:.2s}
.ust-typing span:nth-child(3){animation-delay:.4s}
@keyframes bounce{to{opacity:.25;transform:translateY(-4px)}}

/* ===== Input ===== */
.ust-input-bar{padding:10px 12px;border-top:1px solid #e8e8e8;display:flex;gap:8px;background:#fff;flex-shrink:0}
.ust-input-bar input{flex:1;padding:10px 14px;border:1.5px solid #ddd;border-radius:24px;font-size:13.5px;font-family:inherit;outline:none;transition:border .2s;background:#f9f9f9}
.ust-input-bar input:focus{border-color:var(--ust-blue);background:#fff}
.ust-input-bar button{width:40px;height:40px;border:none;border-radius:50%;background:var(--ust-red);color:#fff;font-size:16px;cursor:pointer;transition:all .2s;flex-shrink:0;display:flex;align-items:center;justify-content:center}
.ust-input-bar button:hover{background:#b8070f;transform:scale(1.05)}
.ust-input-bar button:disabled{background:#ccc;cursor:default;transform:none}

/* ===== Quick Replies ===== */
.ust-quick{padding:0 12px 10px;display:flex;gap:6px;flex-wrap:wrap}
.ust-quick button{padding:5px 12px;border:1.5px solid var(--ust-blue);background:#fff;color:var(--ust-blue);border-radius:20px;font-size:11.5px;cursor:pointer;font-family:inherit;transition:all .2s;white-space:nowrap}
.ust-quick button:hover{background:var(--ust-blue);color:#fff}
</style>
</head>
<body>

<button class="ust-chat-fab open" id="ustFab" aria-label="Chat">
  <i class="fas fa-comment-dots"></i>
  <i class="fas fa-times"></i>
  <div class="ripple"></div>
</button>

<div class="ust-chat-window" id="ustWindow">
  <div class="ust-header">
    <div class="logo-wrap">
      <img src="https://ust.edu.sd/public/fornt/img/678.png" alt="UST"
           onerror="this.style.display='none';this.nextElementSibling.style.display='flex'">
      <span class="fallback-icon" style="display:flex;align-items:center;justify-content:center">&#127891;</span>
    </div>
    <div class="info">
      <h3>جامعة العلوم والتقانة</h3>
      <p>UST Smart Assistant &bull; online</p>
    </div>
    <div class="online-dot"></div>
  </div>

  <div class="ust-messages" id="ustMsgs">
    <div class="ust-msg bot">&#1571;&#1607;&#1604;&#1575;&#1611; &#1576;&#1575;&#1603; &#1601;&#1610; &#1580;&#1575;&#1605;&#1593;&#1577; &#1575;&#1604;&#1593;&#1604;&#1608;&#1605; &#1608;&#1575;&#1604;&#1578;&#1602;&#1575;&#1606;&#1577; &#128522;</div>
    <div class="ust-msg bot">أسئلني عن الكليات، التسجيل، الرسوم، مواعيد الامتحانات، أو أي سؤال ثاني!</div>
  </div>

  <div class="ust-quick" id="ustQuick">
    <button data-q="شنو كليات الجامعة">الكليات</button>
    <button data-q="كم رسوم التسجيل">الرسوم</button>
    <button data-q="شروط القبول">القبول</button>
    <button data-q="متى تأسست الجامعة">نبذة</button>
  </div>

  <div class="ust-typing" id="ustTyping"><span></span><span></span><span></span></div>

  <div class="ust-input-bar">
    <input id="ustInp" placeholder="اكتب سؤالك هنا..." autocomplete="off">
    <button id="ustSend" aria-label="Send"><i class="fas fa-paper-plane"></i></button>
  </div>
</div>

<script>
(function(){
var fab=document.getElementById('ustFab'),win=document.getElementById('ustWindow'),
    msgs=document.getElementById('ustMsgs'),inp=document.getElementById('ustInp'),
    btn=document.getElementById('ustSend'),typing=document.getElementById('ustTyping'),
    quick=document.getElementById('ustQuick');

fab.addEventListener('click',function(){
  fab.classList.toggle('open');
  win.classList.toggle('open');
  if(win.classList.contains('open'))inp.focus();
});

var sid=localStorage.getItem('ust_chat_sid');
if(!sid){sid=crypto.randomUUID?crypto.randomUUID():Math.random().toString(36).slice(2);localStorage.setItem('ust_chat_sid',sid)}

function addMsg(text,cls){
  var d=document.createElement('div');d.className='ust-msg '+cls;
  d.textContent=text;msgs.appendChild(d);msgs.scrollTop=msgs.scrollHeight;
}
function showTyping(){typing.style.display='flex';msgs.scrollTop=msgs.scrollHeight}
function hideTyping(){typing.style.display='none'}

function send(text){
  var t=text||inp.value.trim();if(!t)return;
  inp.value='';quick.style.display='none';
  addMsg(t,'user');btn.disabled=true;showTyping();
  fetch('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({message:t,session_id:sid})})
  .then(function(r){return r.json()})
  .then(function(d){hideTyping();addMsg(d.reply||'&#1575;&#1604;&#1570;&#1606; &#1605;&#1575; &#1571;&#1578;&#1605;&#1603;&#1606; &#1575;&#1604;&#1575;&#1606;&#1578;&#1575;&#1580; &#1575;&#1604;&#1570;&#1606;.','bot');btn.disabled=false})
  .catch(function(){hideTyping();addMsg('&#1581;&#1589;&#1604; &#1582;&#1591;&#1572; &#1578;&#1602;&#1606;&#1610;. &#1580;&#1585;&#1576; &#1578;&#1575;&#1606;&#1610;.','bot');btn.disabled=false});
}

btn.addEventListener('click',function(){send()});
inp.addEventListener('keydown',function(e){if(e.key==='Enter')send()});
quick.addEventListener('click',function(e){if(e.target.dataset.q)send(e.target.dataset.q)});
})();
</script>
</body>
</html>"""


def handle_chat_request(body):
    msg = (body.get("message") or "").strip()
    sid = body.get("session_id") or ""
    if not msg:
        return {"reply": "وضّح سؤالك أكثر؟"}
    _get_session(sid) or _new_session()
    lang = detect_text_language(msg)
    try:
        reply = asyncio.run(generate_answer(msg, chat_id=0, language=lang))
    except Exception as e:
        logging.error("Web chat error: %s", e)
        reply = "حصل خطأ تقني. جرب تاني بعد شوية."
    return {"reply": reply, "session_id": sid}

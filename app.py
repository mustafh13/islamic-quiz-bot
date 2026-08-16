import os, json, random, threading, asyncio
from flask import Flask, jsonify, request, render_template_string
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

BASE=os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE,"questions.json"),encoding="utf-8") as f:
    QUESTIONS=json.load(f)

# ---------------- Web ----------------
app=Flask(__name__)

HTML="""<!doctype html>
<html lang="bn"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>ইসলামিক জ্ঞান পরীক্ষা</title>
<style>
*{box-sizing:border-box}body{margin:0;font-family:system-ui,sans-serif;background:linear-gradient(135deg,#e9f7ef,#f7faf8);color:#17251c}
.wrap{max-width:780px;margin:25px auto;padding:14px}.card{background:#fff;border-radius:24px;padding:24px;box-shadow:0 12px 40px #164b2b18}
.header{text-align:center}.logo{font-size:42px}h1{margin:5px 0}.sub{color:#65746a}
.info{display:flex;gap:10px;justify-content:space-between;flex-wrap:wrap;margin:18px 0}.pill{background:#edf7f0;border-radius:12px;padding:10px 14px;font-weight:700}
.progress{height:9px;background:#e5ebe7;border-radius:99px;overflow:hidden}.bar{height:100%;background:#126b3a;width:0%;transition:.25s}
.q{font-size:22px;line-height:1.65;margin:18px 0}.option{display:block;width:100%;text-align:left;margin:10px 0;background:#f5f8f6;color:#173323;border:2px solid #e5ebe7;border-radius:14px;padding:14px;font-size:17px;cursor:pointer}
.option.correct{background:#dff5e6;border-color:#169447}.option.wrong{background:#ffe5e5;border-color:#d33}.option:disabled{cursor:default}
.feedback{min-height:28px;font-weight:800;margin:12px 0}.next,.restart{background:#126b3a;color:#fff;border:0;border-radius:13px;padding:13px 22px;font-size:17px;cursor:pointer}
.next{display:none}.result{text-align:center;display:none}.score{font-size:42px;font-weight:900;color:#126b3a}
</style></head><body><div class="wrap"><div class="card">
<div class="header"><div class="logo">🕌</div><h1>ইসলামিক জ্ঞান পরীক্ষা</h1><div class="sub">১০০ প্রশ্ন • ১০০ নম্বর • ৪ অপশন</div></div>
<div id="exam"><div class="info"><div class="pill">📝 <span id="counter">১/১০০</span></div><div class="pill">🏆 <span id="score">০</span></div><div class="pill">🎯 ১০০</div></div>
<div class="progress"><div id="bar" class="bar"></div></div><div class="q" id="question"></div><div id="options"></div><div id="feedback" class="feedback"></div><button id="next" class="next" onclick="nextQ()">পরের প্রশ্ন →</button></div>
<div id="result" class="result"><div class="logo">🏆</div><h1>পরীক্ষা শেষ!</h1><div class="score"><span id="final">০</span>/১০০</div><p>সঠিক: <b id="right">০</b> | ভুল: <b id="wrong">০</b></p><p>শতকরা: <b id="percent">০</b>%</p><h2 id="grade"></h2><button class="restart" onclick="start()">আবার পরীক্ষা দিন</button></div>
</div></div>
<script>
let exam=[],p=0,s=0,r=0,w=0,locked=false;
const bn=n=>String(n).replace(/\d/g,d=>"০১২৩৪৫৬৭৮৯"[d]);
async function start(){let x=await fetch('/api/exam?count=100');exam=await x.json();p=0;s=0;r=0;w=0;document.getElementById('exam').style.display='block';document.getElementById('result').style.display='none';show()}
function show(){locked=false;let q=exam[p];document.getElementById('counter').textContent=bn(p+1)+"/"+bn(100);document.getElementById('score').textContent=bn(s);document.getElementById('bar').style.width=(p)+"%";document.getElementById('question').textContent=q.question;document.getElementById('feedback').textContent='';document.getElementById('next').style.display='none';let L=['ক','খ','গ','ঘ'];document.getElementById('options').innerHTML=q.options.map((x,i)=>`<button class="option" onclick="ans(${i},this)">${L[i]}. ${x}</button>`).join('')}
function ans(i,b){if(locked)return;locked=true;let q=exam[p],bs=document.querySelectorAll('.option');bs.forEach((x,j)=>{x.disabled=true;if(q.options[j]===q.answer)x.classList.add('correct')});if(q.options[i]===q.answer){s++;r++;b.classList.add('correct');document.getElementById('feedback').textContent='✅ সঠিক! +১ নম্বর'}else{w++;b.classList.add('wrong');document.getElementById('feedback').textContent='❌ ভুল! সঠিক উত্তর: '+q.answer}document.getElementById('score').textContent=bn(s);document.getElementById('next').style.display='inline-block'}
function nextQ(){p++;if(p>=100){document.getElementById('exam').style.display='none';document.getElementById('result').style.display='block';document.getElementById('final').textContent=bn(s);document.getElementById('right').textContent=bn(r);document.getElementById('wrong').textContent=bn(w);document.getElementById('percent').textContent=bn(s);document.getElementById('grade').textContent=s>=80?'🌟 অসাধারণ!':s>=60?'👏 খুব ভালো!':s>=40?'👍 ভালো চেষ্টা!':'📚 আরও অনুশীলন করুন!'}else show()}
start();
</script></body></html>"""

@app.get("/")
def home(): return render_template_string(HTML)
@app.get("/api/exam")
def exam_api():
    n=min(max(int(request.args.get("count",100)),1),len(QUESTIONS))
    return jsonify(random.sample(QUESTIONS,n))
@app.get("/api/stats")
def stats(): return jsonify({"total_questions":len(QUESTIONS),"exam_questions":100,"marks_per_question":1,"total_marks":100})

# ---------------- Telegram Bot ----------------
user_exams={}

def bn(n): return str(n).translate(str.maketrans("0123456789","০১২৩৪৫৬৭৮৯"))

async def start_cmd(update:Update, context:ContextTypes.DEFAULT_TYPE):
    kb=[[InlineKeyboardButton("📝 ১০০ নম্বরের পরীক্ষা শুরু করুন",callback_data="start_exam")]]
    await update.message.reply_text(
        "🕌 *ইসলামিক জ্ঞান পরীক্ষা*\n\n"
        "📚 ১১৬৮+ প্রশ্নের ডাটাবেস\n"
        "📝 প্রতি পরীক্ষায় ১০০টি Random প্রশ্ন\n"
        "🎯 ১ প্রশ্ন = ১ নম্বর\n"
        "🏆 মোট = ১০০ নম্বর\n"
        "🔘 প্রতিটি প্রশ্নে ৪টি Option\n\n"
        "নিচের বাটনে চাপ দিন 👇",
        reply_markup=InlineKeyboardMarkup(kb),parse_mode="Markdown")

async def button(update:Update, context:ContextTypes.DEFAULT_TYPE):
    q=update.callback_query
    await q.answer()
    uid=q.from_user.id
    if q.data=="start_exam":
        user_exams[uid]={"qs":random.sample(QUESTIONS,100),"pos":0,"score":0,"right":0,"wrong":0}
        await send_question(q,uid)
        return
    if q.data.startswith("ans:"):
        i=int(q.data.split(":")[1]); e=user_exams.get(uid)
        if not e or e["pos"]>=100: return
        item=e["qs"][e["pos"]]
        if item["options"][i]==item["answer"]:
            e["score"]+=1;e["right"]+=1;msg="✅ *সঠিক উত্তর!*  +১ নম্বর"
        else:
            e["wrong"]+=1;msg=f"❌ *ভুল উত্তর!*\nসঠিক উত্তর: *{item['answer']}*"
        e["pos"]+=1
        if e["pos"]>=100:
            await q.edit_message_text(
                f"🏆 *পরীক্ষা শেষ!*\n\n"
                f"🎯 প্রাপ্ত নম্বর: *{e['score']}/100*\n"
                f"✅ সঠিক: *{e['right']}টি*\n"
                f"❌ ভুল: *{e['wrong']}টি*\n"
                f"📊 শতকরা: *{e['score']}%*\n\n"
                + ("🌟 অসাধারণ!" if e["score"]>=80 else "👏 খুব ভালো!" if e["score"]>=60 else "👍 ভালো চেষ্টা!" if e["score"]>=40 else "📚 আরও অনুশীলন করুন!"),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔄 আবার পরীক্ষা",callback_data="start_exam")]]),
                parse_mode="Markdown")
        else:
            await q.edit_message_text(msg+"\n\nপরবর্তী প্রশ্ন লোড হচ্ছে...",parse_mode="Markdown")
            await send_question(q,uid)

async def send_question(query,uid):
    e=user_exams[uid]; item=e["qs"][e["pos"]]; L=["ক","খ","গ","ঘ"]
    kb=[[InlineKeyboardButton(f"{L[i]}. {x}",callback_data=f"ans:{i}")] for i,x in enumerate(item["options"])]
    text=(f"📝 *প্রশ্ন {bn(e['pos']+1)}/১০০*\n"
          f"🏆 বর্তমান স্কোর: *{bn(e['score'])}*\n\n"
          f"*{item['question']}*")
    markup=InlineKeyboardMarkup(kb)
    try:
        await query.edit_message_text(text,reply_markup=markup,parse_mode="Markdown")
    except Exception:
        await query.message.reply_text(text,reply_markup=markup,parse_mode="Markdown")

def run_bot():
    token=os.environ.get("BOT_TOKEN")
    if not token:
        print("BOT_TOKEN not set; Telegram bot disabled.")
        return
    loop=asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    application=Application.builder().token(token).build()
    application.add_handler(CommandHandler("start",start_cmd))
    application.add_handler(CallbackQueryHandler(button))
    loop.run_until_complete(application.initialize())
    loop.run_until_complete(application.start())
    loop.run_until_complete(application.updater.start_polling())
    print("Telegram bot polling started.")
    loop.run_forever()

# Gunicorn imports this module, so start the Telegram bot on import.
# Keep one Render web instance/worker to avoid multiple polling processes.
if os.environ.get("BOT_TOKEN"):
    threading.Thread(target=run_bot,daemon=True).start()

if __name__=="__main__":
    port=int(os.environ.get("PORT",10000))
    app.run(host="0.0.0.0",port=port)

(function(){
const history=[];
function add(text,user){const box=document.getElementById("realAiMsgs"),d=document.createElement("div");d.style="max-width:86%;padding:12px 14px;border-radius:14px;margin:8px 0;white-space:pre-wrap;line-height:1.45;"+(user?"margin-left:auto;background:#9cff22;color:#071006":"background:#171e28;color:#e9edf2");d.textContent=text;box.appendChild(d);box.scrollTop=box.scrollHeight;return d}
function mount(){
 const host=document.querySelector(".smm-main")||document.querySelector(".wrap");
 if(!host||document.getElementById("realAiBox"))return;
 const box=document.createElement("section");box.id="realAiBox";box.className="smm-panel";box.style="margin-top:14px;padding:0;overflow:hidden";
 box.innerHTML='<div style="padding:16px 18px;border-bottom:1px solid #202631;display:flex;justify-content:space-between"><b>✦ INK SMM INTELLIGENCE — LIVE</b><span class="smm-pill">AI ONLINE</span></div><div id="realAiMsgs" style="height:250px;overflow:auto;padding:16px"><div style="background:#171e28;color:#e9edf2;padding:12px 14px;border-radius:14px">Я готов работать. Дай задачу или нажми «Запустить агента».</div></div><form id="realAiForm" style="display:flex;gap:8px;padding:12px;border-top:1px solid #202631"><input id="realAiInput" maxlength="6000" style="flex:1;background:#151b24;border:1px solid #303946;color:#fff;border-radius:12px;padding:13px" placeholder="Например: создай контент-план на 7 дней"><button class="smm-run">Отправить</button></form>';
 host.appendChild(box);
 document.getElementById("realAiForm").onsubmit=async e=>{e.preventDefault();const i=document.getElementById("realAiInput"),m=i.value.trim();if(!m)return;i.value="";add(m,true);history.push({role:"user",content:m});await ask()};
}
async function ask(){
 const load=add("⏳ AI анализирует задачу…",false);
 try{
  const r=await fetch(SUPABASE_URL+"/functions/v1/smm-ai-chat",{method:"POST",headers:{"Content-Type":"application/json","apikey":SUPABASE_PUBLISHABLE_KEY},body:JSON.stringify({messages:history})});
  const d=await r.json();load.remove();if(!r.ok)throw Error(d.error||"AI HTTP "+r.status);
  add(d.answer||"AI не вернул ответ.",false);history.push({role:"assistant",content:d.answer||""});
 }catch(e){load.textContent="❌ "+e.message}
}
window.ramzesAskAI=async function(prompt){if(!document.getElementById("realAiBox"))mount();history.push({role:"user",content:prompt});await ask()};
document.addEventListener("DOMContentLoaded",mount);
})();
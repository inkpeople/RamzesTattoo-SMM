(function(){
const history=[];
function mount(){
 const root=document.getElementById("realAiMsgs");
 if(!root||document.getElementById("realAiForm"))return;
 const form=document.createElement("form"); form.id="realAiForm"; form.style="display:flex;gap:8px;padding:12px;border-top:1px solid #202631";
 form.innerHTML='<input id="realAiInput" maxlength="6000" style="flex:1;background:#151b24;border:1px solid #303946;color:#fff;border-radius:12px;padding:13px" placeholder="Задача агенту…"><button class="smm-run">Отправить</button>';
 root.parentElement.appendChild(form);
 form.onsubmit=async function(e){e.preventDefault();const i=document.getElementById("realAiInput"),m=i.value.trim();if(!m)return; i.value="";
 add(m,true); history.push({role:"user",content:m}); const load=add("⏳ Агент анализирует…",false);
 try{const r=await fetch(SUPABASE_URL+"/functions/v1/smm-ai-chat",{method:"POST",headers:{"Content-Type":"application/json","apikey":SUPABASE_PUBLISHABLE_KEY},body:JSON.stringify({messages:history})});const d=await r.json();load.remove();if(!r.ok)throw Error(d.error||"Ошибка AI");add(d.answer,false);history.push({role:"assistant",content:d.answer||""})}catch(x){load.textContent="Ошибка AI: "+x.message}}
}
function add(t,user){const b=document.getElementById("realAiMsgs"),d=document.createElement("div");d.style="max-width:82%;padding:12px 14px;border-radius:14px;margin:8px 0;white-space:pre-wrap;"+(user?"margin-left:auto;background:#9cff22;color:#071006":"background:#171e28;color:#e9edf2");d.textContent=t;b.appendChild(d);b.scrollTop=b.scrollHeight;return d}
document.addEventListener("DOMContentLoaded",mount);
})();
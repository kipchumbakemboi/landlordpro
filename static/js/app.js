function money(n){return 'KSh '+Number(n||0).toLocaleString(undefined,{minimumFractionDigits:2,maximumFractionDigits:2})}
async function loadMessages(userId){
  const box=document.getElementById('messages'); if(!box) return;
  box.dataset.userId=userId; box.innerHTML='<p class="text-muted">Loading messages...</p>';
  const res=await fetch(`/api/messages/${userId}`); const messages=await res.json();
  box.innerHTML=messages.map(m=>`<div class="bubble ${m.is_me?'me':''}"><div>${escapeHtml(m.content)}</div><small>${m.time}</small></div>`).join('') || '<p class="text-muted">No messages yet. Start the conversation.</p>';
  box.scrollTop=box.scrollHeight;
}
async function sendMessage(){
  const box=document.getElementById('messages'); const input=document.getElementById('messageInput');
  if(!box||!input||!box.dataset.userId||!input.value.trim()) return;
  await fetch('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({receiver_id:box.dataset.userId,content:input.value})});
  input.value=''; loadMessages(box.dataset.userId);
}
async function askAI(){
  const q=document.getElementById('aiQuestion'); const out=document.getElementById('aiMessages'); if(!q||!out||!q.value.trim())return;
  out.innerHTML += `<div class="bubble me">${escapeHtml(q.value)}</div>`;
  const text=q.value; q.value='';
  const res=await fetch('/api/ai',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question:text})});
  const data=await res.json(); out.innerHTML += `<div class="bubble">${escapeHtml(data.response)}</div>`; out.scrollTop=out.scrollHeight;
}
function escapeHtml(s){return String(s).replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]));}

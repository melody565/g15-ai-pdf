const API='/api/03.08';
const PROMPT=`請只在 AI-DEMO「03.08 帳號、登入與註冊」模組建立模擬註冊教學展示。包含註冊、聯絡驗證、沙盒管理者審核、使用者管理、模擬登入與稽核紀錄；使用 PostgreSQL 隔離保存，密碼只存安全雜湊，不發送真實郵件或簡訊，也不修改正式帳號與登入機制。`;
let state={applications:[],deliveries:[],users:[],events:[],sandbox:'',demoCode:'246810'};
const $=selector=>document.querySelector(selector);

async function request(path,options={}){
  const response=await fetch(API+path,{headers:{'Content-Type':'application/json'},...options});
  const payload=await response.json().catch(()=>({message:'伺服器回應格式不正確。'}));
  if(!response.ok){const error=new Error(payload.message||'操作失敗。');error.payload=payload;error.status=response.status;throw error}
  return payload;
}
function notify(message,error=false){const node=$('#notice');node.textContent=message;node.classList.toggle('error',error);node.hidden=false;node.scrollIntoView({behavior:'smooth',block:'nearest'})}
function escapeHtml(value){return String(value??'').replace(/[&<>'"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;',"'":'&#39;','"':'&quot;'}[c]))}
function statusLabel(value){return ({pending_contact:'待聯絡驗證',pending_review:'待審核',changes_requested:'退回補件',rejected:'已拒絕',approved:'已核准',active:'啟用',disabled:'停用',simulated_ready:'模擬待驗證',simulated_failed:'模擬寄送失敗',verified:'已驗證',expired:'已過期',superseded:'已取代'})[value]||value}
function statusClass(value){return ['rejected','disabled','simulated_failed','expired'].includes(value)?'danger':['pending_contact','pending_review','changes_requested'].includes(value)?'warn':''}

async function loadState(){
  try{state=await request('/state');$('#sandbox-id').textContent=`教學沙盒 ${state.sandbox}`;renderAll()}
  catch(error){notify(error.message,true)}
}
function renderAll(){renderLifecycle();renderVerification();renderReviews();renderUsers();renderAudit()}
function renderLifecycle(){
  const statuses=state.applications.map(x=>x.status);let stage='register';
  if(statuses.includes('pending_contact'))stage='verify';if(statuses.includes('pending_review'))stage='review';if(state.users.some(x=>x.user_status==='active'))stage='login';
  document.querySelectorAll('#lifecycle li').forEach(li=>li.classList.toggle('current',li.dataset.stage===stage));
}
function latestDelivery(applicationId){return state.deliveries.find(item=>item.application_id===applicationId)}
function renderVerification(){
  const target=$('#verification-list');const apps=state.applications.filter(app=>app.status==='pending_contact');
  target.innerHTML=apps.length?apps.map(app=>{const delivery=latestDelivery(app.id);return `<article class="record-card"><div><h3>${escapeHtml(app.username)} · ${escapeHtml(app.full_name)}</h3><p>${escapeHtml(app.contact_method==='email'?app.email:app.phone)}<br>${delivery?`模擬寄送：${escapeHtml(delivery.destination_masked)} · ${statusLabel(delivery.delivery_status)} · 錯誤 ${delivery.attempts}/5`:''}</p><span class="chip ${statusClass(delivery?.delivery_status)}">${statusLabel(delivery?.delivery_status||'尚未寄送')}</span>${delivery?.delivery_status==='simulated_ready'?`<p><b>教學驗證碼：${state.demoCode}</b>（畫面示範用）</p>`:''}</div><div class="record-actions">${delivery?`<input aria-label="${escapeHtml(app.username)} 驗證碼" data-code-for="${delivery.id}" inputmode="numeric" maxlength="6" placeholder="6 碼驗證碼"><button data-verify="${delivery.id}" type="button">驗證</button><button data-expire="${delivery.id}" type="button">模擬過期</button><button data-resend="${delivery.id}" type="button">模擬重送</button>`:''}</div></article>`}).join(''):'<p class="empty">目前沒有待聯絡驗證的申請。</p>';
}
function renderReviews(){
  const apps=state.applications.filter(app=>app.status==='pending_review');$('#review-list').innerHTML=apps.length?apps.map(app=>`<article class="record-card"><div><h3>${escapeHtml(app.username)} · ${escapeHtml(app.full_name)}</h3><p>${escapeHtml(app.organization)} · 申請 ${escapeHtml(app.requested_role)}<br>${escapeHtml(app.purpose)}</p><span class="chip warn">${statusLabel(app.status)}</span></div><div class="record-actions"><button data-review="changes" data-id="${app.id}" data-version="${app.version}" type="button">退回補件</button><button data-review="reject" data-id="${app.id}" data-version="${app.version}" type="button">拒絕</button><button class="primary" data-review="approve" data-id="${app.id}" data-version="${app.version}" type="button">核准</button></div></article>`).join(''):'<p class="empty">目前沒有待審核申請。</p>';
}
function renderUsers(){
  $('#user-list').innerHTML=state.users.length?state.users.map(user=>`<article class="record-card"><div><h3>${escapeHtml(user.username)} · ${escapeHtml(user.display_name)}</h3><p>沙盒角色：${escapeHtml(user.sandbox_role)} · 不具正式權限</p><span class="chip ${statusClass(user.user_status)}">${statusLabel(user.user_status)}</span></div><div class="record-actions"><button data-user-status="${user.user_status==='active'?'disabled':'active'}" data-id="${user.id}" data-version="${user.version}" type="button">${user.user_status==='active'?'停用':'重新啟用'}</button></div></article>`).join(''):'<p class="empty">尚未建立已核准的沙盒使用者。</p>';
}
function renderAudit(){
  $('#audit-list').innerHTML=state.events.length?state.events.map(event=>`<article class="audit-item"><time>${new Date(event.created_at).toLocaleString('zh-TW',{hour12:false})}</time><b>${escapeHtml(event.event_type)}</b><code>${escapeHtml(JSON.stringify(event.detail))}</code></article>`).join(''):'<p class="empty">尚無流程紀錄。</p>';
}
function switchTab(name){
  document.querySelectorAll('[data-tab]').forEach(button=>button.classList.toggle('active',button.dataset.tab===name));document.querySelectorAll('[data-panel]').forEach(panel=>{panel.hidden=panel.dataset.panel!==name;panel.classList.toggle('active',panel.dataset.panel===name)});const map={register:'register',verify:'verify',review:'review',users:'review',login:'login',audit:'login'};document.querySelectorAll('#lifecycle li').forEach(li=>li.classList.toggle('current',li.dataset.stage===map[name]));
}
function demoDraft(){
  const form=$('#registration-form');const values={username:'demo.student',full_name:'虛構學生',email:'student@example.invalid',phone:'0912000037',organization:'AI-DEMO 虛構學系',title:'學生',requested_role:'student',purpose:'練習 03.08 註冊、驗證、審核與登入流程。',password:'DemoPass123',password_confirm:'DemoPass123'};Object.entries(values).forEach(([name,value])=>form.elements[name].value=value);form.elements.contact_method.value='email';form.elements.consent.checked=true;form.elements.simulate_failure.checked=false;clearErrors();notify('已填入不含真實個人資料的 Demo 草稿。')
}
function clearErrors(){document.querySelectorAll('[data-error]').forEach(node=>node.textContent='');document.querySelectorAll('.invalid').forEach(node=>node.classList.remove('invalid'))}
function showErrors(errors={}){clearErrors();Object.entries(errors).forEach(([name,message])=>{const node=document.querySelector(`[data-error="${name}"]`);if(node){node.textContent=message;node.closest('label,fieldset')?.classList.add('invalid')}})}
function formPayload(form){const data=Object.fromEntries(new FormData(form));return {...data,consent:form.elements.consent.checked,simulate_failure:form.elements.simulate_failure.checked}}
function validateClient(data){
  const errors={};
  if(!/^[A-Za-z0-9._-]{4,32}$/.test(data.username||''))errors.username='帳號需為 4～32 個英數字及 . _ -。';
  if((data.full_name||'').length<2||(data.full_name||'').length>60)errors.full_name='姓名需為 2～60 字。';
  ['organization','title','requested_role','purpose'].forEach(name=>{if(!(data[name]||'').trim())errors[name]='此欄位為必填。'});
  if(data.contact_method==='email'&&!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email||''))errors.email='Email 為必填且格式需正確。';
  if(data.contact_method==='sms'&&!/^(?:\+886|0)9\d{8}$/.test((data.phone||'').replace(/[\s()-]/g,'')))errors.phone='手機為必填，請輸入臺灣手機格式。';
  if((data.password||'').length<8||(data.password||'').length>128||!/[A-Za-z]/.test(data.password||'')||!(/\d/.test(data.password||'')))errors.password='密碼需為 8～128 字元且同時包含英文字母與數字。';
  if(data.password!==data.password_confirm)errors.password_confirm='兩次密碼不一致。';
  if(!data.consent)errors.consent='請勾選同意教學沙盒說明。';
  return errors;
}

document.querySelector('.tabs').addEventListener('click',event=>{const button=event.target.closest('[data-tab]');if(button)switchTab(button.dataset.tab)});
$('#fill-demo').addEventListener('click',demoDraft);
$('#registration-form').addEventListener('submit',async event=>{event.preventDefault();const payload=formPayload(event.currentTarget);const clientErrors=validateClient(payload);clearErrors();if(Object.keys(clientErrors).length){showErrors(clientErrors);document.querySelector(`[name="${Object.keys(clientErrors)[0]}"]`)?.focus();return notify('請先修正表單欄位。',true)}const button=event.submitter;button.disabled=true;try{const result=await request('/register',{method:'POST',body:JSON.stringify(payload)});notify(`${result.message} 真實訊息寄送：否。`);await loadState();switchTab('verify')}catch(error){showErrors(error.payload?.errors);notify(error.message,true)}finally{button.disabled=false}});
$('#registration-form').addEventListener('reset',()=>setTimeout(clearErrors));
document.addEventListener('click',async event=>{
  const refresh=event.target.closest('[data-refresh]');if(refresh)return loadState();
  const verify=event.target.closest('[data-verify]');const expire=event.target.closest('[data-expire]');const resend=event.target.closest('[data-resend]');const review=event.target.closest('[data-review]');const userStatus=event.target.closest('[data-user-status]');
  try{
    if(verify){const input=document.querySelector(`[data-code-for="${verify.dataset.verify}"]`);const result=await request(`/deliveries/${verify.dataset.verify}/verify`,{method:'POST',body:JSON.stringify({code:input.value})});notify(result.message);await loadState();return switchTab('review')}
    if(expire){const result=await request(`/deliveries/${expire.dataset.expire}/expire`,{method:'POST',body:'{}'});notify(result.message);return loadState()}
    if(resend){const result=await request(`/deliveries/${resend.dataset.resend}/resend`,{method:'POST',body:'{}'});notify(result.message);return loadState()}
    if(review){const result=await request(`/applications/${review.dataset.id}/review`,{method:'POST',body:JSON.stringify({action:review.dataset.review,version:Number(review.dataset.version)})});notify(result.message);await loadState();return switchTab(review.dataset.review==='approve'?'users':'audit')}
    if(userStatus){const result=await request(`/users/${userStatus.dataset.id}/status`,{method:'POST',body:JSON.stringify({status:userStatus.dataset.userStatus,version:Number(userStatus.dataset.version)})});notify(result.message);return loadState()}
  }catch(error){notify(error.message,true);await loadState()}
});
$('#login-form').addEventListener('submit',async event=>{event.preventDefault();const button=event.submitter;button.disabled=true;try{const result=await request('/login',{method:'POST',body:JSON.stringify(formPayload(event.currentTarget))});$('#login-result').textContent=result.message;notify(result.message)}catch(error){$('#login-result').textContent=error.message;notify(error.message,true)}finally{event.currentTarget.elements.password.value='';button.disabled=false;await loadState()}});
$('#seed-scenarios').addEventListener('click',async event=>{event.currentTarget.disabled=true;try{const result=await request('/demo/scenarios',{method:'POST',body:'{}'});notify(`${result.message} 驗收密碼顯示於操作說明，不寫入紀錄。`);await loadState();switchTab('audit')}catch(error){notify(error.message,true)}finally{event.currentTarget.disabled=false}});

document.querySelectorAll('.prompt-host').forEach(host=>host.innerHTML=`<section class="prompt-box"><header><h3>可複製的自然語言 Prompt</h3><button data-copy-prompt type="button">複製 Prompt</button></header><pre>${escapeHtml(PROMPT)}</pre></section>`);
document.addEventListener('click',async event=>{if(event.target.matches('[data-copy-prompt]')){await navigator.clipboard.writeText(PROMPT);event.target.textContent='已複製';setTimeout(()=>event.target.textContent='複製 Prompt',1200)}});
loadState();

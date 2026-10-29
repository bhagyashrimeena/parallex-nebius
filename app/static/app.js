/* PARALLAX Studio — no frontend build tooling required. */
(() => {
  'use strict';
  const $ = (id) => document.getElementById(id);
  const state = { files: [], session: null, busy: false, live: false, toastTimeout: null };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function showToast(message, error=false) {
    const toast = $('toast'); toast.textContent = message; toast.classList.toggle('error', error); toast.classList.remove('hidden');
    clearTimeout(state.toastTimeout); state.toastTimeout = setTimeout(() => toast.classList.add('hidden'), 6000);
  }
  async function request(path, options = {}) {
    let response;
    try { response = await fetch(path, options); }
    catch { throw new Error('Cannot reach PARALLAX server. Check the app is running.'); }
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === 'string' ? body.detail : `Request failed (${response.status})`);
    return body;
  }
  function clock() { $('clock').textContent = new Date().toLocaleTimeString('en-IN', {hour:'2-digit',minute:'2-digit',hour12:false,timeZone:'Asia/Kolkata'}) + ' IST'; }
  clock(); setInterval(clock, 60_000);
  async function config() {
    try {
      const health = await request('/api/health');
      state.live = health.nebius_configured;
      const badge = $('modelBadge'); badge.classList.add(state.live ? 'is-live' : 'is-offline');
      badge.innerHTML = `<span class="status-light"></span>${state.live ? 'Nebius configured · AI ready' : 'Offline · key required for AI'}`;
    } catch { $('modelBadge').textContent = 'Server unavailable'; }
  }
  config();
  function setBusy(value) {
    state.busy = value; $('runBtn').disabled = value || state.files.length === 0;
    $('runBtn').innerHTML = value ? 'Inspecting evidence <span>◌</span>' : 'Analyze evidence <span>↗</span>';
  }
  function addFiles(newFiles) {
    if (state.busy) return;
    for (const file of newFiles) {
      if (!['image/jpeg','image/png','image/webp'].includes(file.type)) { showToast(`${file.name} is not a JPG, PNG or WebP.`, true); continue; }
      if (file.size > 8*1024*1024) { showToast(`${file.name} exceeds 8 MB.`, true); continue; }
      if (state.files.length >= 6) { showToast('Maximum of 6 images per inspection.', true); break; }
      if (state.files.some((item) => item.name === file.name && item.size === file.size)) continue;
      state.files.push(file);
    }
    renderPreviews();
  }
  function renderPreviews() {
    const gallery = $('previewGallery'); gallery.replaceChildren();
    gallery.classList.toggle('hidden', state.files.length === 0);
    state.files.forEach((file, index) => {
      const wrapper = document.createElement('div'); wrapper.className = 'preview-item';
      const img = document.createElement('img'); img.alt = `Selected evidence ${index+1}: ${file.name}`;
      const url = URL.createObjectURL(file); img.src = url; img.onload = () => URL.revokeObjectURL(url);
      const remove = document.createElement('button'); remove.textContent = `P-${String(index+1).padStart(2,'0')} · Remove`;
      remove.addEventListener('click', () => {state.files.splice(index,1);renderPreviews();});
      wrapper.append(img,remove); gallery.append(wrapper);
    });
    $('evidenceCount').textContent = String(state.files.length).padStart(2,'0');
    $('qualitySignal').textContent = state.files.length ? 'Pending validation' : 'Awaiting photos';
    setBusy(false);
  }
  const zone = $('dropZone');
  zone.addEventListener('click', () => $('fileInput').click());
  zone.addEventListener('keydown', (ev) => { if(ev.key==='Enter'||ev.key===' ') {ev.preventDefault();$('fileInput').click();} });
  $('fileInput').addEventListener('change', (ev) => {addFiles([...ev.target.files]); ev.target.value='';});
  for (const name of ['dragenter','dragover']) zone.addEventListener(name,(ev)=>{ev.preventDefault();zone.classList.add('drag');});
  for (const name of ['dragleave','drop']) zone.addEventListener(name,(ev)=>{ev.preventDefault();zone.classList.remove('drag');});
  zone.addEventListener('drop', (ev)=>addFiles([...ev.dataTransfer.files]));
  function step(active) {
    for(const [i,id] of ['stepCapture','stepAnalyze','stepResolve','stepReport'].entries()) $(id).classList.toggle('current',i===active);
  }
  function reset() {
    state.session=null;state.files=[];renderPreviews();
    ['resultPanel','nextPanel','reportPanel'].forEach(id=>$(id).classList.add('hidden'));
    $('category').value = 'Equipment & assets';
    $('objective').value = 'Document visible condition and outstanding uncertainty';
    $('verifiedSignal').textContent = '—'; $('uncertaintySignal').textContent = '—';
    $('reviewSignal').textContent='Not started'; step(0); window.scrollTo({top:0,behavior:'smooth'});
  }
  $('navNew').addEventListener('click',reset);
  $('navWorkspace').addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
  function updateDashboard(record) {
    $('evidenceCount').textContent=String(record.photos.length).padStart(2,'0');
    const problemCount=record.photos.filter(p=>p.quality.flags.length>0).length;
    $('qualitySignal').textContent=problemCount ? `${problemCount} needs attention` : 'Basic checks passed';
    $('verifiedSignal').textContent=record.result ? `${record.result.findings.length} linked` : '—';
    $('uncertaintySignal').textContent=record.result ? String(record.result.uncertainties.length) : '—';
    $('reviewSignal').textContent=record.result ? `${record.result.findings.filter(f=>f.review_status!=='unreviewed').length} / ${record.result.findings.length} reviewed` : 'Not started';
  }
  function renderResults(record) {
    state.session=record; updateDashboard(record);
    const result=record.result;if(!result)return;
    $('resultPanel').classList.remove('hidden');$('nextPanel').classList.remove('hidden');$('reportPanel').classList.remove('hidden');
    $('caseLabel').textContent= record.id==='demo'?'SYNTHETIC DEMO':`CASE / ${record.id.slice(0,8).toUpperCase()}`;
    $('modeTitle').textContent= result.mode==='live'?'LIVE NVIDIA ANALYSIS · HUMAN REVIEW REQUIRED':'SAMPLE ONLY · NO MODEL INFERENCE';
    $('summaryText').textContent=result.summary;
    $('findingsCount').textContent=`${result.findings.length} EVIDENCE-LINKED OBSERVATION${result.findings.length===1?'':'S'}`;
    $('traceText').textContent=result.mode==='live'?`${result.trace.length} LIVE MODEL CALLS`:'SYNTHETIC FIXTURE';
    const list=$('findingList');list.replaceChildren();
    result.findings.forEach(finding=>{
      const node=document.createElement('article');node.className='finding-card';
      node.innerHTML=`<div class="finding-top"><span class="finding-num">${esc(finding.id)} / EVIDENCE TRACE</span><span class="priority ${esc(finding.priority)}">${esc(finding.priority)} priority</span></div>
      <h3 class="finding-title">${esc(finding.title)}</h3><p class="finding-desc"><strong>Observed:</strong> ${esc(finding.observation)}</p>
      <p class="finding-desc"><strong>Possible interpretation:</strong> ${esc(finding.interpretation||'Not established')}</p>
      <div>${finding.evidence_ids.map(pid=>`<span class="evidence-ref">↗ ${esc(pid)}</span>`).join('')}</div>
      <div class="review-row"><span class="review-label">HUMAN REVIEW</span>${[['confirmed','Confirm'],['rejected','Reject'],['needs_more_evidence','Need more']].map(([status,label])=>`<button class="review-button ${finding.review_status===status?'selected':''}" data-finding="${esc(finding.id)}" data-review="${status}" ${record.id==='demo'?'disabled title="Demo fixture only"':''}>${label}</button>`).join('')}</div>`;
      list.append(node);
    });
    if(result.uncertainties.length){const box=document.createElement('div');box.className='uncertainty-box';box.innerHTML=`<b>◌ OPEN EVIDENCE GAPS · ${result.uncertainties.length}</b>${result.uncertainties.map(x=>`<p>— ${esc(x)}</p>`).join('')}`;list.append(box);}
    list.querySelectorAll('[data-review]').forEach(button=>button.addEventListener('click',async()=>{
      if(state.session?.id==='demo')return;
      button.disabled=true;
      try {const updated=await request(`/api/sessions/${state.session.id}/review`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({finding_id:button.dataset.finding,status:button.dataset.review,note:''})});renderResults(updated);showToast('Human review saved to the inspection record.');}
      catch(error){showToast(error.message,true);button.disabled=false;}
    }));
    $('nextTitle').textContent=result.next_shot?.title||'Capture a clearer second angle';
    $('nextInstruction').textContent=result.next_shot?.instruction||'Photograph the object from a new angle.';
    $('nextReason').textContent=result.next_shot?.reason||'Reduce uncertainty.';
    $('nextQuestion').textContent=result.next_shot?.question||'What additional evidence is needed?';
    $('followupBtn').disabled=record.id==='demo'||record.photos.length>=6;
    $('followupBtn').textContent=record.photos.length>=6?'6-photo limit reached':'+ Add follow-up photo';
    step(2);$('resultPanel').scrollIntoView({behavior:'smooth',block:'start'});
  }
  $('runBtn').addEventListener('click',async()=>{
    if(state.busy||!state.files.length)return;
    setBusy(true);step(1);
    try{
      const data=new FormData();data.append('category',$('category').value);data.append('objective',$('objective').value);
      for(const file of state.files)data.append('files',file,file.name);
      const created=await request('/api/sessions',{method:'POST',body:data});state.session=created;updateDashboard(created);
      if(!state.live){
        showToast('Images saved and quality-checked. Live AI needs a server-side NEBIUS_API_KEY. The sample case is available offline.',true);
        step(0);return;
      }
      const finished=await request(`/api/sessions/${created.id}/analyze`,{method:'POST'});
      renderResults(finished);showToast('Live visual analysis completed. Review the findings and next-shot plan.');
    }catch(error){showToast(error.message,true);step(0);}finally{setBusy(false);}
  });
  $('followupBtn').addEventListener('click',()=> $('followupInput').click());
  $('followupInput').addEventListener('change',async(ev)=>{
    const file=ev.target.files?.[0]; ev.target.value='';
    if(!file || !state.session || state.session.id==='demo')return;
    const sid=state.session.id;
    const data=new FormData();data.append('files',file,file.name);
    $('followupBtn').disabled=true;$('followupBtn').textContent='Adding evidence...';
    try {
      const updated=await request(`/api/sessions/${sid}/photos`,{method:'POST',body:data});
      state.session=updated;updateDashboard(updated);
      if(!state.live){showToast('Follow-up photo saved. Configure the Nebius key for reanalysis.',true);return;}
      $('followupBtn').textContent='Reanalyzing...';
      const result=await request(`/api/sessions/${sid}/analyze`,{method:'POST'});
      renderResults(result);showToast('New evidence analyzed; previous model run preserved in the exported audit trail.');
    } catch(error){showToast(error.message,true);} finally {
      $('followupBtn').disabled=false;$('followupBtn').textContent='+ Add follow-up photo';
    }
  });
  $('sampleBtn').addEventListener('click',async()=>{
    try{const record=await request('/api/demo');reset();$('category').value=record.category;$('objective').value=record.objective;renderResults(record);showToast('Synthetic sample loaded. No live NVIDIA inference was performed.');}
    catch(error){showToast(error.message,true);}
  });
  $('exportBtn').addEventListener('click',()=>{
    if(!state.session)return;
    if(state.session.id==='demo'){
      const blob=new Blob([JSON.stringify(state.session,null,2)],{type:'application/json'});const url=URL.createObjectURL(blob);const a=document.createElement('a');a.href=url;a.download='parallax-synthetic-demo.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);return;
    }
    const a=document.createElement('a');a.href=`/api/sessions/${state.session.id}/export`;a.download='inspection.json';a.click();
  });
  $('printBtn').addEventListener('click',()=>window.print());
  $('closeLightbox').addEventListener('click',()=>$('lightbox').classList.add('hidden'));
  $('lightbox').addEventListener('click',ev=>{if(ev.target===$('lightbox'))$('lightbox').classList.add('hidden');});
  document.addEventListener('keydown',ev=>{if(ev.key==='Escape')$('lightbox').classList.add('hidden');});
  document.addEventListener('click',ev=>{
    const photo=ev.target.closest('.evidence-ref');
    if(!photo||!state.session)return;
    const pid=photo.textContent.replace('↗','').trim();const p=state.session.photos.find(x=>x.id===pid);if(!p)return;
    $('modalImg').src=p.url;$('lightbox').classList.remove('hidden');
  });
})();

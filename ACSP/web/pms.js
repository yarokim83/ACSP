'use strict';
let code = '', noticeTimer, refreshTimer;
const $ = id => document.getElementById(id);
function notify(text, error=false) {
  clearTimeout(noticeTimer); $('message').textContent = text; $('message').classList.toggle('error', error); $('message').hidden = false;
  noticeTimer = setTimeout(() => $('message').hidden = true, error ? 10000 : 5000);
}
async function api(path, options={}) {
  const response = await fetch(path, {...options, headers: {'Authorization': 'Bearer '+code, 'Content-Type': 'application/json'}, signal: AbortSignal.timeout(15000)});
  const data = await response.json();
  if (!response.ok) {
    if (response.status === 401) logout();
    throw new Error(data.error || '요청에 실패했습니다.');
  }
  return data;
}
function failure(error) { notify(error.message || '관리 PC 연결을 확인하세요.', true); }
function page(name) {
  document.querySelectorAll('.page').forEach(el => el.hidden = el.id !== name);
  document.querySelectorAll('nav button').forEach(el => el.classList.toggle('active', el.dataset.page === name));
  if (name === 'history') loadHistory().catch(failure);
  if (name === 'status') loadStatus().catch(failure);
}
function option(select, value, label=value) { const el = document.createElement('option'); el.value = value; el.textContent = label; select.append(el); }
function localDate() { const d = new Date(); return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`; }
async function loadStatus(initialize=false) {
  const data = await api('/api/status');
  if (initialize) {
    $('equipment').replaceChildren(); $('filter-equipment').replaceChildren(); $('filter-task').replaceChildren();
    option($('filter-equipment'), '', '전체'); option($('filter-task'), 'PMS', '통합 PMS');
    data.equipment.forEach(eq => {option($('equipment'), eq); option($('filter-equipment'), eq);});
    option($('filter-task'), '분류별 보관 이력');
    $('maintenance-date').value = localDate(); $('maintenance-date').max = localDate();
  }
  const counts = {};
  data.status.forEach(job => counts[job.status] = (counts[job.status] || 0) + 1);
  $('summary').textContent = `${data.equipment.length}호기 · 통합 PMS | 지연 ${counts['지연']||0} · 임박 ${counts['임박']||0} · 미등록 ${counts['미등록']||0} | 15초마다 현황 갱신`;
  $('matrix').replaceChildren();
  for (const eq of data.equipment) {
    const row = document.createElement('tr'), first = document.createElement('td'); first.textContent = eq; row.append(first);
    for (const task of data.tasks) {
      const job = data.status.find(j => j.equipment_id === eq && j.task === task);
      const cell = document.createElement('td'), button = document.createElement('button');
      button.type = 'button'; button.textContent = job.maintenance_date || '시행 실적 없음';
      const workers = document.createElement('small'); workers.textContent = job.workers || '—';
      const badge = document.createElement('span'); badge.className = 'badge '+job.status;
      badge.textContent = job.status + (job.remaining === null ? '' : job.remaining < 0 ? ` · ${-job.remaining}일 초과` : ` · ${job.remaining}일 남음`);
      button.title = job.next_date ? `다음 예정일: ${job.next_date}` : '시행일을 입력하세요';
      button.append(workers, badge); button.onclick = () => {$('equipment').value = eq; $('task').value = task; page('entry');};
      cell.append(button); row.append(cell);
    }
    $('matrix').append(row);
  }
}
async function loadHistory() {
  const query = new URLSearchParams(new FormData($('filter-form')));
  const data = await api('/api/history?'+query);
  $('history-rows').replaceChildren(); $('count').textContent = `${data.records.length}건`;
  if (!data.records.length) {
    const tr = document.createElement('tr'), td = document.createElement('td'); td.colSpan=5; td.textContent='조회 조건에 맞는 시행 실적이 없습니다.'; tr.append(td); $('history-rows').append(tr);
  }
  data.records.forEach(record => {
    const row = document.createElement('tr');
    ['maintenance_date','equipment_id','task','workers','notes'].forEach(key => {const cell = document.createElement('td'); cell.textContent = record[key]; row.append(cell);});
    $('history-rows').append(row);
  });
}
function logout() { code=''; clearInterval(refreshTimer); $('workspace').hidden=true; $('login').hidden=false; $('access-code').value=''; }
$('login-form').onsubmit = async event => {
  event.preventDefault(); code = $('access-code').value.trim();
  try {await loadStatus(true); $('workspace').hidden=false; $('login').hidden=true; $('access-code').value=''; page('status'); clearInterval(refreshTimer); refreshTimer=setInterval(()=>{if (!$('status').hidden) loadStatus().catch(failure);},15000);} catch(error) {failure(error);}
};
$('entry-form').onsubmit = async event => {
  event.preventDefault(); $('save').disabled = true;
  const values = Object.fromEntries(new FormData(event.target)); values.equipment_id=Number(values.equipment_id);
  try {
    await api('/api/history', {method:'POST', body:JSON.stringify(values)});
    $('filter-form').reset();
    $('filter-equipment').value=String(values.equipment_id);
    $('filter-task').value=values.task;
    notify(`QC ${values.equipment_id} / ${values.task} / ${values.maintenance_date} 실적을 저장했습니다.`);
    page('history');
  } catch(error) {failure(error);} finally {$('save').disabled=false;}
};
$('filter-form').onsubmit = event => {event.preventDefault(); loadHistory().catch(failure);};
$('refresh').onclick = () => loadStatus().catch(failure);
$('logout').onclick = logout;
document.querySelectorAll('nav button').forEach(el => el.onclick = () => page(el.dataset.page));

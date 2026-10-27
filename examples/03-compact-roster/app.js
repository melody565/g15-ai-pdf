const projects = [
  { name: '晨光閱讀推廣', short: '晨光', type: '教育合作', owner: '知識企劃組', city: '臺北市', status: '進行中', priority: '高', rating: 4.8, progress: 78, updated: '今天 09:20', order: 6, color: '#167d68' },
  { name: '河岸友善市集', short: '河岸', type: '地方創生', owner: '社群營運組', city: '新北市', status: '待確認', priority: '中', rating: 4.5, progress: 42, updated: '昨天 16:45', order: 5, color: '#3a718d' },
  { name: '島嶼設計週', short: '島嶼', type: '設計策展', owner: '視覺設計組', city: '臺中市', status: '進行中', priority: '高', rating: 4.9, progress: 66, updated: '10 月 25 日', order: 4, color: '#98655d' },
  { name: '綠色辦公提案', short: '綠辦', type: '永續顧問', owner: '研究策略組', city: '新竹市', status: '已完成', priority: '低', rating: 4.6, progress: 100, updated: '10 月 23 日', order: 3, color: '#64784f' },
  { name: '港都文化散步', short: '港都', type: '文化體驗', owner: '內容編輯組', city: '高雄市', status: '進行中', priority: '中', rating: 4.7, progress: 58, updated: '10 月 21 日', order: 2, color: '#7a66a5' },
  { name: '田野影像紀錄', short: '田野', type: '影像製作', owner: '影音製作組', city: '臺南市', status: '待確認', priority: '低', rating: 4.3, progress: 35, updated: '10 月 18 日', order: 1, color: '#b07632' }
];

const roster = document.querySelector('#roster');
const search = document.querySelector('#search');
const statusFilter = document.querySelector('#status-filter');
const sortBy = document.querySelector('#sort-by');
const visibleCount = document.querySelector('#visible-count');
const resultMessage = document.querySelector('#result-message');
const priorityValue = { 高: 3, 中: 2, 低: 1 };
const statusClass = { 進行中: 'status-active', 待確認: 'status-waiting', 已完成: 'status-done' };

function render() {
  const keyword = search.value.trim().toLowerCase();
  const status = statusFilter.value;
  const sort = sortBy.value;
  const rows = projects
    .filter(item => !status || item.status === status)
    .filter(item => !keyword || [item.name, item.type, item.owner, item.city].some(value => value.toLowerCase().includes(keyword)))
    .sort((a, b) => {
      if (sort === 'priority') return priorityValue[b.priority] - priorityValue[a.priority];
      if (sort === 'progress') return b.progress - a.progress;
      if (sort === 'rating') return b.rating - a.rating;
      return b.order - a.order;
    });

  visibleCount.textContent = rows.length;
  resultMessage.textContent = rows.length ? `顯示 ${rows.length} 筆虛構資料` : '沒有符合條件的項目';
  roster.innerHTML = rows.length ? rows.map(item => `
    <article class="roster-row">
      <div class="identity">
        <span class="avatar" style="--avatar:${item.color}" aria-hidden="true">${item.short}</span>
        <div><h3 class="name">${item.name}</h3><p class="owner">負責人：${item.owner}</p></div>
      </div>
      <div class="meta"><span>${item.type}</span><small>${item.city}</small></div>
      <div class="state"><span class="badge ${statusClass[item.status]}">${item.status}</span><div class="priority">${item.priority}優先</div></div>
      <div class="score"><b>★ ${item.rating.toFixed(1)}</b><small>5 分制</small></div>
      <div class="progress" aria-label="完成度 ${item.progress}%"><span class="progress-track"><i style="--progress:${item.progress}%"></i></span><b>${item.progress}%</b></div>
      <time class="updated">${item.updated}</time>
    </article>`).join('') : '<p class="empty">請調整搜尋文字或狀態篩選。</p>';
}

[search, statusFilter, sortBy].forEach(control => control.addEventListener('input', render));
render();

(() => {
  const customerNav = document.querySelector('[data-nav="客戶管理"]');
  const globalSearch = document.querySelector('#global-search');
  const globalSearchInput = document.querySelector('#global-search-input');

  customerNav.addEventListener('click', () => {
    customerNav.dataset.nav = '客戶查詢';
  }, { capture: true });

  customerNav.addEventListener('click', () => {
    customerNav.dataset.nav = '客戶管理';
    document.querySelector('#current-page').textContent = '客戶管理';
    document.querySelector('#page-title').textContent = '客戶管理';
  });

  globalSearch.addEventListener('submit', event => {
    event.preventDefault();
    customerNav.click();
    document.querySelector('#search').value = globalSearchInput.value.trim();
    page = 1;
    render();
    document.querySelector('#search').focus();
  });

  document.querySelector('#notifications').addEventListener('click', () => {
    message('通知中心 · 示範模式', '目前顯示 3 則介面示範通知。本原型未連接通知服務，也不會寄信或更新真實帳號狀態。');
  });
})();

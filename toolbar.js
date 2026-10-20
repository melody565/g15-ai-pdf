(() => {
  const globalSearch = document.querySelector('#global-search');
  const globalSearchInput = document.querySelector('#global-search-input');

  globalSearch.addEventListener('submit', event => {
    event.preventDefault();
    showWorkspaceView('customers');
    document.querySelector('#search').value = globalSearchInput.value.trim();
    page = 1;
    render();
    document.querySelector('#search').focus();
  });

  document.querySelector('#notifications').addEventListener('click', () => {
    message('通知中心 · Demo', '3 則虛構通知：專案申請模組已上線、產品需求規格書已完成示範分析、5 位潛在客戶待聯繫。');
  });
})();

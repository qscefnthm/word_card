'use strict';
// The home landing never touches the legacy stores. Load the unchanged legacy
// application only when its preserved index.html section is opened.
(() => {
  const legacy = document.getElementById('legacy');
  let started = false;
  function startLegacy() {
    if (!legacy.open || started) return;
    started = true;
    const script = document.createElement('script');
    script.src = './assets/app.js?v=20260927-audit';
    script.onload = () => {
      const requested = new URLSearchParams(location.search).get('deck');
      if (!requested) return;
      const select = document.getElementById('deckSelect');
      const observer = new MutationObserver(selectRequested);
      function selectRequested() {
        if (select.disabled) return;
        observer.disconnect();
        if ([...select.options].some(option => option.value === requested) && select.value !== requested) {
          select.value = requested;
          select.dispatchEvent(new Event('change', {bubbles:true}));
        }
      }
      observer.observe(select, {childList:true,attributes:true});
      selectRequested();
    };
    script.onerror = () => {
      started = false;
      document.getElementById('loadingMessage').textContent = '旧词卡脚本暂未加载成功，请关闭后重新展开。原有记录未被清空。';
    };
    document.body.append(script);
  }
  function route() {
    if (location.hash === '#legacy' || new URLSearchParams(location.search).has('deck')) {
      legacy.open = true;
      startLegacy();
    }
  }
  legacy.addEventListener('toggle', startLegacy);
  window.addEventListener('hashchange', route);
  route();
})();

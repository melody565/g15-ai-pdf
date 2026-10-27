const order = Object.freeze({
  orderNumber: 'DEMO-TW-20261012-037',
  status: 'paid',
  createdAtUtc: '2026-10-12T15:30:00.000Z',
  currency: 'TWD',
  totalMinor: 1203792,
  items: [
    { productKey: 'productLamp', quantity: 2, unitPriceMinor: 498000 },
    { productKey: 'productShelf', quantity: 1, unitPriceMinor: 207792 }
  ]
});

const presets = [
  { id: 'taiwan', title: '臺灣繁中展示', prompt: '請用繁體中文顯示訂單，日期與金額採臺灣格式，時間顯示 Asia/Taipei。', language: 'zh-TW', locale: 'zh-TW', timezone: 'Asia/Taipei', missing: false },
  { id: 'english', title: '英文介面、臺灣格式', prompt: '請把訂單介面切換成英文，但日期、數字與金額仍使用臺灣地區格式。', language: 'en-US', locale: 'zh-TW', timezone: 'Asia/Taipei', missing: false },
  { id: 'japan', title: '日文與日本格式', prompt: '請用日文顯示相同訂單，套用日本地區格式，時間仍顯示臺北時區。', language: 'ja-JP', locale: 'ja-JP', timezone: 'Asia/Taipei', missing: false },
  { id: 'fallback', title: '缺譯 fallback 驗證', prompt: '請切換英文介面並模擬一筆商品名稱缺譯，退回繁體中文並清楚標示。', language: 'en-US', locale: 'en-US', timezone: 'UTC', missing: true }
];

const languageSelect = document.querySelector('#language-select');
const localeSelect = document.querySelector('#locale-select');
const timezoneSelect = document.querySelector('#timezone-select');
const missingToggle = document.querySelector('#missing-toggle');
const preview = document.querySelector('#order-preview');
const activeConfig = document.querySelector('#active-config');
const presetList = document.querySelector('#presets');

document.querySelector('#raw-json').textContent = JSON.stringify(order, null, 2);

function createTranslator(language, simulateMissing) {
  const selected = ORDER_TRANSLATIONS[language] || {};
  const fallback = ORDER_TRANSLATIONS['zh-TW'];
  const missing = [];
  return {
    missing,
    text(key) {
      const intentionallyMissing = simulateMissing && key === 'productShelf';
      if (!intentionallyMissing && selected[key]) return selected[key];
      missing.push(key);
      return fallback[key] || `⟦${key}⟧`;
    }
  };
}

function formatDate(value, locale, timezone) {
  return new Intl.DateTimeFormat(locale, {
    timeZone: timezone,
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
    hour12: false, hourCycle: 'h23'
  }).format(new Date(value));
}

function formatMoney(minor, locale, currency) {
  return new Intl.NumberFormat(locale, {
    style: 'currency', currency,
    useGrouping: true,
    minimumFractionDigits: 2,
    maximumFractionDigits: 2
  }).format(minor / 100);
}

function formatInteger(value, locale) {
  return new Intl.NumberFormat(locale, { maximumFractionDigits: 0 }).format(value);
}

function escapeHtml(value) {
  return String(value).replace(/[&<>'"]/g, character => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[character]);
}

function renderPreview() {
  const language = languageSelect.value;
  const locale = localeSelect.value;
  const timezone = timezoneSelect.value;
  const translator = createTranslator(language, missingToggle.checked);
  const t = key => translator.text(key);

  const rows = order.items.map(item => {
    const subtotal = item.quantity * item.unitPriceMinor;
    return `<tr>
      <td data-label="${escapeHtml(t('item'))}"><strong>${escapeHtml(t(item.productKey))}</strong>${translator.missing.includes(item.productKey) ? '<mark class="missing-mark">fallback · zh-TW</mark>' : ''}</td>
      <td data-label="${escapeHtml(t('quantity'))}">${formatInteger(item.quantity, locale)}</td>
      <td data-label="${escapeHtml(t('unitPrice'))}">${escapeHtml(formatMoney(item.unitPriceMinor, locale, order.currency))}</td>
      <td data-label="${escapeHtml(t('subtotal'))}">${escapeHtml(formatMoney(subtotal, locale, order.currency))}</td>
    </tr>`;
  }).join('');

  preview.lang = language;
  preview.dir = 'ltr';
  preview.innerHTML = `
    <div class="order-topline"><div><p class="preview-eyebrow">AI-DEMO ORDER</p><h2>${escapeHtml(t('orderTitle'))}</h2></div><span class="status-chip">${escapeHtml(t('statusPaid'))}</span></div>
    <p class="preview-notice">${escapeHtml(t('demoNotice'))}</p>
    <dl class="order-meta">
      <div><dt>${escapeHtml(t('orderNumber'))}</dt><dd><bdi>${escapeHtml(order.orderNumber)}</bdi></dd></div>
      <div><dt>${escapeHtml(t('orderedAt'))}</dt><dd>${escapeHtml(formatDate(order.createdAtUtc, locale, timezone))}</dd></div>
      <div><dt>${escapeHtml(t('timeZone'))}</dt><dd><bdi>${escapeHtml(timezone)}</bdi></dd></div>
      <div><dt>${escapeHtml(t('currency'))}</dt><dd><bdi>${escapeHtml(order.currency)}</bdi></dd></div>
    </dl>
    <div class="table-scroll"><table><thead><tr><th>${escapeHtml(t('item'))}</th><th>${escapeHtml(t('quantity'))}</th><th>${escapeHtml(t('unitPrice'))}</th><th>${escapeHtml(t('subtotal'))}</th></tr></thead><tbody>${rows}</tbody></table></div>
    <div class="order-total"><span>${escapeHtml(t('total'))}</span><strong>${escapeHtml(formatMoney(order.totalMinor, locale, order.currency))}</strong></div>
    ${translator.missing.length ? `<p class="fallback-alert" role="status"><b>${escapeHtml(t('fallbackNotice'))}</b> ${[...new Set(translator.missing)].map(escapeHtml).join('、')}</p>` : ''}
    <button type="button" class="preview-action">${escapeHtml(t('action'))}</button>`;

  activeConfig.textContent = `${language} · ${locale} · ${timezone}`;
  document.querySelectorAll('.preset-card').forEach(card => card.classList.toggle('active', card.dataset.preset === currentPresetId()));
}

function currentPresetId() {
  const match = presets.find(item => item.language === languageSelect.value && item.locale === localeSelect.value && item.timezone === timezoneSelect.value && item.missing === missingToggle.checked);
  return match ? match.id : '';
}

function applyPreset(preset) {
  languageSelect.value = preset.language;
  localeSelect.value = preset.locale;
  timezoneSelect.value = preset.timezone;
  missingToggle.checked = preset.missing;
  renderPreview();
}

presetList.innerHTML = presets.map((preset, index) => `<button class="preset-card${index === 0 ? ' active' : ''}" data-preset="${preset.id}" type="button"><span>條件 ${index + 1}</span><strong>${preset.title}</strong><small>${preset.prompt}</small></button>`).join('');
presetList.addEventListener('click', event => {
  const button = event.target.closest('[data-preset]');
  if (button) applyPreset(presets.find(item => item.id === button.dataset.preset));
});
[languageSelect, localeSelect, timezoneSelect, missingToggle].forEach(control => control.addEventListener('input', renderPreview));
preview.addEventListener('click', event => {
  if (event.target.matches('.preview-action')) event.target.textContent = ORDER_TRANSLATIONS[preview.lang]?.action || ORDER_TRANSLATIONS['zh-TW'].action;
});
renderPreview();

/* Local-only UI helpers: no trackers, no third-party libraries. */
(function() {
  const safeSession = {
    setItem(k,v) {try {window.sessionStorage.setItem(k,v)} catch (_) {}},
    getItem(k) {try {return window.sessionStorage.getItem(k)} catch (_) {return null}},
    removeItem(k) {try {window.sessionStorage.removeItem(k)} catch (_) {}}
  };
  for (const target of document.querySelectorAll('form[data-confirm]')) {
    target.addEventListener('submit', event => {
      if (!confirm(target.dataset.confirm)) event.preventDefault();
    });
  }
  const form = document.getElementById('filter-form');
  if (form) {
    for (const el of form.querySelectorAll('select,input[type=month]')) {
      el.addEventListener('change', () => {
        if (el.name === 'currency') form.elements.account.value = '';
        form.submit();
      });
    }
  }

  const quick = document.getElementById('quick-filter-form');
  if (!quick) return;
  const input = document.getElementById('quick-filter');
  if (!input) return;
  let pending;
  function submitQuick() {
    // Ensure all searches start on page 1 and show the table, not the top of the page.
    safeSession.setItem('financisto-quick-focus', '1');
    quick.submit();
  }
  input.addEventListener('input', () => {
    clearTimeout(pending);
    pending = setTimeout(submitQuick, 4000); // Four seconds after the last keystroke; Search/Enter submits immediately.
  });
  quick.addEventListener('submit', () => {
    clearTimeout(pending);
    safeSession.setItem('financisto-quick-focus', '1');
  });
  if (safeSession.getItem('financisto-quick-focus') === '1' &&
      window.location.hash === '#buchungen') {
    safeSession.removeItem('financisto-quick-focus');
    input.focus({ preventScroll: true });
    input.setSelectionRange(input.value.length, input.value.length);
  }
})();

(function(){const btn=document.getElementById('print-report'); if(btn) btn.addEventListener('click',()=>window.print());})();

/* 1.7.0: mobile navigation & meaningful in-page links for collapsed sections. */
(function() {
  const toggle = document.querySelector('.mobile-menu-toggle');
  const nav = document.getElementById('mobile-nav');
  if (toggle && nav) {
    function setMenu(open) {
      nav.hidden = !open;
      toggle.setAttribute('aria-expanded', String(open));
      toggle.setAttribute('aria-label', open ? 'Menü schließen' : 'Menü öffnen');
    }
    setMenu(false);
    toggle.addEventListener('click', () => setMenu(nav.hidden));
    nav.querySelectorAll('a').forEach(link => link.addEventListener('click', () => setMenu(false)));
    document.addEventListener('keydown', event => {
      if (event.key === 'Escape' && !nav.hidden) {
        setMenu(false);
        toggle.focus();
      }
    });
  }
  const filter = document.getElementById('dashboard-filters');
  const historyFilter = document.getElementById('history-filters');
  const balances = document.getElementById('dashboard-balances');
  const charts = document.getElementById('dashboard-charts');
  const ledger = document.getElementById('dashboard-ledger');
  const cashflow = document.getElementById('dashboard-cashflow');
  function openHashTarget() {
    const hash = window.location.hash;
    let target;
    if ((hash === '#filter-form' || hash === '#dashboard-filters' || hash === '#filter-panel') && filter) {
      filter.open = true;
      target = hash === '#filter-form' ? document.getElementById('filter-form') : filter;
    } else if ((hash === '#filter-form' || hash === '#history-filters' || hash === '#historischer-filterbereich') && historyFilter) {
      historyFilter.open = true;
      target = hash === '#filter-form' ? document.getElementById('filter-form') : historyFilter;
    } else if ((hash === '#kontostaende' || hash === '#dashboard-balances') && balances) {
      balances.open = true;
      target = document.getElementById('kontostaende');
    } else if ((hash === '#ausgabenkategorien' || hash === '#dashboard-charts') && charts) {
      charts.open = true;
      target = document.getElementById('ausgabenkategorien');
    }
    else if ((hash === '#cashflow' || hash === '#dashboard-cashflow') && cashflow) {
      cashflow.open = true;
      target = document.getElementById('cashflow');
    }
    else if ((hash === '#buchungen' || hash === '#dashboard-ledger') && ledger) {
      ledger.open = true;
      target = document.getElementById('buchungen');
    }
    else if (hash === '#telegram-buchungen' || hash === '#benachrichtigungen') {
      // Keep the settings page compact on ordinary visits, but reveal a section
      // when the server redirects back to its anchor after saving a form.
      const section = document.getElementById(hash.slice(1));
      if (section && section.tagName === 'DETAILS') {
        section.open = true;
        target = section;
      }
    }
    if (target) requestAnimationFrame(() => target.scrollIntoView({block:'start'}));
  }
  window.addEventListener('hashchange', openHashTarget);
  openHashTarget();
})();

/* 1.9.1: exclusive settings accordion and context-aware booking fields. */
(function () {
  const sections = document.querySelectorAll('#stammdaten details.settings-list');
  for (const section of sections) {
    section.addEventListener('toggle', () => {
      if (!section.open) return;
      for (const other of sections) {
        if (other !== section) other.open = false;
      }
    });
  }
  const form = document.getElementById('booking-form');
  if (!form) return;
  const kind = form.querySelector('select[name="kind"]');
  const target = document.getElementById('booking-target-field');
  const category = document.getElementById('booking-category-field');
  const neutralSection = document.getElementById('booking-pass-through-field');
  const neutralCheck = neutralSection?.querySelector('input[name="pass_through"]');
  if (!kind || !target || !category) return;
  function update() {
    const transfer = kind.value === 'transfer';
    const advanced = document.getElementById('booking-extra');
    if (advanced) advanced.hidden = transfer;
    const neutral = !transfer && !!neutralCheck?.checked;
    target.hidden = !transfer;
    category.hidden = transfer || neutral;
    if (neutralSection) neutralSection.hidden = transfer;
    if (neutralCheck) neutralCheck.disabled = transfer;
    target.querySelector('select').disabled = !transfer;
    target.querySelector('select').required = transfer;
    category.querySelector('select').disabled = transfer || neutral;
    const categoryQuick = document.getElementById('booking-category-quick');
    if (categoryQuick) categoryQuick.hidden = transfer || neutral;
  }
  kind.addEventListener('change', () => {
    // On a fresh form use the shared default for expenses only; do not
    // reassign a stored category when editing or cloning an existing booking.
    if (form.dataset.newBooking === 'true') {
      const select = category.querySelector('select');
      if (select) {
        const candidate = kind.value === 'expense' ? select.dataset.defaultExpense : '';
        select.value = candidate && Array.from(select.options).some(option => option.value === candidate)
          ? candidate : '';
        select.dispatchEvent(new Event('change', {bubbles: true}));
      }
    }
    update();
  });
  neutralCheck?.addEventListener('change', update);
  update();
})();


/* 1.9.6: immediate in-browser master-data filters (no server requests). */
(function () {
  function canonical(value) {
    return String(value || '').normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLocaleLowerCase('de-DE').trim();
  }
  const kinds = {payees: 'Empfänger', categories: 'Kategorien', accounts: 'Konten'};
  for (const section of document.querySelectorAll('#stammdaten details[data-master-section]')) {
    const field = section.querySelector('[data-master-search]');
    const clear = section.querySelector('[data-master-clear]');
    const counter = section.querySelector('[data-master-count]');
    const empty = section.querySelector('[data-master-empty]');
    const rows = Array.from(section.querySelectorAll('[data-master-item]'));
    if (!field || !clear || !counter || !empty) continue;
    const kind = kinds[section.dataset.masterSection] || 'Einträge';
    const indexed = rows.map(row => ({row, text: canonical(row.dataset.searchName || row.textContent)}));
    function apply() {
      const search = canonical(field.value);
      let visible = 0;
      for (const item of indexed) {
        const match = !search || item.text.includes(search);
        item.row.hidden = !match;
        if (match) visible += 1;
      }
      counter.textContent = search
        ? `${visible} von ${indexed.length} ${kind} angezeigt`
        : `${indexed.length} ${kind} insgesamt`;
      empty.hidden = visible > 0;
      clear.hidden = !field.value;
    }
    field.addEventListener('input', apply);
    field.addEventListener('search', apply);
    clear.addEventListener('click', () => {
      field.value = '';
      apply();
      field.focus();
    });
    apply();
  }
})();

/* 1.9.11: edit recurring rules in an accessible dialog, near the selected row. */
(function () {
  const panel = document.getElementById('regel-formular');
  const source = document.getElementById('recurring-editor-data');
  if (!panel || !source || typeof HTMLDialogElement === 'undefined') return;
  const form = panel.querySelector('form');
  if (!form) return;
  let records = [];
  try { records = JSON.parse(source.textContent || '[]'); } catch (_) { return; }
  const byId = new Map(records.map(rule => [Number(rule.id), rule]));
  const dialog = document.createElement('dialog');
  dialog.className = 'recurring-form-dialog';
  dialog.setAttribute('aria-labelledby', 'recurring-editor-title');
  panel.parentNode.insertBefore(dialog, panel);
  dialog.appendChild(panel);
  const heading = document.getElementById('recurring-editor-title');
  const submit = document.getElementById('recurring-save-button');
  const close = panel.querySelector('[data-recurring-close]');
  if (close) {
    close.hidden = false;
    close.addEventListener('click', () => dialog.close());
  }
  dialog.addEventListener('click', event => {
    if (event.target === dialog) dialog.close();
  });
  function field(name, value) {
    const target = form.elements.namedItem(name);
    if (target) target.value = value == null ? '' : String(value);
  }
  const startDateInput = form.elements.namedItem('start_on');
  const monthDayInput = form.elements.namedItem('day_of_month');
  const frequencyInput = form.elements.namedItem('frequency');
  const monthDayRow = monthDayInput?.closest('.formgrid');
  let monthDayOverridden = false;
  const derivedMonthDay = () => {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(startDateInput?.value || '');
    return match ? String(Number(match[3])) : '';
  };
  function updateMonthDayVisibility() {
    if (!monthDayRow || !frequencyInput) return;
    const irrelevant = frequencyInput.value === 'daily' || frequencyInput.value === 'weekly';
    monthDayRow.hidden = irrelevant;
    monthDayRow.style.display = irrelevant ? 'none' : '';
  }
  startDateInput?.addEventListener('change', () => {
    if (!monthDayOverridden && monthDayInput) {
      const day = derivedMonthDay();
      if (day) monthDayInput.value = day;
    }
  });
  monthDayInput?.addEventListener('input', () => { monthDayOverridden = true; });
  frequencyInput?.addEventListener('change', updateMonthDayVisibility);
  function openEditor(rule, trigger) {
    form.reset();
    field('edit_id', rule ? rule.id : '');
    field('title', rule ? rule.title : '');
    field('kind', rule ? rule.kind : 'expense');
    field('account_id', rule ? rule.account_id : '');
    field('to_account_id', rule ? rule.to_account_id : '0');
    field('category_id', rule ? rule.category_id : '0');
    field('payee_title', rule ? (rule.payee_title || '') : '');
    const rawDigits = rule && rule.decimals != null ? Number(rule.decimals) : 2;
    const digits = Number.isInteger(rawDigits) && rawDigits >= 0 && rawDigits <= 6 ? rawDigits : 2;
    const amount = rule ? (Math.abs(Number(rule.amount_minor)) / Math.pow(10, digits)).toFixed(digits).replace('.', ',') : '';
    field('amount', amount);
    field('start_on', rule ? rule.start_on : new Date().toLocaleDateString('sv-SE'));
    field('run_at', rule ? (rule.run_at || '00:00') : '00:00');
    field('frequency', rule && rule.frequency !== 'custom' ? rule.frequency : 'monthly');
    field('interval_count', rule ? rule.interval_count : 1);
    // Existing rules preserve their independently configured month day.
    // For a new rule the date determines the default until the user edits it.
    monthDayOverridden = Boolean(rule);
    field('day_of_month', rule ? rule.day_of_month : (derivedMonthDay() || 1));
    updateMonthDayVisibility();
    field('end_on', rule ? (rule.end_on || '') : '');
    field('max_occurrences', rule ? (rule.max_occurrences || '') : '');
    field('note', rule ? rule.note : '');
    heading.textContent = rule ? `Regel bearbeiten: ${rule.title}` : 'Neue wiederkehrende Buchung';
    submit.textContent = rule ? 'Änderung speichern und deaktivieren' : 'Vorlage anlegen (deaktiviert)';
    dialog.showModal();
    dialog.querySelector('input[name="title"]')?.focus({preventScroll:true});
    if (trigger) dialog.addEventListener('close', () => trigger.focus({preventScroll:true}), {once:true});
  }
  for (const link of document.querySelectorAll('[data-recurring-edit]')) {
    link.addEventListener('click', event => {
      const rule = byId.get(Number(link.dataset.recurringEdit));
      if (!rule) return;
      event.preventDefault();
      openEditor(rule, link);
    });
  }
  const create = document.querySelector('[data-recurring-create]');
  if (create) create.addEventListener('click', event => {
    event.preventDefault();
    openEditor(null, create);
  });
  // Fallback URL from a non-JS browser remains usable if JS becomes available later.
  const selected = new URLSearchParams(window.location.search).get('edit');
  const chosen = selected && byId.get(Number(selected));
  if (chosen && window.location.hash === '#regel-formular') {
    openEditor(chosen, null);
  }
})();

/* 1.9.22: category creation without leaving the current booking form. */
(function () {
  const book = document.getElementById('booking-form');
  const dlg = document.getElementById('booking-category-dialog');
  const open = document.getElementById('booking-category-add');
  const mini = document.getElementById('booking-category-create');
  const category = document.getElementById('booking-category-select');
  const status = document.getElementById('booking-category-message');
  if (!book || !dlg || !open || !mini || !category || !status) return;
  const kind = book.querySelector('select[name="kind"]');
  const parent = mini.querySelector('select[name="parent_id"]');
  const title = mini.querySelector('input[name="title"]');
  function refreshParents() {
    const selectedKind = kind.value === 'income' ? '1' : '0';
    mini.elements.kind.value = kind.value;
    for (const option of parent.options) {
      if (!option.value) continue;
      option.hidden = option.dataset.kind !== selectedKind;
      option.disabled = option.dataset.kind !== selectedKind;
    }
    if (parent.selectedOptions[0]?.disabled) parent.value = '';
  }
  open.addEventListener('click', () => {
    if (kind.value === 'transfer') return;
    status.textContent = '';
    refreshParents();
    dlg.showModal();
    title.focus();
  });
  dlg.querySelector('[data-close-category]')?.addEventListener('click', () => dlg.close());
  dlg.addEventListener('click', event => { if (event.target === dlg) dlg.close(); });
  mini.addEventListener('submit', async event => {
    event.preventDefault();
    refreshParents();
    const submit = mini.querySelector('button[type="submit"]');
    submit.disabled = true;
    status.textContent = 'Kategorie wird angelegt …';
    try {
      const response = await fetch(mini.action, {
        method: 'POST', body: new FormData(mini),
        credentials: 'same-origin', headers: {Accept: 'application/json'}
      });
      const data = await response.json();
      if (!response.ok || !data.id) throw new Error(data.error || 'Kategorie konnte nicht angelegt werden.');
      category.add(new Option(data.title, String(data.id), true, true));
      const option = new Option(data.title, String(data.id));
      option.dataset.kind = String(data.kind);
      parent.add(option);
      // Select the new category, preserving all other booking fields.
      category.value = String(data.id);
      category.dispatchEvent(new Event('change', { bubbles: true }));
      dlg.close();
    } catch (error) {
      status.textContent = error.message || 'Anlegen fehlgeschlagen.';
    } finally {
      submit.disabled = false;
    }
  });
  kind.addEventListener('change', refreshParents);
})();

/* 1.9.23: shared, non-binding account reconciliation preview. */
(function () {
  for (const form of document.querySelectorAll('form[data-reconcile-form]')) {
    const account = form.querySelector('[data-reconcile-account]');
    const amount = form.querySelector('[data-reconcile-actual]');
    const preview = form.parentElement.querySelector('[data-reconcile-preview]');
    if (!account || !amount || !preview) continue;
    function update() {
      const option = account.selectedOptions[0];
      if (!option || !option.dataset.balance) {
        preview.textContent = 'Wähle ein Konto und gib den aktuellen Stand ein.';
        return;
      }
      const decimals = Number(option.dataset.decimals || '2');
      const unit = 10 ** decimals;
      const previousMinor = Number(option.dataset.balance);
      const nf = new Intl.NumberFormat('de-DE', {minimumFractionDigits: decimals, maximumFractionDigits: decimals});
      const display = value => nf.format(value / unit) + ' ' + option.dataset.code;
      const typed = amount.value.trim().replace(/\s/g, '');
      const normalized = typed.includes(',') ? typed.replace(/\./g, '').replace(',', '.') : typed;
      const validFormat = /^[-+]?\d+(?:\.\d+)?$/.test(normalized);
      const fractionDigits = normalized.split('.')[1]?.length || 0;
      const parsed = validFormat ? Number(normalized) : NaN;
      const actualMinor = Math.round(parsed * unit);
      if (!typed || !Number.isFinite(parsed) || fractionDigits > decimals || !Number.isSafeInteger(actualMinor)) {
        preview.textContent = 'Bisheriger Kontostand: ' + display(previousMinor);
        return;
      }
      const deltaMinor = actualMinor - previousMinor;
      preview.textContent = 'Bisher: ' + display(previousMinor) +
        ' · Korrektur: ' + (deltaMinor > 0 ? '+' : '') + display(deltaMinor);
    }
    account.addEventListener('change', update);
    amount.addEventListener('input', update);
    update();
  }
})();

/* 1.9.29: grow a booking note only when its content needs space. */
(function () {
  const note = document.querySelector('#booking-form textarea[name="note"]');
  if (!note) return;
  function resize() { note.style.height = 'auto'; note.style.height = Math.min(170, Math.max(41, note.scrollHeight)) + 'px'; }
  note.addEventListener('input', resize);
  resize();
})();

/* 1.9.45: Offline-localized, accessible file picker. The real input remains intact. */
(function(){
 for(const picker of document.querySelectorAll('.custom-file-picker')){
  const file=picker.querySelector('input[type="file"]'),label=picker.querySelector('.custom-file-picker-name');
  if(!file||!label)return;
  file.addEventListener('change',()=>{const name=file.files?.[0]?.name;label.textContent=name||window.FinancistoI18n?.translate(label.dataset.emptyLabel)||label.dataset.emptyLabel;});
 }
})();


/* 1.9.50: mobile-safe payee autocomplete. Avoid native <datalist> popups,
 * which may cover the entire Android form when the soft keyboard opens.
 * The free-text input and the submitted payee_title field are unchanged.
 */
(function () {
  const input = document.getElementById('booking-payee-input');
  const source = document.getElementById('known-payees');
  if (!input || !source || !input.closest('#booking-form')) return;

  // Existing known payees come only from escaped <option value="..."> fields.
  const suggestionLimit = Math.max(1, Math.min(100, Number.parseInt(input.closest('#booking-form').dataset.suggestionLimit || '20', 10) || 20));
  const payees = [...new Set(Array.from(source.querySelectorAll('option'))
    .map(option => option.value.trim()).filter(Boolean))];
  if (!payees.length) return;

  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const lang = document.documentElement.lang === 'en' ? 'en' : 'de';
  const list = document.createElement('div');
  list.id = 'booking-payee-suggestions';
  list.className = 'booking-payee-suggestions';
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', lang === 'en' ? 'Known payees' : 'Bekannte Empfänger');
  list.setAttribute('data-no-i18n', '');
  list.hidden = true;
  document.body.appendChild(list);
  let matches = [];
  let highlighted = -1;

  function close() {
    list.hidden = true;
    list.replaceChildren();
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    matches = [];
    highlighted = -1;
  }

  function choose(value) {
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    close();
    input.focus({ preventScroll: true });
  }

  function position() {
    if (list.hidden) return;
    const rect = input.getBoundingClientRect();
    const vv = window.visualViewport;
    const visibleTop = vv ? vv.offsetTop : 0;
    const visibleBottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const below = Math.max(0, visibleBottom - rect.bottom - 8);
    const above = Math.max(0, rect.top - visibleTop - 8);
    const openAbove = below < 160 && above > below;
    const available = openAbove ? above : below;
    if (available < 45) { list.hidden = true; input.setAttribute('aria-expanded', 'false'); return; }
    const maxHeight = Math.min(236, Math.floor(available));
    const desired = Math.min(maxHeight, matches.length * 45 + 6);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8));
    list.style.left = `${left}px`;
    list.style.width = `${Math.min(rect.width, window.innerWidth - left - 8)}px`;
    list.style.top = `${openAbove ? rect.top - desired - 4 : rect.bottom + 4}px`;
    list.style.maxHeight = `${maxHeight}px`;
    list.dataset.position = openAbove ? 'above' : 'below';
  }

  function highlight(index) {
    highlighted = index;
    Array.from(list.children).forEach((node, i) => {
      node.setAttribute('aria-selected', i === highlighted ? 'true' : 'false');
      if (i === highlighted) {
        input.setAttribute('aria-activedescendant', node.id);
        node.scrollIntoView({ block: 'nearest' });
      }
    });
    if (highlighted === -1) input.removeAttribute('aria-activedescendant');
  }

  function render(showAll = false) {
    // Opening the field shows known payees immediately; typing filters the list.
    const query = showAll ? '' : normalize(input.value.trim());
    if (document.activeElement !== input) { close(); return; }
    matches = payees.filter(name => normalize(name).includes(query))
      .sort((a, b) => {
        const aStart = normalize(a).startsWith(query);
        const bStart = normalize(b).startsWith(query);
        return aStart === bStart ? a.localeCompare(b, lang) : aStart ? -1 : 1;
      }).slice(0, suggestionLimit);
    if (!matches.length) { close(); return; }
    highlighted = -1;
    list.replaceChildren();
    matches.forEach((name, index) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.id = `booking-payee-option-${index}`;
      option.className = 'booking-payee-option';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.textContent = name;
      option.addEventListener('pointerdown', event => event.preventDefault());
      option.addEventListener('click', () => choose(name));
      list.appendChild(option);
    });
    list.hidden = false;
    input.setAttribute('aria-expanded', 'true');
    position();
  }

  input.addEventListener('input', () => render());
  input.addEventListener('focus', () => render(true));
  input.addEventListener('click', () => render(true));
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !list.hidden) { event.preventDefault(); close(); return; }
    if (list.hidden) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const diff = event.key === 'ArrowDown' ? 1 : -1;
      highlight((highlighted + diff + matches.length) % matches.length);
    } else if (event.key === 'Enter' && highlighted >= 0) {
      event.preventDefault();
      choose(matches[highlighted]);
    } else if (event.key === 'Tab') close();
  });
  input.addEventListener('blur', () => window.setTimeout(close, 150));
  document.addEventListener('pointerdown', event => {
    if (!list.hidden && event.target !== input && !list.contains(event.target)) close();
  });
  window.addEventListener('resize', position, { passive: true });
  window.addEventListener('scroll', position, { passive: true, capture: true });
  window.visualViewport?.addEventListener('resize', position, { passive: true });
  window.visualViewport?.addEventListener('scroll', position, { passive: true });
  input.closest('form')?.addEventListener('submit', close);
})();


/* 1.9.54: mobile-safe free-text payee autocomplete in recurring editor. Avoid native <datalist> popups,
 * which may cover the entire Android form when the soft keyboard opens.
 * The free-text input and the submitted payee_title field are unchanged.
 */
(function () {
  const input = document.getElementById('recurring-payee-input');
  const source = document.getElementById('recurring-known-payees');
  if (!input || !source || !input.closest('#recurring-form')) return;

  // Existing known payees come only from escaped <option value="..."> fields.
  const suggestionLimit = Math.max(1, Math.min(100, Number.parseInt(input.closest('#recurring-form').dataset.suggestionLimit || '20', 10) || 20));
  const payees = [...new Set(Array.from(source.querySelectorAll('option'))
    .map(option => option.value.trim()).filter(Boolean))];
  if (!payees.length) return;

  const normalize = value => value.normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const lang = document.documentElement.lang === 'en' ? 'en' : 'de';
  const list = document.createElement('div');
  list.id = 'recurring-payee-suggestions';
  list.className = 'booking-payee-suggestions recurring-payee-suggestions';
  list.setAttribute('popover','manual');
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', lang === 'en' ? 'Known payees' : 'Bekannte Empfänger');
  list.setAttribute('data-no-i18n', '');
  list.hidden = true;
  (input.closest('dialog') || document.body).appendChild(list);
  let matches = [];
  let highlighted = -1;

  function close() {
    if (list.matches(':popover-open')) list.hidePopover();
    list.hidden = true;
    list.replaceChildren();
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    matches = [];
    highlighted = -1;
  }

  function choose(value) {
    input.value = value;
    input.dispatchEvent(new Event('input', { bubbles: true }));
    input.dispatchEvent(new Event('change', { bubbles: true }));
    close();
    input.focus({ preventScroll: true });
  }

  function position() {
    if (list.hidden) return;
    const rect = input.getBoundingClientRect();
    const vv = window.visualViewport;
    const visibleTop = vv ? vv.offsetTop : 0;
    const visibleBottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const below = Math.max(0, visibleBottom - rect.bottom - 8);
    const above = Math.max(0, rect.top - visibleTop - 8);
    const openAbove = below < 160 && above > below;
    const available = openAbove ? above : below;
    if (available < 45) { close(); return; }
    const maxHeight = Math.min(236, Math.floor(available));
    const desired = Math.min(maxHeight, matches.length * 45 + 6);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8));
    list.style.left = `${left}px`;
    list.style.width = `${Math.min(rect.width, window.innerWidth - left - 8)}px`;
    list.style.top = `${openAbove ? rect.top - desired - 4 : rect.bottom + 4}px`;
    list.style.maxHeight = `${maxHeight}px`;
    list.dataset.position = openAbove ? 'above' : 'below';
  }

  function highlight(index) {
    highlighted = index;
    Array.from(list.children).forEach((node, i) => {
      node.setAttribute('aria-selected', i === highlighted ? 'true' : 'false');
      if (i === highlighted) {
        input.setAttribute('aria-activedescendant', node.id);
        node.scrollIntoView({ block: 'nearest' });
      }
    });
    if (highlighted === -1) input.removeAttribute('aria-activedescendant');
  }

  function render(showAll = false) {
    // Opening the field shows known payees immediately; typing filters the list.
    const query = showAll ? '' : normalize(input.value.trim());
    if (document.activeElement !== input) { close(); return; }
    matches = payees.filter(name => normalize(name).includes(query))
      .sort((a, b) => {
        const aStart = normalize(a).startsWith(query);
        const bStart = normalize(b).startsWith(query);
        return aStart === bStart ? a.localeCompare(b, lang) : aStart ? -1 : 1;
      }).slice(0, suggestionLimit);
    if (!matches.length) { close(); return; }
    highlighted = -1;
    list.replaceChildren();
    matches.forEach((name, index) => {
      const option = document.createElement('button');
      option.type = 'button';
      option.id = `recurring-payee-option-${index}`;
      option.className = 'booking-payee-option';
      option.setAttribute('role', 'option');
      option.setAttribute('aria-selected', 'false');
      option.textContent = name;
      option.addEventListener('pointerdown', event => event.preventDefault());
      option.addEventListener('click', () => choose(name));
      list.appendChild(option);
    });
    list.hidden = false;
    if (typeof list.showPopover === 'function' && !list.matches(':popover-open')) list.showPopover();
    input.setAttribute('aria-expanded', 'true');
    position();
  }

  input.addEventListener('input', () => render());
  input.addEventListener('focus', () => render(true));
  input.addEventListener('click', () => render(true));
  input.addEventListener('keydown', event => {
    if (event.key === 'Escape' && !list.hidden) { event.preventDefault(); close(); return; }
    if (list.hidden) return;
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const diff = event.key === 'ArrowDown' ? 1 : -1;
      highlight((highlighted + diff + matches.length) % matches.length);
    } else if (event.key === 'Enter' && highlighted >= 0) {
      event.preventDefault();
      choose(matches[highlighted]);
    } else if (event.key === 'Tab') close();
  });
  input.addEventListener('blur', () => window.setTimeout(close, 150));
  document.addEventListener('pointerdown', event => {
    if (!list.hidden && event.target !== input && !list.contains(event.target)) close();
  });
  window.addEventListener('resize', position, { passive: true });
  window.addEventListener('scroll', position, { passive: true, capture: true });
  window.visualViewport?.addEventListener('resize', position, { passive: true });
  window.visualViewport?.addEventListener('scroll', position, { passive: true });
  input.closest('form')?.addEventListener('submit', close);
  document.querySelector('.recurring-form-dialog')?.addEventListener('close', close);
})();


/* v1.9.51: Consistent, mobile-safe category picker. Keep the original <select>
 * as the submitted category_id so account logic, editing and the AJAX category
 * creation endpoint continue working. It remains visible without JavaScript.
 */
(function () {
  const select = document.getElementById('booking-category-select');
  const input = document.getElementById('booking-category-search');
  const form = document.getElementById('booking-form');
  if (!select || !input || !form) return;
  const suggestionLimit = Math.max(1, Math.min(100, Number.parseInt(form.dataset.suggestionLimit || '20', 10) || 20));
  const lang = document.documentElement.lang === 'en' ? 'en' : 'de';
  const zeroLabel = select.options[0]?.textContent?.trim() || (lang === 'en' ? 'No category' : 'Ohne Kategorie');
  const normalize = value => String(value || '').normalize('NFKD').replace(/[\u0300-\u036f]/g, '').toLocaleLowerCase();
  const list = document.createElement('div');
  list.id = 'booking-category-suggestions';
  list.className = 'booking-payee-suggestions booking-category-suggestions';
  list.setAttribute('role', 'listbox');
  list.setAttribute('aria-label', lang === 'en' ? 'Available categories' : 'Verfügbare Kategorien');
  list.setAttribute('data-no-i18n', '');
  list.hidden = true;
  document.body.appendChild(list);
  // The native select is retained as the only submitted field.
  select.classList.add('booking-category-native-hidden');
  input.hidden = false;
  const items = () => Array.from(select.options).filter(option => !option.disabled)
    .map(option => ({id: option.value, name: option.textContent.trim()}));
  let matches = [], selected = -1;
  function sync() {
    const option = select.selectedOptions[0];
    input.value = option ? option.textContent.trim() : zeroLabel;
  }
  function close() {
    list.hidden = true;
    list.replaceChildren();
    input.setAttribute('aria-expanded', 'false');
    input.removeAttribute('aria-activedescendant');
    matches = [];
    selected = -1;
  }
  function position() {
    if (list.hidden) return;
    const rect = input.getBoundingClientRect();
    const vv = window.visualViewport;
    const top = vv ? vv.offsetTop : 0;
    const bottom = vv ? vv.offsetTop + vv.height : window.innerHeight;
    const below = Math.max(0, bottom - rect.bottom - 8);
    const above = Math.max(0, rect.top - top - 8);
    const openAbove = below < 160 && above > below;
    const available = openAbove ? above : below;
    if (available < 45) { close(); return; }
    const height = Math.min(236, Math.floor(available));
    const wanted = Math.min(height, matches.length * 45 + 6);
    const left = Math.max(8, Math.min(rect.left, window.innerWidth - rect.width - 8));
    list.style.left = `${left}px`;
    list.style.width = `${Math.min(rect.width, window.innerWidth - left - 8)}px`;
    list.style.top = `${openAbove ? rect.top - wanted - 4 : rect.bottom + 4}px`;
    list.style.maxHeight = `${height}px`;
    list.dataset.position = openAbove ? 'above' : 'below';
  }
  function choose(option) {
    select.value = option.id;
    select.dispatchEvent(new Event('change', {bubbles: true}));
    close();
    input.focus({preventScroll: true});
  }
  function highlight(idx) {
    selected = idx;
    Array.from(list.children).forEach((element,i) => {
      element.setAttribute('aria-selected', String(i === idx));
      if (i === idx) {
        input.setAttribute('aria-activedescendant', element.id);
        element.scrollIntoView({block:'nearest'});
      }
    });
    if (idx < 0) input.removeAttribute('aria-activedescendant');
  }
  function render(showAll = false) {
    if (document.activeElement !== input || select.disabled) {close(); return;}
    const query = normalize(input.value.trim());
    // Opening the existing selection shows nearby categories; typing filters all names.
    const selectedOption = select.selectedOptions[0];
    const currentName = selectedOption?.textContent?.trim() || zeroLabel;
    const filterText = showAll && input.value === currentName ? '' : query;
    matches = items().filter(option => normalize(option.name).includes(filterText))
      .sort((a,b) => {
        if (filterText) {
          const as = normalize(a.name).startsWith(filterText), bs = normalize(b.name).startsWith(filterText);
          if (as !== bs) return as ? -1 : 1;
        }
        return a.name.localeCompare(b.name,lang);
      }).slice(0,suggestionLimit);
    if (!matches.length) {close(); return;}
    selected = -1;
    list.replaceChildren();
    matches.forEach((option,i) => {
      const element = document.createElement('button');
      element.type = 'button';
      element.id = `booking-category-option-${i}`;
      element.className = 'booking-payee-option booking-category-option';
      element.setAttribute('role','option');
      element.setAttribute('aria-selected','false');
      element.textContent = option.name;
      element.addEventListener('pointerdown',event => event.preventDefault());
      element.addEventListener('click',() => choose(option));
      list.appendChild(element);
    });
    list.hidden = false;
    input.setAttribute('aria-expanded','true');
    position();
  }
  // When the preset category is still displayed, select its full label on
  // focus/tap so typing replaces it instead of appending to the label.
  // Keep an already typed search query and the submitted category ID intact.
  function selectPresetLabel() {
    const currentLabel = select.selectedOptions[0]?.textContent?.trim() || zeroLabel;
    if (input.value === currentLabel) input.select();
  }
  select.addEventListener('change', () => {sync(); close();});
  input.addEventListener('focus',() => {selectPresetLabel(); render(true);});
  input.addEventListener('click',() => {selectPresetLabel(); render(true);});
  input.addEventListener('input',() => render());
  input.addEventListener('keydown',event => {
    if (event.key === 'Escape') {event.preventDefault(); sync(); close(); return;}
    if (list.hidden) { if (event.key === 'Enter') {event.preventDefault();sync();} return; }
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault();
      const offset = event.key === 'ArrowDown' ? 1 : -1;
      highlight((selected + offset + matches.length) % matches.length);
    } else if (event.key === 'Enter') {
      // Never submit an entire transaction while typing a category search.
      event.preventDefault();
      if (selected >= 0) choose(matches[selected]);
      else if (matches.length) choose(matches[0]);
      else { sync(); close(); }
    } else if (event.key === 'Tab') { sync(); close(); }
  });
  input.addEventListener('blur',() => window.setTimeout(() => {sync();close();},150));
  document.addEventListener('pointerdown', event => {
    if (!list.hidden && event.target !== input && !list.contains(event.target)) {sync();close();}
  });
  window.addEventListener('resize',position,{passive:true});
  window.addEventListener('scroll',position,{passive:true,capture:true});
  window.visualViewport?.addEventListener('resize',position,{passive:true});
  window.visualViewport?.addEventListener('scroll',position,{passive:true});
  form.addEventListener('submit', () => {sync();close();});
  sync();
})();

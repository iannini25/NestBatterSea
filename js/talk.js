/* ============================================================
   NEST BATTERSEA | 10 Talk to us
   ------------------------------------------------------------
   The register interest form: checked in the browser, then it
   opens the visitor's email app with a message addressed to the
   consultation team (there is no backend, nothing is stored).
   The image parallax and the reveals live in js/motion.js.
   ============================================================ */
(() => {
  const $ = (s, r = document) => r.querySelector(s);
  const root = $('#contact'), form = $('#tk-form');
  if (!root || !form) return;
  const TO = 'henry@theccp.net';
  const reduced = matchMedia('(prefers-reduced-motion: reduce)').matches;
  const panel = $('#tk-panel'), done = $('#tk-done');
  let tried = false, lastUrl = '';

  /* ---------- the glass sheen: a soft highlight that follows the pointer */
  if (!reduced && matchMedia('(hover: hover) and (pointer: fine)').matches) {
    let raf = 0, px = 0, py = 0;
    const paint = () => {
      raf = 0;
      const r = panel.getBoundingClientRect();
      panel.style.setProperty('--mx', ((px - r.left) / r.width * 100).toFixed(1) + '%');
      panel.style.setProperty('--my', ((py - r.top) / r.height * 100).toFixed(1) + '%');
      panel.style.setProperty('--sh', '1');
    };
    panel.addEventListener('pointermove', e => { px = e.clientX; py = e.clientY; if (!raf) raf = requestAnimationFrame(paint); });
    panel.addEventListener('pointerleave', () => { cancelAnimationFrame(raf); raf = 0; ['--mx', '--my', '--sh'].forEach(p => panel.style.removeProperty(p)); });
  }

  /* ---------- the form ---------------------------------------------- */
  const rules = {
    first: v => v.trim().length > 0 || 'Please enter your first name.',
    last: v => v.trim().length > 0 || 'Please enter your last name.',
    email: v => /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(v.trim()) || 'Please enter a valid email address.',
    phone: v => !v.trim() || (/^[+()\d\s.]+$/.test(v.trim()) && v.replace(/\D/g, '').length >= 7) || 'Please check the phone number, or leave it empty.'
  };
  function check(input, quiet) {
    const rule = rules[input.name];
    if (!rule) return true;
    const res = rule(input.value), ok = res === true, f = input.closest('.tk-f');
    f.classList.toggle('ok', ok && input.value.trim() !== '');
    if (quiet && !ok) return false;
    f.classList.toggle('bad', !ok);
    input.setAttribute('aria-invalid', String(!ok));
    $('#' + input.getAttribute('aria-describedby')).textContent = ok ? '' : res;
    return ok;
  }
  const fields = () => Object.keys(rules).map(n => form.elements[n]);

  form.addEventListener('input', e => {
    const t = e.target;
    if (rules[t.name]) check(t, !tried && !t.closest('.tk-f').classList.contains('bad'));
  });
  form.addEventListener('focusout', e => {
    const t = e.target;
    if (rules[t.name] && t.value.trim()) check(t);
  });

  const v = n => form.elements[n].value.trim();
  const name = () => [v('first'), v('last')].filter(Boolean).join(' ');
  const chosen = () => { const i = $('input[name="topic"]:checked', form); return i ? i.closest('label').textContent.trim() : ''; };
  function mailto() {
    const topic = chosen();
    const lines = [
      'Hello,', '',
      'I would like to register my interest in Nest Battersea, 38 Lombard Road.', '',
      'Name: ' + name(),
      'Email: ' + v('email')
    ];
    if (v('phone')) lines.push('Phone: ' + v('phone'));
    if (topic) lines.push('Interested in: ' + topic);
    if (v('message')) lines.push('', v('message'));
    if (form.elements.updates.checked) lines.push('', 'Please keep me updated about Nest Battersea.');
    lines.push('', 'Sent from the Nest Battersea website.');
    return `mailto:${TO}?subject=${encodeURIComponent('Nest Battersea | Register interest')}&body=${encodeURIComponent(lines.join('\r\n'))}`;
  }
  // tests may set window.NestTalkOpen to catch the address instead of launching the email app
  const send = url => {
    if (typeof window.NestTalkOpen === 'function') return window.NestTalkOpen(url);
    const a = document.createElement('a');
    a.href = url;
    a.click();
  };

  form.addEventListener('submit', e => {
    e.preventDefault();
    tried = true;
    const bad = fields().filter(i => !check(i));
    if (bad.length) {
      bad[0].focus();
      if (!reduced) { panel.classList.remove('shake'); void panel.offsetWidth; panel.classList.add('shake'); }
      return;
    }
    lastUrl = mailto();
    $('#tk-who').textContent = v('first') ? ', ' + v('first').split(/\s+/)[0] : '';
    const sum = $('#tk-sum'), topic = chosen();
    sum.textContent = '';
    if (topic) { const s = document.createElement('span'); s.textContent = topic; sum.appendChild(s); }
    panel.style.minHeight = panel.offsetHeight + 'px';
    form.hidden = true;
    done.hidden = false;
    done.focus({ preventScroll: true });
    send(lastUrl);
  });
  panel.addEventListener('animationend', () => panel.classList.remove('shake'));

  function reset() {
    form.reset();
    tried = false;
    fields().forEach(i => { const f = i.closest('.tk-f'); f.classList.remove('bad', 'ok'); i.removeAttribute('aria-invalid'); $('#' + i.getAttribute('aria-describedby')).textContent = ''; });
    done.hidden = true;
    form.hidden = false;
    panel.style.minHeight = '';
    form.elements.first.focus({ preventScroll: true });
  }

  root.addEventListener('click', e => {
    const b = e.target.closest('[data-tk]');
    if (!b) return;
    if (b.dataset.tk === 'again' && lastUrl) send(lastUrl);
    if (b.dataset.tk === 'reset') reset();
  });
})();

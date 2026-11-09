/* ============================================================
   NEST BATTERSEA | scroll motion (GSAP 3.12.5 + ScrollTrigger)
   ------------------------------------------------------------
   Loaded from cdnjs only after the page has loaded, so it never
   stands in the way of the tower's first paint. Nothing in the
   CSS hides content for motion: start states are set here, at
   run time, and only on what is still below the fold. If this
   file or GSAP fails, the page is complete and simply still.

   gsap.matchMedia picks one of three moods:
     full   desktop: layered parallax, line by line reveals, the
            exterior views pinned and sliding sideways, the hero
            card trailing as the first section slides over it
     lite   phones and portrait tablets: the same reveals, lighter
            parallax, no pinning
     calm   prefers-reduced-motion: plain fades, nothing moves
   Transform and opacity only. The hero stage, the flights and the
   3D plan are not touched: the hero moves only while the page is
   scrolled, and the stage always opens with the page at the top.
   ============================================================ */
(() => {
  const V = '3.12.5', CDN = `https://cdnjs.cloudflare.com/ajax/libs/gsap/${V}/`;
  const html = document.documentElement;
  const $ = (s, r = document) => r.querySelector(s);
  const $$ = (s, r = document) => [...r.querySelectorAll(s)];

  const load = src => new Promise((res, rej) => {
    const s = document.createElement('script');
    s.src = src; s.async = true; s.crossOrigin = 'anonymous';
    s.onload = res; s.onerror = rej;
    document.head.appendChild(s);
  });
  function start() {
    if (window.gsap && window.ScrollTrigger) return init();
    load(CDN + 'gsap.min.js').then(() => load(CDN + 'ScrollTrigger.min.js')).then(init).catch(() => {});
  }
  if (document.readyState === 'complete') setTimeout(start, 50);
  else addEventListener('load', () => setTimeout(start, 50), { once: true });

  /* ---------- line by line text --------------------------------------
     A paragraph is split into one masked span per rendered line, revealed,
     then put back as plain text so later resizes reflow it normally. */
  const texts = new WeakMap();
  function splitLines(p) {
    if (!texts.has(p)) texts.set(p, p.textContent.replace(/\s+/g, ' ').trim());
    const text = texts.get(p), words = text.split(' ');
    p.textContent = '';
    const spans = words.map((w, i) => {
      const s = document.createElement('span');
      s.textContent = w + (i < words.length - 1 ? ' ' : '');
      p.appendChild(s);
      return s;
    });
    const lines = [];
    let top = null;
    spans.forEach(s => {
      const t = s.offsetTop;
      if (top === null || Math.abs(t - top) > 3) { lines.push(''); top = t; }
      lines[lines.length - 1] += s.textContent;
    });
    p.textContent = '';
    lines.forEach(l => {
      const o = document.createElement('span'), i = document.createElement('span');
      o.className = 'sl'; i.className = 'sl-i'; i.textContent = l.trimEnd();
      o.appendChild(i); p.appendChild(o); p.appendChild(document.createTextNode(' '));
    });
    return $$('.sl-i', p);
  }
  function unsplit(p) { if (texts.has(p)) p.textContent = texts.get(p); }

  function init() {
    const { gsap, ScrollTrigger } = window;
    if (!gsap || !ScrollTrigger) return;
    gsap.registerPlugin(ScrollTrigger);
    html.classList.add('gsap');
    ScrollTrigger.config({ ignoreMobileResize: true });
    gsap.defaults({ ease: 'power3.out', duration: 1 });

    const unseen = el => el.getBoundingClientRect().top > innerHeight * .92;   // not on screen yet
    const once = (trigger, start = 'top 88%') => ({ trigger, start, once: true });
    let pending = [];                                                       // paragraphs split, not revealed yet

    const mm = gsap.matchMedia();
    mm.add({
      full: '(min-width: 861px) and (prefers-reduced-motion: no-preference)',
      lite: '(max-width: 860px) and (prefers-reduced-motion: no-preference)',
      calm: '(prefers-reduced-motion: reduce)'
    }, ctx => {
      const { full, calm } = ctx.conditions;
      const amp = full ? 1 : .5;                                            // parallax amplitude
      pending = [];

      /* 1. hero to sections: the card trails the page and dims while the first section slides over it */
      if (!calm) {
        const hero = $('.hero');
        gsap.timeline({ defaults: { ease: 'none' }, scrollTrigger: { trigger: hero, start: 'top top', end: 'bottom top', scrub: true } })
          .fromTo(['#card', '#mini'], { '--lag': '0px' }, { '--lag': () => Math.round(hero.offsetHeight * (full ? .3 : .16)) + 'px' }, 0)
          .fromTo('#veil', { opacity: 0 }, { opacity: full ? .55 : .4 }, 0)
          .fromTo('.hc-in', { y: 0, opacity: 1 }, { y: full ? -110 : -50, opacity: .15 }, 0)
          .fromTo('.meta .m-in', { y: 0, opacity: 1 }, { y: -70, opacity: .1 }, 0);
      }

      /* 2. headings: their lines rise out of a mask, one after the other */
      $$('main .lines').forEach(h => {
        if (!unseen(h)) return;
        if (calm) return gsap.from(h, { opacity: 0, duration: .6, scrollTrigger: once(h) });
        gsap.from($$('.ln > i', h), { yPercent: 112, duration: 1.2, ease: 'expo.out', stagger: .09, scrollTrigger: once(h, 'top 86%') });
      });
      $$('main .sticker').forEach(st => {
        if (calm || !unseen(st)) return;
        gsap.from(st, { scale: .4, rotation: -36, opacity: 0, duration: .95, ease: 'back.out(2.2)', delay: .35, scrollTrigger: once(st.parentNode, 'top 85%') });
      });

      /* 3. paragraphs: line by line */
      $$('main [data-lines]').forEach(p => {
        if (!unseen(p)) return;
        if (calm) return gsap.from(p, { opacity: 0, duration: .6, scrollTrigger: once(p) });
        gsap.set(splitLines(p), { yPercent: 105, opacity: 0 });
        pending.push(p);
        ScrollTrigger.create({ trigger: p, start: 'top 90%', once: true, onEnter: () => {
          pending = pending.filter(x => x !== p);
          gsap.to($$('.sl-i', p), { yPercent: 0, opacity: 1, duration: 1.05, ease: 'power3.out', stagger: .075, onComplete: () => unsplit(p) });
        } });
      });

      /* 4. blocks, cards and lists */
      $$('main [data-reveal]').forEach(b => {
        if (!unseen(b)) return;
        const card = b.dataset.reveal === 'card';
        if (calm) return gsap.from(b, { opacity: 0, duration: .6, scrollTrigger: once(b) });
        gsap.from(b, card
          ? { y: full ? 80 : 44, opacity: 0, scale: full ? .965 : 1, duration: 1.35, ease: 'expo.out', scrollTrigger: once(b, 'top 92%') }
          : { y: 32, opacity: 0, duration: 1.05, scrollTrigger: once(b) });
      });
      $$('main [data-stagger]').forEach(list => {
        if (!unseen(list)) return;
        const kids = [...list.children];
        if (calm) return gsap.from(kids, { opacity: 0, duration: .6, stagger: .04, scrollTrigger: once(list) });
        gsap.from(kids, { y: 26, opacity: 0, duration: .9, stagger: .07, scrollTrigger: once(list) });
      });
      if (calm) return () => {};

      /* 5. layered parallax: each layer at its own depth */
      $$('main .px[data-speed]').forEach(px => {
        const pic = px.querySelector('picture');
        if (!pic || (full && px.classList.contains('h'))) return;             // views: sideways, below
        const s = +px.dataset.speed * amp;
        gsap.set(pic, { scale: 1 + s * 2.3 / 100, force3D: true });
        gsap.fromTo(pic, { yPercent: -s }, { yPercent: s, ease: 'none', scrollTrigger: { trigger: px, start: 'top bottom', end: 'bottom top', scrub: true } });
      });
      $$('main [data-depth]').forEach(layer => {
        const d = +layer.dataset.depth * amp;
        gsap.fromTo(layer, { y: d }, { y: -d, ease: 'none', scrollTrigger: { trigger: layer.parentNode, start: 'top bottom', end: 'bottom top', scrub: true } });
      });

      /* 6. exterior views (desktop): the row is pinned and slides sideways; each view drifts inside its frame */
      if (full) {
        const pin = $('#viewspin'), row = $('#vrow'), count = $('#vcount'), cards = $$('#vlist .view');
        // pinning adds scroll length above everything after it: only while the visitor has not reached it
        if (pin && row && cards.length && pin.getBoundingClientRect().top > 0) {
          html.classList.add('gsap-pin');
          const dist = () => Math.max(0, row.scrollWidth - innerWidth);
          const slide = gsap.to(row, {
            x: () => -dist(), ease: 'none',
            scrollTrigger: {
              trigger: pin, start: 'top top', end: () => '+=' + dist(), pin: true, scrub: .7, invalidateOnRefresh: true, anticipatePin: 1,
              onUpdate: self => { if (count) count.textContent = String(Math.min(cards.length, 1 + Math.round(self.progress * (cards.length - 1)))).padStart(2, '0'); }
            }
          });
          // keyboard focus on a view off screen: scroll the page to it, never the clipped row
          row.addEventListener('focusin', e => {
            const c = e.target.closest('.view'), st = slide.scrollTrigger;
            pin.scrollLeft = 0;
            if (!c || !st) return;
            const k = cards.indexOf(c) / Math.max(1, cards.length - 1);
            scrollTo({ top: Math.round(st.start + (st.end - st.start) * k), behavior: 'auto' });
          });
          cards.forEach(c => {
            const pic = c.querySelector('.px picture'), cap = c.querySelector('.view-cap');
            if (pic) {
              gsap.set(pic, { scale: 1.16, force3D: true });
              gsap.fromTo(pic, { xPercent: -6 }, { xPercent: 6, ease: 'none', scrollTrigger: { trigger: c, containerAnimation: slide, start: 'left right', end: 'right left', scrub: true } });
            }
            if (cap && c.getBoundingClientRect().left > innerWidth) {
              gsap.from(cap, { y: 24, opacity: 0, duration: .9, scrollTrigger: { trigger: c, containerAnimation: slide, start: 'left 82%', toggleActions: 'play none none none' } });
            }
          });
        }
      }

      return () => {                                                        // leaving this mood
        html.classList.remove('gsap-pin');
        $$('main [data-lines]').forEach(unsplit);
        pending = [];
      };
    });

    /* resizes: paragraphs still waiting for their reveal are split again at the new width */
    let w = innerWidth, rq = 0;
    addEventListener('resize', () => {
      clearTimeout(rq);
      rq = setTimeout(() => {
        if (innerWidth === w) return;
        w = innerWidth;
        pending.forEach(p => gsap.set(splitLines(p), { yPercent: 105, opacity: 0 }));
      }, 180);
    });

    /* keep every trigger exact: when the stage locks or unlocks the page, after late images and the
       fonts. Images carry their sizes, so this is a safety net: it waits for the scroll to rest. */
    let q = 0, scrolled = 0;
    addEventListener('scroll', () => { scrolled = performance.now(); }, { passive: true });
    const refresh = (delay = 250) => {
      clearTimeout(q);
      q = setTimeout(function go() {
        if (performance.now() - scrolled < 400) { q = setTimeout(go, 300); return; }
        ScrollTrigger.refresh();
      }, delay);
    };
    document.addEventListener('nest:lock', () => refresh(60));
    $$('main img').forEach(img => { if (!img.complete) img.addEventListener('load', () => refresh(), { once: true }); });
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => refresh());
    window.NestMotion = { refresh: () => ScrollTrigger.refresh(), ready: true };
  }
})();

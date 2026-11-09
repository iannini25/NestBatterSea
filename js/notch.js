/* ============================================================
   NEST BATTERSEA | notched card outline
   The card is a rounded rectangle with corner notches cut out of it.
   Each notch wraps a piece of UI with a concave curve concentric with
   that UI, and meets the card edges with soft convex flares.
   The outline is built as one SVG path in the element's own pixel
   space and applied as clip-path, so the curves stay vector sharp at
   any size or pixel ratio, and clicks in a notch reach the page below.

   Notch.path(W, H, spec) -> path string
   spec = { R, f,                      card corner radius, flare radius
            tl: { w, h, r },           top left notch (r = concave radius)
            tr: { w, h, r },           top right notch
            br: [ { w, h, r }, ... ] } bottom right, steps listed bottom up,
                                       each step narrower than the one below
   ============================================================ */
const Notch = (() => {
  const on = n => n && n.w > 0.5 && n.h > 0.5;

  // a closed rectilinear outline, clockwise; vertex = [x, y, radius, priority]
  // priority decides which radius gives way when two arcs share a short edge
  function outline(W, H, s) {
    const R = s.R, f = s.f, v = [];
    if (on(s.tl)) v.push([0, s.tl.h, f, 0], [s.tl.w, s.tl.h, s.tl.r, 2], [s.tl.w, 0, f, 0]);
    else v.push([0, 0, R, 1]);
    if (on(s.tr)) v.push([W - s.tr.w, 0, f, 0], [W - s.tr.w, s.tr.h, s.tr.r, 2], [W, s.tr.h, f, 0]);
    else v.push([W, 0, R, 1]);
    const st = (s.br || []).filter(on);
    if (st.length) {
      const tops = [];
      let y = H;
      st.forEach(k => { y -= k.h; tops.push(y); });
      v.push([W, tops[st.length - 1], f, 0]);
      for (let k = st.length - 1; k >= 0; k--) {
        v.push([W - st[k].w, tops[k], st[k].r, 2]);
        v.push([W - st[k].w, k > 0 ? tops[k - 1] : H, f, 0]);
      }
    } else v.push([W, H, R, 1]);
    v.push([0, H, R, 1]);
    return v;
  }

  // two arcs on one edge may not overlap: shrink the lower priority one first
  function clamp(v) {
    for (let pass = 0; pass < 3; pass++) {
      for (let i = 0; i < v.length; i++) {
        const a = v[i], b = v[(i + 1) % v.length];
        const L = Math.abs(b[0] - a[0]) + Math.abs(b[1] - a[1]);
        let ex = a[2] + b[2] - L;
        if (ex <= 0) continue;
        const lo = a[3] <= b[3] ? a : b, hi = lo === a ? b : a;
        const d = Math.min(ex, lo[2]);
        lo[2] -= d; ex -= d;
        if (ex > 0) hi[2] = Math.max(0, hi[2] - ex);
      }
    }
    return v;
  }

  const unit = (a, b) => {
    const dx = b[0] - a[0], dy = b[1] - a[1], L = Math.abs(dx) + Math.abs(dy) || 1;
    return [dx / L, dy / L];
  };

  function path(W, H, spec, dpr) {
    const k = Math.max(1, dpr || window.devicePixelRatio || 1);
    const sn = x => Math.round(x * k) / k;                 // snap to device pixels
    const n2 = x => +sn(x).toFixed(3);
    const v = clamp(outline(W, H, spec).map(p => [sn(p[0]), sn(p[1]), Math.max(0, sn(p[2])), p[3]]));
    const n = v.length;
    const pts = v.map((p, i) => {
      const din = unit(v[(i - 1 + n) % n], p), dout = unit(p, v[(i + 1) % n]);
      const r = p[2];
      return {
        a: [p[0] - din[0] * r, p[1] - din[1] * r],
        b: [p[0] + dout[0] * r, p[1] + dout[1] * r],
        r,
        sweep: din[0] * dout[1] - din[1] * dout[0] > 0 ? 1 : 0   // right turn = convex
      };
    });
    let d = `M${n2(pts[0].b[0])} ${n2(pts[0].b[1])}`;
    for (let i = 1; i <= n; i++) {
      const q = pts[i % n];
      d += `L${n2(q.a[0])} ${n2(q.a[1])}`;
      if (q.r > 0) d += `A${n2(q.r)} ${n2(q.r)} 0 0 ${q.sweep} ${n2(q.b[0])} ${n2(q.b[1])}`;
    }
    return d + 'Z';
  }

  const supported = typeof CSS !== 'undefined' && CSS.supports && CSS.supports('clip-path', 'path("M0 0L1 0L1 1Z")');

  function apply(el, W, H, spec) {
    if (!supported) return false;
    const v = `path("${path(W, H, spec)}")`;
    if (el._notch !== v) { el.style.clipPath = v; el.style.webkitClipPath = v; el._notch = v; }
    return true;
  }

  return { path, apply, supported };
})();

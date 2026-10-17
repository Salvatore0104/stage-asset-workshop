/* Pure frame rendering: project data are supplied by the generated HTML. */
window.Workshop = (() => {
  const C = window.WORKSHOP_CONFIG;
  const media = window.WORKSHOP_MEDIA;
  const images = {};
  let stageMask, pgmMask, scratch, overlayCache;
  const canvas = (w, h) => {
    const c = document.createElement('canvas'); c.width = w; c.height = h;
    if (!c.getContext('2d')) throw new Error(`无法建立 ${w}×${h} 画布，请降低尺寸或改用离线渲染。`);
    return c;
  };
  const clamp = (x, a = 0, b = 1) => Math.max(a, Math.min(b, x));
  const frac = x => x - Math.floor(x);
  const seconds = (part, bpm) => part.duration.value * (part.duration.unit === 'beats' ? 60 / bpm : 1);
  const count = (part, bpm) => Math.max(1, Math.round(seconds(part, bpm) * C.fps));
  const context = (part, frame, bpm) => {
    const frames = count(part, bpm), duration = frames / C.fps, t = frame / C.fps;
    return {config: C, part, frame, frames, fps: C.fps, bpm, t, duration,
      beat: t * bpm / 60, phase: part.loop ? frac(t / duration) : clamp(t / duration),
      width: C.stage.width, height: C.stage.height, clamp, frac,
      kick: Math.exp(-frac(t * bpm / 60) * 5),
      // Stateless random: never use evolving global RNG in frame rendering.
      random: seed => frac(Math.sin(seed * 127.1 + 311.7) * 43758.5453)};
  };
  function shapePath(g, shapes) {
    g.beginPath();
    for (const s of shapes) {
      if (s.type === 'rect') g.rect(s.x, s.y, s.w, s.h);
      else {g.moveTo(...s.points[0]); for (const p of s.points.slice(1)) g.lineTo(...p); g.closePath();}
    }
  }
  async function load(file) {
    if (!media[file]) throw new Error(`未打包素材：${file}`);
    const im = new Image();
    await new Promise((resolve, reject) => {im.onload = resolve; im.onerror = () => reject(new Error(`素材加载失败：${file}`)); im.src = media[file];});
    return im;
  }
  async function maskCanvas(spec) {
    const c = canvas(C.stage.width, C.stage.height), g = c.getContext('2d');
    if (spec.type === 'geometry') {g.fillStyle = '#fff'; shapePath(g, spec.shapes); g.fill();}
    else {
      const im = await load(spec.file);
      if (im.naturalWidth !== c.width || im.naturalHeight !== c.height) throw new Error(`遮罩尺寸不符：${spec.file}`);
      g.drawImage(im, 0, 0); const data = g.getImageData(0, 0, c.width, c.height), d = data.data;
      for (let i = 0; i < d.length; i += 4) {
        // Luminance is multiplied by source alpha; invert applies to final coverage.
        let a = spec.channel === 'alpha' ? d[i + 3] : (.2126 * d[i] + .7152 * d[i + 1] + .0722 * d[i + 2]) * d[i + 3] / 255;
        d[i] = d[i + 1] = d[i + 2] = 255; d[i + 3] = Math.round(spec.invert ? 255 - a : a);
      }
      g.putImageData(data, 0, 0);
    }
    return c;
  }
  const layers = part => [...part.layers,
    ...(C.pgm.enabled ? [{id: 'pgm_matte', name: 'PGM 白色遮罩', static: true, defaultVisible: false}] : []),
    {id: 'stage_mask', name: '舞台白色遮罩', static: true, defaultVisible: false}];
  function image(g, id, options = {}) {
    const a = C.assets[id], im = images[id]; if (!a || !im) throw new Error(`未定义素材：${id}`);
    const r = options.rect || a, scale = options.scale ?? 1;
    g.save(); g.translate(r.x + r.w / 2 + (options.dx || 0), r.y + r.h / 2 + (options.dy || 0));
    g.rotate(options.rotate || 0); g.scale(scale, scale);
    g.globalAlpha *= (a.opacity ?? 1) * (options.opacity ?? 1);
    g.globalCompositeOperation = options.blend || a.blend || 'source-over';
    g.drawImage(im, -r.w / 2, -r.h / 2, r.w, r.h); g.restore();
  }
  function render(target, {part, frame, bpm, layerIds, clip = false}) {
    if (!Number.isInteger(frame) || frame < 0 || frame >= count(part, bpm)) throw new Error('帧超出段落范围');
    const g = target.getContext('2d'), w = target.width, h = target.height;
    if (!scratch || scratch.width !== w || scratch.height !== h) scratch = canvas(w, h);
    const q = scratch.getContext('2d'), state = context(part, frame, bpm);
    g.setTransform(1, 0, 0, 1, 0, 0); g.clearRect(0, 0, w, h);
    for (const id of layerIds) {
      const layer = layers(part).find(l => l.id === id); if (!layer) throw new Error(`未知图层：${id}`);
      q.setTransform(1, 0, 0, 1, 0, 0); q.globalAlpha = 1; q.globalCompositeOperation = 'source-over'; q.clearRect(0, 0, w, h);
      q.save(); q.scale(w / C.stage.width, h / C.stage.height); q.imageSmoothingEnabled = C.imageSmoothing;
      try {
        if (id === 'stage_mask') q.drawImage(stageMask, 0, 0);
        else if (id === 'pgm_matte') q.drawImage(pgmMask, 0, 0);
        else {
          const scene = window.WORKSHOP_SCENES[part.id];
          if (!scene) throw new Error(`缺少段落绘图：${part.id}`);
          scene(q, state, id, {image, shapePath});
        }
      } finally {q.restore();}
      if (C.pgm.enabled && layer.cutPgm) {q.globalCompositeOperation = 'destination-out'; q.drawImage(pgmMask, 0, 0, w, h);}
      if (clip && id !== 'stage_mask') {q.globalCompositeOperation = 'destination-in'; q.drawImage(stageMask, 0, 0, w, h);}
      q.globalCompositeOperation = 'source-over';
      g.save(); g.globalCompositeOperation = layer.blend || 'source-over'; g.drawImage(scratch, 0, 0); g.restore();
    }
    return target;
  }
  function overlay(target, opacity) {
    if (opacity <= 0) return;
    const key = `${target.width}:${target.height}:${opacity}`;
    if (!overlayCache || overlayCache.key !== key) {
      const c = canvas(target.width, target.height), q = c.getContext('2d');
      q.fillStyle = `rgba(0,0,0,${opacity})`; q.fillRect(0, 0, c.width, c.height);
      q.globalCompositeOperation = 'destination-out'; q.drawImage(stageMask, 0, 0, c.width, c.height);
      overlayCache = {key, canvas: c};
    }
    target.getContext('2d').drawImage(overlayCache.canvas, 0, 0);
  }
  async function init() {
    for (const [id, a] of Object.entries(C.assets)) images[id] = await load(a.file);
    stageMask = await maskCanvas(C.stageMask);
    if (C.pgm.enabled) pgmMask = await maskCanvas(C.pgm.mask);
    for (const p of C.parts) if (!window.WORKSHOP_SCENES[p.id]) throw new Error(`缺少段落绘图：${p.id}`);
    await document.fonts.ready;
  }
  return {config: C, init, canvas, render, overlay, seconds, count, context, layers};
})();

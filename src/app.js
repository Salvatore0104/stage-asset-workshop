(async () => {
  const W = window.Workshop, C = W.config, $ = id => document.getElementById(id);
  let part = C.parts[0], frame = 0, bpm = C.bpm, visible = new Set(), playing = false;
  let busy = false, cancelled = false, anchor = 0, anchorFrame = 0, raf = 0;
  const view = $('view');
  const audio = new Audio();let audioUrl;
  const audioAt = () => C.parts.slice(0,C.parts.indexOf(part)).reduce((n,p)=>n+W.count(p,bpm)/C.fps,0)+frame/C.fps+(C.audio?.offsetSeconds||0);
  function seekAudio(){if(audio.src&&Number.isFinite(audio.duration))audio.currentTime=Math.max(0,Math.min(audio.duration,audioAt()));}
  const message = text => {$('status').textContent = text;};
  const fail = error => {$('error').textContent = error.message || String(error);};
  const delay = ms => new Promise(r => setTimeout(r, ms));
  function download(blob, name) {
    const url = URL.createObjectURL(blob), a = document.createElement('a'); a.href = url; a.download = name;
    document.body.append(a); a.click(); a.remove(); setTimeout(() => URL.revokeObjectURL(url), 10000);
  }
  function png(c) {return new Promise((resolve, reject) => c.toBlob(b => b ? resolve(b) : reject(new Error('PNG 编码失败；请降低尺寸。')), 'image/png'));}
  const visibleIds = () => W.layers(part).filter(l => visible.has(l.id)).map(l => l.id);
  function draw() {
    W.render(view, {part, frame, bpm, layerIds: visibleIds()});
    W.overlay(view, Number($('mask').value) / 100);
    $('scrub').value = frame;
    $('tc').textContent = `f${frame} / ${W.count(part, bpm) - 1} · ${(frame / C.fps).toFixed(2)}s`;
  }
  function stop() {playing = false;audio.pause(); cancelAnimationFrame(raf); $('play').textContent = '播放';}
  function tick(now) {
    if (!playing) return;
    const next = anchorFrame + Math.floor((now - anchor) * C.fps / 1000), n = W.count(part, bpm);
    frame = part.loop ? next % n : Math.min(n - 1, next); draw();
    if(audio.src&&Number.isFinite(audio.duration)&&Math.abs(audio.currentTime-audioAt())>.18)seekAudio();
    if (!part.loop && next >= n - 1) {stop(); return;}
    raf = requestAnimationFrame(tick);
  }
  function start() {
    if (!part.loop && frame >= W.count(part, bpm) - 1) frame = 0;
    if(audio.src){seekAudio();audio.play().catch(()=>message('音乐未能自动播放，请重新选择本地音频后点击播放。'));}
    playing = true; anchor = performance.now(); anchorFrame = frame; $('play').textContent = '暂停'; raf = requestAnimationFrame(tick);
  }
  function lock(value) {
    busy = value; $('export-controls').disabled = value; $('cancel').disabled = !value;
    for (const el of $('transport').querySelectorAll('input,select,button')) el.disabled = value;
    for (const el of $('layers').querySelectorAll('input')) el.disabled = value;
    for (const el of $('show-settings').querySelectorAll('input,button')) el.disabled = value;
  }
  function setup() {
    $('show-text').value=part.text??'';$('show-subtitle').value=part.subtitle??'';
    const n = W.count(part, bpm); frame = Math.min(frame, n - 1);
    $('scrub').max = n - 1; $('start').value = 0; $('end').value = n - 1;
    $('start').max = $('end').max = n - 1; visible = new Set();
    $('layers').replaceChildren(); $('export-layer').replaceChildren(new Option('全部制作图层（逐层）', 'all'), new Option('目前勾选的合成参考', 'comp'));
    for (const layer of W.layers(part)) {
      const label = document.createElement('label'), input = document.createElement('input'); input.type = 'checkbox';
      input.checked = layer.defaultVisible !== false; if (input.checked) visible.add(layer.id);
      input.onchange = () => {input.checked ? visible.add(layer.id) : visible.delete(layer.id); draw();};
      label.append(input, document.createTextNode(layer.name || layer.id)); $('layers').append(label);
      $('export-layer').add(new Option(layer.name || layer.id, layer.id));
    }
    $('layer-info').textContent = `${part.loop ? '循环段' : '单次段'} · ${part.duration.value} ${part.duration.unit === 'beats' ? '拍' : '秒'} · 实际 ${n} 帧 / ${(n / C.fps).toFixed(3)} 秒`;
    draw();
  }
  function dimensions() {
    const width = Number($('width').value), height = Math.round(width * C.stage.height / C.stage.width);
    if (!Number.isSafeInteger(width) || width <= 0 || height < 1) throw new Error('请输入有效的整数宽度。');
    return {width, height};
  }
  const renderTo = (c, i, id, clip) => W.render(c, {part, frame: i, bpm, layerIds: id === 'comp' ? visibleIds() : [id], clip});
  async function writeJson(dir, name, data) {
    const handle = await dir.getFileHandle(name, {create: true}), stream = await handle.createWritable();
    try {await stream.write(JSON.stringify(data, null, 2));} finally {await stream.close();}
  }
  $('play').onclick = () => playing ? stop() : start();
  $('scrub').oninput = () => {stop(); frame = Number($('scrub').value);seekAudio(); draw();};
  $('mask').oninput = draw;
  $('part').onchange = () => {stop(); part = C.parts[Number($('part').value)]; frame = 0; setup();};
  $('bpm').onchange = () => {
    const next = Number($('bpm').value);
    if (!Number.isFinite(next) || next <= 0 || next > 999) {$('bpm').value = bpm; message('BPM 请输入 0–999 之间的正数。'); return;}
    stop(); bpm = next; frame = 0; setup();
  };
  $('width').oninput = () => {try {const d = dimensions(); $('output-size').textContent = `× ${d.height} px`;} catch {$('output-size').textContent = '尺寸无效';}};
  $('cancel').onclick = () => {cancelled = true; message('正在停止，已完成的文件会保留。');};
  $('show-text').oninput=()=>{part.text=$('show-text').value;draw();};
  $('show-subtitle').oninput=()=>{part.subtitle=$('show-subtitle').value;draw();};
  $('audio-file').onchange=()=>{stop();if(audioUrl)URL.revokeObjectURL(audioUrl);const file=$('audio-file').files[0];if(file){audioUrl=URL.createObjectURL(file);audio.src=audioUrl;$('audio-status').textContent=`本地试听：${file.name}`;}};
  $('save-settings').onclick=()=>download(new Blob([JSON.stringify({...C,bpm},null,2)],{type:'application/json'}),`${C.projectId}_workshop-settings.json`);
  $('still').onclick = async () => {
    try {
      const d = dimensions(), id = $('export-layer').value;
      if (id === 'all') throw new Error('单张下载请先选一个图层或合成参考。');
      download(await png(renderTo(W.canvas(d.width, d.height), frame, id, $('clip').checked)), `${C.projectId}_${part.id}_${id}_${String(frame).padStart(6, '0')}.png`);
      message('已下载目前单张 PNG。');
    } catch (e) {fail(e);}
  };
  $('export').onclick = async () => {
    let folder, meta, written = 0;
    try {
      $('error').textContent = ''; stop();
      if (!window.showDirectoryPicker) throw new Error('此环境无法选取文件夹。请使用支持此功能的浏览器；仍不可用时，请由 Codex 启动 localhost 服务。可先下载单张 PNG。');
      const a = Number($('start').value), b = Number($('end').value), n = W.count(part, bpm), d = dimensions();
      if (![a, b].every(Number.isInteger) || a < 0 || b < a || b >= n) throw new Error(`帧范围必须是 0–${n - 1} 的整数，且结束帧不小于起始帧。`);
      const choice = $('export-layer').value, clip = $('clip').checked;
      const selected = choice === 'all' ? W.layers(part) : choice === 'comp' ? [{id: 'comp', static: false}] : W.layers(part).filter(l => l.id === choice);
      cancelled = false; lock(true);
      const root = await window.showDirectoryPicker({mode: 'readwrite'});
      // Fresh run folder: stale tail frames cannot contaminate a shorter new export.
      const run = `${C.projectId}_${part.id}_${new Date().toISOString().replace(/[:.]/g, '-')}_${Math.random().toString(36).slice(2, 7)}`;
      folder = await root.getDirectoryHandle(run, {create: true});
      const total = selected.reduce((sum, l) => sum + (l.static ? 1 : b - a + 1), 0);
      meta = {projectId: C.projectId, partId: part.id, fps: C.fps, bpm, width: d.width, height: d.height,
        sourceFrameStart: a, sourceFrameEnd: b, totalPartFrames: n, actualDurationSeconds: n / C.fps,
        clipToStage: clip, alpha: 'straight PNG', complete: false, writtenFiles: 0,
        visibleLayers: visibleIds(), previewMaskIncluded: false,
        layers: selected.map(l => ({id: l.id, static: !!l.static, blend: l.blend || 'source-over', expectedFiles: l.static ? 1 : b - a + 1}))};
      await writeJson(folder, 'export_manifest.json', meta);
      const output = W.canvas(d.width, d.height); $('progress').value = 0;
      for (const layer of selected) {
        if (cancelled) break;
        const dir = await folder.getDirectoryHandle(layer.id, {create: true});
        for (let i = a; i <= (layer.static ? a : b); i++) {
          if (cancelled) break;
          const blob = await png(renderTo(output, i, layer.id, clip));
          const file = await dir.getFileHandle(`${part.id}_${layer.id}_${String(i).padStart(6, '0')}.png`, {create: true});
          const stream = await file.createWritable(); try {await stream.write(blob);} finally {await stream.close();}
          written++; $('progress').value = written / total; message(`${layer.id} · ${written}/${total}`); await delay(0);
        }
      }
      meta.complete = !cancelled; meta.writtenFiles = written; await writeJson(folder, 'export_manifest.json', meta);
      message(cancelled ? `已取消；保留 ${written} 个文件，manifest 标记为未完成。` : `已完成 ${written} 个 PNG；文件夹：${run}`);
    } catch (e) {
      if (meta && folder) {meta.writtenFiles = written; meta.error = e.message; try {await writeJson(folder, 'export_manifest.json', meta);} catch {}}
      if (e.name === 'AbortError') message('已取消选取文件夹。'); else fail(e);
    } finally {lock(false);}
  };
  $('record').onclick = async () => {
    let stream, recorder, oldFrame = frame;
    try {
      $('error').textContent = ''; stop();
      const mimeType = ['video/webm;codecs=vp9', 'video/webm;codecs=vp8', 'video/webm'].find(t => window.MediaRecorder?.isTypeSupported(t));
      if (!mimeType || !view.captureStream) throw new Error('浏览器不支持 WebM 预览录制。');
      lock(true); cancelled = false;
      const recordCanvas = W.canvas(view.width, view.height), rg = recordCanvas.getContext('2d');
      function recordDraw() {
        draw(); rg.fillStyle = '#000'; rg.fillRect(0, 0, recordCanvas.width, recordCanvas.height); rg.drawImage(view, 0, 0);
      }
      frame = 0; recordDraw(); stream = recordCanvas.captureStream(C.fps);
      recorder = new MediaRecorder(stream, {mimeType, videoBitsPerSecond: 8e6});
      const chunks = []; let recordingError;
      recorder.ondataavailable = e => {if (e.data.size) chunks.push(e.data);};
      recorder.onerror = e => {recordingError = e.error || new Error('录制失败'); cancelled = true;};
      const stopped = new Promise(resolve => {recorder.onstop = resolve;}); recorder.start(250);
      const n = W.count(part, bpm), startTime = performance.now();
      message('录制中；请保持此分页在前景。视频包含目前预览遮罩，背景为黑色。');
      while (!cancelled) {
        const i = Math.floor((performance.now() - startTime) * C.fps / 1000);
        if (i >= n) break;
        frame = i; recordDraw(); $('progress').value = i / n; await delay(1000 / C.fps);
      }
      if (recorder.state !== 'inactive') recorder.stop(); await stopped;
      if (recordingError) throw recordingError;
      if (!cancelled) {download(new Blob(chunks, {type: mimeType}), `${C.projectId}_${part.id}_preview.webm`); message('预览视频已下载。');}
      else message('预览录制已取消。');
    } catch (e) {fail(e);}
    finally {if (recorder && recorder.state !== 'inactive') recorder.stop(); stream?.getTracks().forEach(t => t.stop()); frame = oldFrame; lock(false); draw();}
  };
  try {
    await W.init();
    if(C.audio?.file&&window.WORKSHOP_MEDIA[C.audio.file]){audio.src=window.WORKSHOP_MEDIA[C.audio.file];$('audio-status').textContent='已加载节目预览音乐';}
    document.title = $('title').textContent = C.title;
    $('spec').textContent = `${C.stage.width}×${C.stage.height} · ${C.fps} fps · 所有图层同尺寸带透明通道`;
    C.parts.forEach((p, i) => $('part').add(new Option(p.name, i)));
    $('bpm').value = bpm; $('width').value = C.stage.width; $('clip').checked = C.clipExportToStage;
    const vw = Math.min(C.stage.width, C.previewMaxWidth); view.width = vw; view.height = Math.max(1, Math.round(vw * C.stage.height / C.stage.width));
    setup(); $('width').oninput(); $('play').disabled = false; $('export-controls').disabled = false;
    message('已就绪。可先拖动时间轴、切换段落或下载单张检查。');
    // Stable inspection API for Codex: never mutates the selected preview part.
    window.workshopAPI = {ready: true, config: C, frameCount: (id, rate = C.bpm) => W.count(C.parts.find(p => p.id === id), rate),
      render: ({partId, frame: f = 0, layerIds, width = C.stage.width, bpm: rate = C.bpm, clip = false}) => {
        const p = C.parts.find(p => p.id === partId); if (!p) throw new Error('未知段落');
        const c = W.canvas(width, Math.max(1, Math.round(width * C.stage.height / C.stage.width)));
        return W.render(c, {part: p, frame: f, bpm: rate, layerIds: layerIds || p.layers.filter(l => l.defaultVisible !== false).map(l => l.id), clip});
      }};
  } catch (e) {fail(e); message('初始化失败，请修正后重新开启。'); $('play').disabled = true; $('export-controls').disabled = true;}
})();

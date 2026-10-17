/* Shared scene renderer. Extend a particular ID for bespoke animation. */
window.WORKSHOP_SCENES = {};
function renderShow(g, s, layer, api) {
  const {width: w, height: h} = s, colors = s.config.palette || [];
  if (layer === 'background') {
    const gradient = g.createLinearGradient(0, 0, w, h);
    gradient.addColorStop(0, colors[0] || '#101827'); gradient.addColorStop(1, colors[1] || '#261c48');
    g.fillStyle = gradient; g.fillRect(0, 0, w, h);
    for (const id of s.part.backgroundAssets || []) api.image(g, id);
    return;
  }
  const main = (s.config.screens || []).find(r => r.id === (s.part.textScreen || 'main')) || {x:0,y:0,w,h};
  if (layer === 'art') {
    const entry = s.part.loop ? 1 : 1 - Math.pow(1 - s.clamp(s.t / .8), 3);
    const pulse = s.part.loop ? 1 + .018 * Math.sin(s.phase * Math.PI * 2) : 1;
    g.save();g.translate(main.x + main.w/2, main.y + main.h/2 + main.h*.12*(1-entry));g.scale(pulse,pulse);g.globalAlpha=entry;
    g.fillStyle='rgba(8,12,24,.48)';g.fillRect(-main.w*.32,-main.h*.18,main.w*.64,main.h*.36);
    const fitText=(text,initial,maxWidth)=>{let size=initial;g.font=`700 ${size}px system-ui,"Microsoft YaHei",sans-serif`;while(size>10&&g.measureText(text).width>maxWidth){size*=.94;g.font=`700 ${size}px system-ui,"Microsoft YaHei",sans-serif`;}return size;};
    const title=String(s.part.text ?? s.config.title), subtitle=String(s.part.subtitle || '');
    g.textAlign='center';g.textBaseline='middle';g.fillStyle=colors[2]||'#f9afcf';
    fitText(title,Math.min(main.h*.16,main.w*.075),main.w*.85);g.fillText(title,0,-main.h*.035);
    g.fillStyle=colors[3]||'#87dbe5';fitText(subtitle,Math.min(main.h*.045,main.w*.03),main.w*.85);g.fillText(subtitle,0,main.h*.10);
    g.restore();return;
  }
  if (layer === 'fx') {
    const cycles=Math.max(1,Math.round(s.duration*s.bpm/60));
    const kick=Math.exp(-s.frac(s.phase*cycles)*5);
    for(let i=0;i<32;i++){
      const a=s.phase*Math.PI*2+i*Math.PI*2/32;
      const x=w/2+Math.cos(a)*w*.43,y=h/2+Math.sin(a)*h*(.32+.025*kick);
      g.fillStyle=i%2?(colors[2]||'#f9afcf'):(colors[3]||'#87dbe5');
      g.globalAlpha=.4+.5*kick;g.beginPath();g.arc(x,y,Math.max(1,h*.004)*(1+kick*.6),0,Math.PI*2);g.fill();
    }
    g.globalAlpha=1;return;
  }
  if(layer==='frame'){
    g.strokeStyle='rgba(162,192,216,.3)';g.lineWidth=Math.max(1,h*.0015);
    if(s.config.stageMask.type==='geometry'){api.shapePath(g,s.config.stageMask.shapes);g.stroke();}
  }
}
for(const part of window.WORKSHOP_CONFIG.parts) window.WORKSHOP_SCENES[part.id]=renderShow;

(function () {
  'use strict';
  if (window.PMDocument) return;
  const originals = new WeakMap();
  const ui = '[data-pm-ui]';
  const styles = document.createElement('style');
  styles.dataset.pmUi = 'style';
  styles.textContent = [
    'body{font-family:system-ui,sans-serif;color:#243530;margin:0;padding:28px;background:#f7f9f8}',
    '#prdContent{max-width:1320px;margin:auto}table{border-collapse:collapse;table-layout:fixed;width:100%;margin:18px 0}th,td{border:1px solid #dce4e0;padding:12px;position:relative;vertical-align:top;overflow-wrap:anywhere}th{background:#eef4f1}.prototype-frame{width:100%;min-width:0}',
    '.pm-controls{display:flex;gap:4px;position:absolute;left:0;bottom:0;opacity:0;z-index:3}tr:hover .pm-controls{opacity:1}.pm-controls button{font-size:11px;padding:1px 7px}',
    '.pm-col{position:absolute;right:0;top:0;width:6px;height:100%;cursor:col-resize}.pm-row{position:absolute;left:0;bottom:0;height:5px;width:100%;cursor:row-resize}',
    '.pm-edited{background:#e6f5ec}.pm-toolbar{position:fixed;bottom:18px;left:18px;display:flex;gap:8px;z-index:25;flex-wrap:wrap;max-width:90vw}',
    '.pm-toolbar button,.pm-preview button{padding:9px 12px;border:1px solid #d5e5de;border-radius:8px;cursor:pointer;background:white;color:#21654f}',
    '.pm-status{position:fixed;left:18px;bottom:68px;max-width:500px;padding:10px;border-radius:8px;background:#173d32;color:white;z-index:26;display:none}.pm-status.show{display:block}',
    '.pm-preview{position:fixed;right:0;top:0;height:100vh;width:var(--pm-panel,480px);background:#182622;color:#fff;z-index:20;display:flex;flex-direction:column}.pm-preview[hidden]{display:none}',
    '.pm-preview header{display:flex;gap:7px;align-items:center;padding:12px;flex-wrap:wrap}.pm-preview select{max-width:100%;padding:8px}.pm-shell{overflow:auto;padding:20px;flex:1;min-height:0}.pm-device{flex:0 0 auto}.pm-device iframe{border:0;transform-origin:top left}',
    '.pm-panel-grip{position:absolute;left:0;top:0;bottom:0;width:5px;cursor:col-resize}.pm-dual{padding-right:calc(var(--pm-panel,480px) + 28px)}',
    '@media(max-width:850px){.pm-preview{width:92vw}.pm-dual{padding-right:28px}.pm-toolbar{z-index:25}}',
    '@media print{[data-pm-ui]{display:none!important}body.pm-dual{padding:0}}'
  ].join('\n');
  document.querySelectorAll(ui).forEach(e => e.remove());
  document.head.append(styles);
  const content = document.getElementById('prdContent');
  if (!content) return;

  function notify(text) {
    const n = document.querySelector('.pm-status');
    n.textContent = text; n.classList.add('show');
  }
  function clean(root) {
    root.querySelectorAll(ui).forEach(e => e.remove());
    root.querySelectorAll('[contenteditable]').forEach(e => e.removeAttribute('contenteditable'));
    return root;
  }
  function matrix(section) {
    // Build logical columns so rowspan/colspan mutations keep cells aligned.
    const rows = Array.from(section.rows), grid = [];
    rows.forEach((row, r) => {
      grid[r] = grid[r] || [];
      let c = 0;
      Array.from(row.cells).forEach(cell => {
        while (grid[r][c]) c++;
        const rs = cell.rowSpan || (rows.length-r);
        for (let y=r; y<r+rs; y++) {
          grid[y] = grid[y] || [];
          for (let x=c; x<c+cell.colSpan; x++) grid[y][x] = {cell, r, c};
        }
        c += cell.colSpan;
      });
    });
    return {rows, grid};
  }
  function changeRow(row, remove) {
    const section = row.parentElement, {rows, grid} = matrix(section);
    const index = rows.indexOf(row);
    if (remove && rows.length <= 1) return;
    const seen = new Set();
    if (remove) {
      (grid[index] || []).forEach(entry => {
        if (!entry || seen.has(entry.cell)) return;
        const cell = entry.cell; seen.add(cell);
        if (entry.r < index) cell.rowSpan = Math.max(1, cell.rowSpan - 1);
        else if (cell.rowSpan > 1 && rows[index+1]) {
          cell.rowSpan -= 1;
          const nextEntries = grid[index+1] || [];
          const following = Array.from(rows[index+1].cells).find(c =>
            nextEntries.findIndex(e => e && e.cell === c) > entry.c);
          rows[index+1].insertBefore(cell, following || null);
        }
      });
      row.remove();
    } else {
      const created = document.createElement('tr'), insert = index + 1;
      (grid[index] || []).forEach(entry => {
        if (!entry || seen.has(entry.cell)) return;
        const cell = entry.cell; seen.add(cell);
        if (entry.r + cell.rowSpan > insert || cell.rowSpan === 0) {
          if (cell.rowSpan !== 0) cell.rowSpan += 1;
        } else {
          const blank = document.createElement(cell.tagName);
          blank.colSpan = cell.colSpan;
          blank.innerHTML = '<br>';
          created.append(blank);
        }
      });
      row.after(created);
    }
    initEditing();
  }
  function initEditing() {
    content.querySelectorAll(ui).forEach(e => e.remove());
    content.querySelectorAll('table:not(.no-edit)').forEach(table => {
      const first = table.rows[0];
      if (!first) return;
      if (!table.querySelector(':scope > colgroup')) {
        const group = document.createElement('colgroup');
        let count = Array.from(first.cells).reduce((n,c) => n + c.colSpan, 0);
        while (count--) group.append(document.createElement('col'));
        table.prepend(group);
      }
      let colIndex = 0;
      Array.from(first.cells).forEach(cell => {
        const grip = document.createElement('span');
        grip.className = 'pm-col'; grip.dataset.pmUi = 'column'; grip.dataset.index = colIndex;
        cell.append(grip); colIndex += cell.colSpan;
      });
      Array.from(table.tBodies).forEach(section => Array.from(section.rows).forEach(row => {
        if (Array.from(row.cells).every(c => c.tagName === 'TH') || !row.cells[0]) return;
        const controls = document.createElement('span');
        controls.className = 'pm-controls'; controls.dataset.pmUi = 'rows'; controls.contentEditable = 'false';
        controls.innerHTML = '<button type="button" data-pm-action="add-row" aria-label="下方插入一行">＋</button><button type="button" data-pm-action="delete-row" aria-label="删除本行">−</button>';
        row.cells[0].append(controls);
        const grip = document.createElement('span'); grip.className='pm-row'; grip.dataset.pmUi='row';
        row.cells[0].append(grip);
      }));
    });
    content.querySelectorAll('td,th,p,li,h1,h2,h3,h4,blockquote,dd,dt').forEach(el => {
      if (el.closest(ui + ',.no-edit') || el.querySelector('iframe,img,table,video,canvas,pre')) return;
      el.contentEditable = 'true';
      if (!originals.has(el)) originals.set(el, el.textContent);
    });
    scaleEmbeds();
  }
  function scaleEmbeds(width) {
    content.querySelectorAll('.prototype-frame').forEach(outer => {
      const iframe=outer.querySelector('iframe');if(!iframe)return;
      const w=Number(outer.dataset.pw)||390,h=Number(outer.dataset.ph)||844;
      if(width)outer.style.width=width+'px';
      const visible=outer.clientWidth||320;
      outer.style.position='relative';outer.style.height=Math.round(h*visible/w)+'px';outer.style.overflow='hidden';
      iframe.style.cssText='position:absolute;left:0;top:0;border:0;transform-origin:top left;width:'+w+'px;height:'+h+'px;transform:scale('+visible/w+')';
      if(!outer.querySelector('.pm-proto-grip')&&!window.PM_RUNTIME?.readOnly){
        const grip=document.createElement('span');grip.dataset.pmUi='proto-size';grip.className='pm-proto-grip';grip.title='拖拽缩放原型';
        grip.style.cssText='position:absolute;right:0;bottom:0;width:16px;height:16px;cursor:nwse-resize;background:#2c876d80';outer.append(grip);
      }
    });
  }
  document.addEventListener('focusout', e => {
    if (originals.has(e.target) && originals.get(e.target) !== e.target.textContent) e.target.classList.add('pm-edited');
  });
  let catalog = [];
  try { catalog = JSON.parse(document.getElementById('prdPages')?.textContent || '[]'); } catch (e) { notify(e.message); }
  let current = catalog[0]?.value, zoom = null, lockUntil = 0;
  const toolbar = document.createElement('div');
  toolbar.className='pm-toolbar'; toolbar.dataset.pmUi='toolbar';
  toolbar.innerHTML='<button data-pm-action="copy">一键复制全文</button><button data-pm-action="refresh-copy">重新生成图片并复制</button><button data-pm-action="preview">双栏预览</button><button data-pm-action="save">保存</button><button data-pm-action="download">下载副本</button>';
  const status = document.createElement('div'); status.className='pm-status'; status.dataset.pmUi='status'; status.role='status';
  document.body.append(toolbar,status);
  const panel=document.createElement('aside'); panel.className='pm-preview'; panel.dataset.pmUi='preview';
  panel.innerHTML='<div class="pm-panel-grip"></div><header><select aria-label="原型页面"></select><button data-pm-action="minus">－</button><span class="pm-zoom"></span><button data-pm-action="plus">＋</button><button data-pm-action="fit">适配</button><button data-pm-action="preview">关闭</button></header><div class="pm-shell"><div class="pm-device"><iframe title="交互原型预览"></iframe></div></div>';
  document.body.append(panel);
  const select=panel.querySelector('select'), frame=panel.querySelector('iframe'), wrap=panel.querySelector('.pm-device');
  catalog.forEach(item => {const o=document.createElement('option'); o.value=item.value;o.textContent=item.label;select.append(o);});
  function scale() {
    const item=catalog.find(c=>c.value===current);
    if (!item) return;
    const factor=zoom===null ? Math.max(100,panel.querySelector('.pm-shell').clientWidth-40)/item.w : zoom;
    frame.style.width=item.w+'px'; frame.style.height=item.h+'px'; frame.style.transform='scale('+factor+')';
    wrap.style.width=item.w*factor+'px';wrap.style.height=item.h*factor+'px';
    panel.querySelector('.pm-zoom').textContent=Math.round(factor*100)+'%';
  }
  function showPage(value) {
    const item=catalog.find(c=>c.value===value);
    if (!item) return;
    current=value; select.value=value; frame.src=item.url; requestAnimationFrame(scale);
  }
  function togglePreview() {panel.hidden=!panel.hidden;document.body.classList.toggle('pm-dual',!panel.hidden);requestAnimationFrame(()=>{scale();scaleEmbeds();});}
  select.addEventListener('change',()=>{lockUntil=Date.now()+4000;showPage(select.value);});
  addEventListener('resize',()=>{scale();scaleEmbeds();});
  addEventListener('message',e=>{
    if(e.source!==frame.contentWindow||e.data?.type!=='page-changed')return;
    if(catalog.some(c=>c.value===e.data.page)){current=e.data.page;select.value=current;lockUntil=Date.now()+4000;scale();}
  });
  addEventListener('scroll',()=>{
    if(panel.hidden||Date.now()<lockUntil)return;
    let node;
    content.querySelectorAll('[data-preview]').forEach(n=>{if(n.getBoundingClientRect().top<=innerHeight*.35)node=n;});
    if(node && node.dataset.preview!==current) showPage(node.dataset.preview);
  },{passive:true});
  document.addEventListener('pointerdown',e=>{
    const grip=e.target.closest('.pm-col,.pm-row,.pm-panel-grip,.pm-proto-grip');
    if(!grip)return;e.preventDefault();
    const x=e.clientX,y=e.clientY, cell=grip.closest('th,td');
    const table=cell?.closest('table'),row=cell?.parentElement;
    const width=cell?.getBoundingClientRect().width,height=row?.getBoundingClientRect().height,panelWidth=panel.offsetWidth;
    const protoWidth=grip.closest('.prototype-frame')?.clientWidth;
    function move(ev){
      if(grip.classList.contains('pm-proto-grip')){
        scaleEmbeds(Math.max(160,Math.min(1200,protoWidth+ev.clientX-x)));
      }else if(grip.classList.contains('pm-col')){
        const col=table.querySelectorAll('colgroup col')[Number(grip.dataset.index)];
        if(col)col.style.width=Math.max(48,width+ev.clientX-x)+'px';scaleEmbeds();
      }else if(grip.classList.contains('pm-row'))row.style.height=Math.max(24,height+ev.clientY-y)+'px';
      else {document.body.style.setProperty('--pm-panel',Math.max(320,Math.min(innerWidth-200,panelWidth+x-ev.clientX))+'px');scale();scaleEmbeds();}
    }
    function up(){document.removeEventListener('pointermove',move);document.removeEventListener('pointerup',up);}
    document.addEventListener('pointermove',move);document.addEventListener('pointerup',up);
  });
  async function writeClipboard(html,text) {
    try {
      if(!navigator.clipboard||!window.ClipboardItem)throw Error('fallback');
      await navigator.clipboard.write([new ClipboardItem({'text/html':new Blob([html],{type:'text/html'}),'text/plain':new Blob([text],{type:'text/plain'})})]);
    }catch(e){
      const el=document.createElement('div');el.contentEditable='true';el.style.cssText='position:fixed;left:-99999px';el.innerHTML=html;document.body.append(el);
      const range=document.createRange();range.selectNodeContents(el);const selection=getSelection();selection.removeAllRanges();selection.addRange(range);
      const ok=document.execCommand('copy');selection.removeAllRanges();el.remove();if(!ok)throw Error('浏览器拒绝复制');
    }
  }
  async function shrink(data) {
    return new Promise(resolve=>{
      const im=new Image(); im.onload=()=>{
        if(im.width<=2000){resolve(data);return;}
        try{const c=document.createElement('canvas');c.width=2000;c.height=Math.round(im.height*2000/im.width);const ctx=c.getContext('2d');ctx.fillStyle='white';ctx.fillRect(0,0,c.width,c.height);ctx.drawImage(im,0,0,c.width,c.height);resolve(c.toDataURL('image/jpeg',.9));}catch(e){resolve(data);}
      };im.onerror=()=>resolve(data);im.src=data;
    });
  }
  let copying=false;
  async function copyAll(force) {
    if(copying)return;copying=true;
    try {
      const clone=clean(content.cloneNode(true));
      const live=content.querySelectorAll('img,iframe'), images=clone.querySelectorAll('img,iframe');
      live.forEach((n,i)=>{if(images[i]){images[i].style.width=Math.round(n.getBoundingClientRect().width)+'px';images[i].style.maxWidth='100%';}});
      const cache=new Map();let ok=0,failed=0;
      for(const el of Array.from(images)){
        const src=el.getAttribute('src');if(!src)continue;
        if(src.startsWith('data:')){ok++;continue;}
        notify('正在处理图片 '+(ok+failed+1)+'/'+images.length);
        try{
          const key=el.tagName+src;
          if(!cache.has(key)){
            const data=el.tagName==='IFRAME'?await window.snapshotPrototypeViaServer(src,{force}):await window.inlineAssetViaServer(src,{});
            cache.set(key,await shrink(data.dataUrl));
          }
          const im=document.createElement('img');im.src=cache.get(key);im.alt=el.getAttribute('title')||el.getAttribute('alt')||'原型图';
          im.style.cssText=el.style.cssText+';height:auto;transform:none;position:static';
          const outer=el.closest('.prototype-frame');
          if(outer){outer.style.cssText='height:auto;overflow:visible';}
          el.replaceWith(im);ok++;
        }catch(e){
          const fallback=document.createElement('p');fallback.textContent='[图片未复制：'+(el.title||el.alt||src)+']';el.replaceWith(fallback);failed++;
        }
      }
      clone.querySelectorAll('.pm-edited').forEach(e=>e.classList.remove('pm-edited'));
      clone.querySelectorAll('table').forEach(t=>t.style.cssText+=';border-collapse:collapse;width:100%');
      clone.querySelectorAll('th,td').forEach(c=>c.style.cssText+=';border:1px solid #ccc;padding:8px;vertical-align:top');
      clone.querySelectorAll('button,script').forEach(e=>e.remove());
      await writeClipboard('<meta charset="utf-8">'+clone.innerHTML,clone.textContent);
      notify('已复制，包含 '+ok+' 张图'+(failed?'，'+failed+' 张缺失，已标注位置':'。目标文档首次粘贴请确认图片显示正常'));
      return {ok,failed};
    }finally{copying=false;}
  }
  function serialize(){
    const clone=clean(document.documentElement.cloneNode(true));
    clone.querySelector('body').classList.remove('pm-dual');
    return '<!doctype html>\n'+clone.outerHTML;
  }
  document.addEventListener('click',async e=>{
    const button=e.target.closest('[data-pm-action]');if(!button)return;
    e.preventDefault();
    try{
      const action=button.dataset.pmAction;
      if(action==='add-row'||action==='delete-row')changeRow(button.closest('tr'),action==='delete-row');
      if(action==='preview')togglePreview();
      if(action==='fit'){zoom=null;scale();}
      if(action==='plus'||action==='minus'){
        const now=parseFloat(panel.querySelector('.pm-zoom').textContent)/100;
        const steps=[.25,.5,.75,1,1.25,1.5,2,3];
        zoom=(action==='plus'?steps.find(s=>s>now+.001):steps.reverse().find(s=>s<now-.001))||now;scale();
      }
      if(action==='copy'||action==='refresh-copy')await copyAll(action==='refresh-copy');
      if(action==='save'){
        button.disabled=true;
        const result=await window.PMService.save(serialize());
        notify('已保存并备份。请让 AI 读取文件以同步相关产物');
        window.dispatchEvent(new CustomEvent('pm-saved',{detail:result}));
      }
      if(action==='download'){
        const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([serialize()],{type:'text/html'}));a.download=decodeURIComponent(location.pathname.split('/').pop()||'PRD.html');a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);
        notify('已下载副本，原文件未被覆盖');
      }
    }catch(error){notify(error.message);}finally{button.disabled=false;}
  });
  if(!window.PM_RUNTIME?.readOnly)initEditing();else scaleEmbeds();
  panel.hidden=!catalog.length;
  document.body.classList.toggle('pm-dual',!!catalog.length);
  if(catalog.length)showPage(current);
  requestAnimationFrame(()=>scaleEmbeds());
  if(window.ResizeObserver)new ResizeObserver(()=>scaleEmbeds()).observe(content);
  window.PMDocument={initEditing,serialize,copyAll,matrix};
  if(window.PM_RUNTIME?.readOnly)notify('只读分享模式，可浏览或下载副本');
  else window.PMService?.revision().catch(e=>notify('保存尚未就绪：'+e.message));
})();

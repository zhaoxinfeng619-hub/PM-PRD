(function () {
  'use strict';
  const source=document.getElementById('acceptanceData');
  if(!source)return;
  const spec=JSON.parse(source.textContent);
  const states=['待验收','通过','未通过','跳过'];
  if(!spec.version||!Array.isArray(spec.cases))throw Error('验收清单缺少版本或用例');
  const ids=new Set();
  spec.cases.forEach(item=>{
    if(!item.id||ids.has(item.id)||!item.preconditions||!Array.isArray(item.steps)||!item.steps.length||!item.expected)throw Error('用例字段缺失或编号重复');
    ids.add(item.id);
  });
  const key='pm-acceptance:'+location.pathname+':'+spec.version;
  const signature=item=>JSON.stringify([item.preconditions,item.data,item.steps,item.expected]);
  const empty=item=>({status:'待验收',actual:'',evidence:'',reason:'',tester:'',time:'',signature:signature(item),history:[]});
  let records={};
  try{records=JSON.parse(localStorage.getItem(key)||'{}');}catch(e){}
  spec.cases.forEach(item=>{
    const old=records[item.id];
    if(!old)records[item.id]=empty(item);
    else if(old.signature!==signature(item)||!states.includes(old.status))records[item.id]=Object.assign(empty(item),{history:[...(old.history||[]),old]});
  });
  function store(){localStorage.setItem(key,JSON.stringify(records));}
  function stats(){
    const counts=Object.fromEntries(states.map(s=>[s,0]));
    spec.cases.forEach(item=>counts[records[item.id].status]++);
    const executed=counts['通过']+counts['未通过'],eligible=spec.cases.length-counts['跳过'];
    return {counts,total:spec.cases.length,completion:eligible?executed/eligible:null,passRate:executed?counts['通过']/executed:null};
  }
  function set(id,patch){
    if(!ids.has(id))throw Error('未知用例');
    const record=Object.assign({},records[id],patch);
    if(!states.includes(record.status))throw Error('无效状态');
    if(record.status==='跳过'&&!record.reason.trim())throw Error('跳过必须填写原因');
    if(['通过','未通过'].includes(record.status)&&(!record.actual.trim()||!record.evidence.trim()||!record.tester.trim()))throw Error('请填写实际结果、验证证据和验收人');
    record.time=new Date().toISOString();
    records[id]=record;store();render();
  }
  function exported(){return {version:spec.version,path:location.pathname,stats:stats(),records};}
  function imported(data){
    if(data.version!==spec.version||data.path!==location.pathname)throw Error('清单或版本不一致，无法覆盖');
    if(!data.records||Array.isArray(data.records))throw Error('导入记录格式错误');
    for(const [id,record] of Object.entries(data.records)){
      const item=spec.cases.find(c=>c.id===id);
      if(!item||record.signature!==signature(item)||!states.includes(record.status))throw Error('用例或预期结果不一致');
      if(['actual','evidence','reason','tester'].some(k=>typeof record[k]!=='string'))throw Error('导入字段不完整');
      if(record.status==='跳过'&&!record.reason.trim())throw Error('缺少跳过原因');
      if(['通过','未通过'].includes(record.status)&&(!record.actual.trim()||!record.evidence.trim()||!record.tester.trim()))throw Error('缺少实际验证记录');
    }
    const validated=Object.fromEntries(Object.entries(data.records).map(([id,r])=>[id,{status:r.status,actual:r.actual,evidence:r.evidence,reason:r.reason,tester:r.tester,time:typeof r.time==='string'?r.time:'',signature:r.signature,history:Array.isArray(r.history)?r.history:[]}]));
    records=Object.assign({},records,validated);store();render();
  }
  const root=document.getElementById('acceptanceContent')||document.body;
  let filter='全部';
  const text=(tag,value)=>{const el=document.createElement(tag);el.textContent=value;return el;};
  function render(){
    root.replaceChildren();
    const status=stats();
    root.append(text('h1',spec.title||'功能验收清单'));
    root.append(text('p','验收版本 '+spec.version+' · 进度仅保存在当前浏览器，导出 JSON 可传递记录'));
    const percent=n=>n===null?'暂无可计算样本':Math.round(n*100)+'%';
    root.append(text('p','执行完成率 '+percent(status.completion)+' · 通过率 '+percent(status.passRate)+' · 跳过 '+status.counts['跳过']));
    const select=document.createElement('select');select.ariaLabel='状态筛选';
    ['全部',...states].forEach(s=>{const o=text('option',s);o.value=s;select.append(o);});select.value=filter;
    select.onchange=()=>{filter=select.value;render();};root.append(select);
    const groups=new Map();
    spec.cases.filter(item=>filter==='全部'||records[item.id].status===filter).forEach(item=>{
      const name=item.module||'功能验收';
      if(!groups.has(name)){const d=document.createElement('details');d.open=true;d.append(text('summary',name));root.append(d);groups.set(name,d);}
      const r=records[item.id],card=document.createElement('article');card.dataset.case=item.id;
      card.append(text('h3',item.id+' '+(item.title||'')+' · '+(item.priority||'待定')));
      card.append(text('p','前置条件：'+item.preconditions),text('p','步骤：'+item.steps.join('；')),text('p','预期结果：'+item.expected));
      const controls={};
      for(const [k,label] of Object.entries({actual:'实际结果',evidence:'验证证据',reason:'跳过/阻塞原因',tester:'验收人'})){
        const input=document.createElement('input');input.placeholder=label;input.ariaLabel=label;input.value=r[k];controls[k]=input;card.append(input);
      }
      const picker=document.createElement('select');picker.ariaLabel='验收状态';
      states.forEach(s=>{const o=text('option',s);o.value=s;picker.append(o);});picker.value=r.status;
      const apply=text('button','保存结果'),message=text('p','');
      apply.onclick=()=>{try{set(item.id,{status:picker.value,...Object.fromEntries(Object.entries(controls).map(([k,input])=>[k,input.value]))});}catch(e){message.textContent=e.message;}};
      card.append(picker,apply,message);groups.get(name).append(card);
    });
    const download=text('button','导出验收 JSON');
    download.onclick=()=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([JSON.stringify(exported(),null,2)],{type:'application/json'}));a.download='验收记录.json';a.click();setTimeout(()=>URL.revokeObjectURL(a.href),1000);};
    const file=document.createElement('input');file.type='file';file.accept='.json';file.ariaLabel='导入验收 JSON';
    file.onchange=async()=>{try{imported(JSON.parse(await file.files[0].text()));}catch(e){alert(e.message);}};
    root.append(download,file);
  }
  store();render();
  window.PMAcceptance={stats,set,exported,imported};
})();

/* EpiRed | Experiencia de vigilancia y operaciones. API real en Python.
   No usar resultados para decisiones clínicas o emergencias. */
'use strict';
const $ = id => document.getElementById(id);
const fmt = n => new Intl.NumberFormat('es-CO', {maximumFractionDigits:1}).format(n ?? 0);
const safe = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const icon = n => `<svg aria-hidden="true"><use href="#ic-${n}"/></svg>`;
const state = {screen:'inicio', enfermedad:'COVID-19', red:null, selected:'C', mapLayer:'casos', maps:{}, results:{}, requests:0};
const groupColors = ['#13b699','#698dde','#e3ad51','#9278ce','#ed8472','#56b2ba'];
const navLabels = {inicio:'Centro de control', vigilancia:'Mapa de enfermedades', muestras:'Traslado de muestras',alertas:'Alertas territoriales',enlaces:'Continuidad de la red',brigadas:'Brigadas sanitarias',insumos:'Distribución de insumos',registros:'Registros y datos'};
const labelOff = {A:[-26,-20],B:[-19,-19],C:[-70,9],D:[22,-9],E:[16,30],F:[-19,27],G:[-32,-20],H:[-22,-19],I:[-18,-11],J:[12,25]};
let toastTimer;

async function api(path,query={}){
  const qs = new URLSearchParams(query).toString();
  const resp = await fetch(`/api/${path}${qs?'?'+qs:''}`,{cache:'no-store'});
  let body;
  try{body=await resp.json()}catch{throw Error('El servidor no devolvió JSON. Inicia con python server.py.')}
  if(!resp.ok) throw Error(body.error||`Error HTTP ${resp.status}`);
  return body;
}
async function post(path,payload){
  const resp = await fetch(`/api/${path}`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const body=await resp.json();
  if(!resp.ok)throw Error(body.error||'No se pudo guardar');
  return body;
}
function toast(message,error=false){const el=$('toast');el.textContent=message;el.className='toast visible'+(error?' error':'');clearTimeout(toastTimer);toastTimer=setTimeout(()=>el.className='toast',4200)}
function zone(id){return state.red?.zonas.find(z=>z.id===id)}
function name(id){return zone(id)?.nombre||id}
function badge(carga){return `<span class="load-pill ${safe(carga)}">${safe(carga)}</span>`}
function stat(label,value,sub,ic,theme=''){return `<div class="stat-card"><div class="stat-label"><span>${safe(label)}</span><div class="stat-icon ${theme}">${icon(ic)}</div></div><div class="stat-number">${typeof value==='string'&&!Number.isFinite(Number(value))?safe(value):fmt(value)}</div><div class="stat-sub">${safe(sub)}</div></div>`}

function selectOptions(id,initial){const e=$(id);if(!e||!state.red)return;const prev=e.value||initial||'A';e.innerHTML=state.red.zonas.map(z=>`<option value="${z.id}">${safe(z.nombre)}</option>`).join('');e.value=state.red.zonas.some(z=>z.id===prev)?prev:initial||'A'}
function initOptions(){
 const defaults={
  'traslado-origen':'A','traslado-destino':'F','traslado-via':'D',
  'alerta-origen':'A','insumos-origen':'A','edit-zona':'C'
 };
 Object.entries(defaults).forEach(([id,v])=>selectOptions(id,v));
 const select=$('enlace-seleccion');let current=select.value||'G-J';
 select.innerHTML=state.red.aristas.map(a=>`<option value="${a.desde}-${a.hasta}">${safe(name(a.desde))} ↔ ${safe(name(a.hasta))} · ${fmt(a.minutos)} min</option>`).join('');
 select.value=[...select.options].some(o=>o.value===current)?current:'G-J';
 if(!select.value)select.value=state.red.aristas[0].desde+'-'+state.red.aristas[0].hasta;
 const d=$('insumos-destinos');
 const before=[...d.querySelectorAll('input:checked')].map(e=>e.value);
 d.innerHTML=state.red.zonas.map(z=>`<label><input type="checkbox" value="${z.id}" ${before.length?before.includes(z.id)?'checked':'':z.id!=='A'?'checked':''}> ${safe(z.nombre)}</label>`).join('');
 updateDestCounter();syncEditor();
}
function updateDestCounter(){const n=$('insumos-destinos').querySelectorAll('input:checked').length;$('destino-counter').textContent=`(${n} seleccionados)`}

async function reloadData(){
 const stamp=++state.requests;
 const data=await api('estado',{enfermedad:state.enfermedad});
 if(stamp!==state.requests)return;
 state.red=data;
 initOptions();renderCurrent();
}
function navigate(section){
 if(!navLabels[section])return;
 state.screen=section;
 document.querySelectorAll('.screen').forEach(x=>x.classList.toggle('active',x.id===`screen-${section}`));
 document.querySelectorAll('[data-screen]').forEach(x=>x.classList.toggle('selected',x.dataset.screen===section));
 $('crumb').textContent=navLabels[section];
 $('sidebar').classList.remove('open');
 window.scrollTo({top:0,behavior:'instant'});
 renderCurrent();
}
function renderCurrent(){
 if(!state.red)return;
 if(state.screen==='inicio')return renderHome();
 if(state.screen==='vigilancia')return renderVigilancia();
 if(state.screen==='registros')return renderRegistros();
 if(state.screen==='brigadas')return state.results.brigadas?renderBrigadas():runBrigadas();
 if(state.screen==='muestras')return state.results.muestras?renderMuestras():runMuestras();
 if(state.screen==='alertas')return state.results.alertas?renderAlertas():runAlertas();
 if(state.screen==='enlaces')return state.results.enlaces?renderEnlaces():runEnlaces();
 if(state.screen==='insumos')return state.results.insumos?renderInsumos():runInsumos();
}
function renderHome(){
 const r=state.red.resumen;
 $('stats-home').innerHTML=stat('Casos confirmados',r.confirmados,'Reportes acumulados del escenario','activity')+
 stat('Casos activos',r.activos,'Confirmados − recuperados − fallecidos','bell','blue')+
 stat('Recuperados',r.recuperados,'Cifra acumulada de ejemplo','check','purple')+
 stat('Zonas con carga alta',r.carga_alta,'Umbral didáctico: ≥ 50 activos','map','orange');
 const sorted=[...state.red.zonas].sort((a,b)=>b.activos-a.activos);
 const max=sorted[0]?.activos||1;
 $('priority-list').innerHTML=sorted.slice(0,5).map((z,i)=>`<button class="priority-row" data-select="${z.id}"><span class="priority-num">${String(i+1).padStart(2,'0')}</span><span class="priority-label"><strong>${safe(z.nombre)}</strong><small>${safe(z.carga)} carga · piloto</small></span><span class="priority-right"><strong>${fmt(z.activos)}</strong><small>activos</small><span class="tiny-bar"><i style="width:${100*z.activos/max}%"></i></span></span></button>`).join('');
 $('active-chart').innerHTML=sorted.map(z=>`<div class="chart-row"><span>${safe(z.nombre)}</span><div class="chart-track"><div class="${z.carga.toLowerCase()}" style="width:${Math.max(1,100*z.activos/max)}%"></div></div><strong>${fmt(z.activos)}</strong></div>`).join('');
 $('chart-disease').textContent=state.enfermedad;
 renderMap('map-inicio',{network:true,selected:state.selected});
}
function renderVigilancia(){
 const r=state.red.resumen;
 $('stats-vigilancia').innerHTML=stat('Zonas bajo seguimiento',r.zonas,'Municipios incluidos en el piloto','pin')+
 stat('Casos activos',r.activos,`Evento: ${state.enfermedad}`,'activity','blue')+
 stat('Zonas de carga alta',r.carga_alta,'Con ≥ 50 activos en la simulación','shield','orange');
 document.querySelectorAll('#layer-chooser button').forEach(x=>x.classList.toggle('active',x.dataset.mapLayer===state.mapLayer));
 renderMap('map-vigilancia',{network:state.mapLayer==='red',selected:state.selected});
 renderDetail();
}
function renderDetail(){
 const z=zone(state.selected)||state.red.zonas[0];if(!z)return;
 $('zone-detail').innerHTML=`<div class="zone-profile"><div class="zone-profile-head"><div><small>Municipio · ${safe(z.id)}</small><br><strong>${safe(z.nombre)}</strong></div>${badge(z.carga)}</div><div class="zone-profile-grid"><div><span>Confirmados</span><b>${fmt(z.confirmados)}</b></div><div><span>Activos</span><b>${fmt(z.activos)}</b></div><div><span>Recuperados</span><b>${fmt(z.recuperados)}</b></div><div><span>Fallecidos</span><b>${fmt(z.fallecidos)}</b></div></div></div>`;
 $('municipality-list').innerHTML=state.red.zonas.map(v=>`<button class="municipality-row ${v.id===z.id?'active':''}" data-select="${v.id}"><span>${safe(v.nombre)}</span><span>${fmt(v.activos)} activos</span></button>`).join('');
}

// Proyección cartográfica Web Mercator y teselas XYZ. Las capas de puntos y enlaces
// funcionan también sin internet; OpenStreetMap aporta únicamente el fondo opcional.
function mercator(lat,lon,z){
 const size=256*Math.pow(2,z);
 const latR=Math.max(-85,Math.min(85,lat))*Math.PI/180;
 return [(lon+180)/360*size,(1-Math.log(Math.tan(latR)+1/Math.cos(latR))/Math.PI)/2*size];
}
function poly(seq,coord){return (seq||[]).map(id=>{const p=coord[id];return p?`${p[0].toFixed(1)},${p[1].toFixed(1)}`:''}).filter(Boolean).join(' ')}
function renderMap(id,opts={}){
 const host=$(id);if(!host||!state.red||host.getClientRects().length===0)return;
 const w=host.clientWidth,h=host.clientHeight;if(w<20||h<20)return;
 const baseZoom=w<450?9.55:h<355?10.05:h<430?10.2:10.4;
 const zoom=state.maps[id]?.zoom??baseZoom;
 const center=[6.269,-75.487];const [cx,cy]=mercator(...center,zoom);
 const coords={};
 state.red.zonas.forEach(z=>{let [px,py]=mercator(z.lat,z.lon,zoom);coords[z.id]=[w/2+px-cx,h/2+py-cy]});
 // Render tiles of the nearest lower zoom; CSS scales each tile for fractional zoom.
 const zTile=Math.floor(zoom);const factor=Math.pow(2,zoom-zTile);const tile=256*factor;
 const txCenter=cx/tile,tyCenter=cy/tile;
 const x0=Math.floor(txCenter-w/(2*tile))-1,x1=Math.ceil(txCenter+w/(2*tile))+1;
 const y0=Math.floor(tyCenter-h/(2*tile))-1,y1=Math.ceil(tyCenter+h/(2*tile))+1;
 let tiles='';const max=Math.pow(2,zTile);
 for(let x=x0;x<=x1;x++)for(let y=y0;y<=y1;y++){
  if(y<0||y>=max)continue;
  const left=Math.round(w/2+(x-txCenter)*tile),top=Math.round(h/2+(y-tyCenter)*tile);
  if(x<0||x>=max)continue;
  tiles+=`<img class="map-tile" alt="" loading="lazy" src="https://tile.openstreetmap.org/${zTile}/${x}/${y}.png" style="left:${left}px;top:${top}px;width:${tile+1}px;height:${tile+1}px">`;
 }
 let svg=`<svg class="map-svg" viewBox="0 0 ${w} ${h}" role="group" aria-label="Mapa georreferenciado de los municipios del piloto">`;
 if(opts.network){
  svg+=state.red.aristas.map(e=>`<line class="network-edge" x1="${coords[e.desde][0]}" y1="${coords[e.desde][1]}" x2="${coords[e.hasta][0]}" y2="${coords[e.hasta][1]}"><title>${safe(name(e.desde))} a ${safe(name(e.hasta))}: ${fmt(e.minutos)} minutos simulados</title></line>`).join('');
 }
 for(const path of opts.paths||[]){
  if(!path.seq?.length)continue;
  svg+=`<polyline class="route-line ${path.kind==='baseline'?'route-base':'route-main'}" points="${poly(path.seq,coords)}"/>`;
 }
 if(opts.disabled?.length===2){
  const a=coords[opts.disabled[0]],b=coords[opts.disabled[1]];
  svg+=`<line class="route-line route-disabled" x1="${a[0]}" y1="${a[1]}" x2="${b[0]}" y2="${b[1]}"/>`;
 }
 const zMax=Math.max(1,...state.red.zonas.map(z=>z.activos));
 const draw=[...state.red.zonas].sort((a,b)=>a.activos-b.activos);
 for(const z of draw){
  const [x,y]=coords[z.id];if(x < -140||x>w+140||y < -140||y>h+140)continue;
  let color=z.carga==='Alta'?'#e57663':z.carga==='Media'?'#e0ac4c':'#16b39b';
  let opacity=1;
  if(opts.groups)color=groupColors[opts.groups[z.id]%groupColors.length];
  if(opts.levels){
   const level=opts.levels[z.id];
   if(level===0)color='#097f76';
   else if(level!==undefined&&level<=opts.maxLevel)color=groupColors[(level-1)%groupColors.length];
   else {color='#96aeb9';opacity=.55}
  }
  const highlight=z.id===opts.selected||opts.highlight?.includes(z.id);
  const rad=opts.groups?12:Math.max(8,Math.min(18,8+Math.sqrt(z.activos/zMax)*10));
  const [lx,ly]=labelOff[z.id]||[12,-12];
  svg+=`<g class="town-node" role="button" tabindex="0" data-point="${z.id}" aria-label="Ver ${safe(z.nombre)}, ${fmt(z.activos)} casos activos" opacity="${opacity}"><title>${safe(z.nombre)} · ${fmt(z.activos)} activos de ${safe(state.enfermedad)} (simulado)</title>`;
  if(highlight)svg+=`<circle cx="${x}" cy="${y}" r="${rad+9}" fill="none" stroke="${color}" stroke-width="3" opacity=".45"/>`;
  svg+=`<circle class="node-core" cx="${x}" cy="${y}" r="${rad}" fill="${color}"/><circle cx="${x}" cy="${y}" r="3.2" fill="#fff" opacity=".93"/>`;
  if(opts.stops?.[z.id]!==undefined)svg+=`<circle cx="${x+rad-3}" cy="${y-rad+3}" r="11" fill="#143e50" stroke="#fff" stroke-width="2"/><text x="${x+rad-3}" y="${y-rad+6}" text-anchor="middle" class="stop-index">${opts.stops[z.id]}</text>`;
  svg+=`<text class="town-label" x="${x+lx}" y="${y+ly}" text-anchor="${lx<0?'end':'start'}">${safe(z.nombre)}</text></g>`;
 }
 svg+='</svg>';
 host.innerHTML=`<div class="map-tiles" aria-hidden="true">${tiles}</div>${svg}<div class="map-location">${icon('pin')} Antioquia · Colombia</div><div class="map-controls"><button type="button" data-mapzoom="plus" data-target="${id}" aria-label="Acercar mapa">+</button><button type="button" data-mapzoom="minus" data-target="${id}" aria-label="Alejar mapa">−</button><button type="button" data-mapzoom="reset" data-target="${id}" aria-label="Restablecer zoom" style="font-size:13px">⌖</button></div><div class="map-schematic">Centros urbanos georreferenciados · relaciones esquemáticas</div><div class="map-scale"><a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a> · ${Math.round(zoom*10)/10}x</div>`;
}

async function runMuestras(){try{
 const q={origen:$('traslado-origen').value,destino:$('traslado-destino').value,via:$('traslado-via').value};
 const result=await api('operaciones/traslado',q);state.results.muestras=result;
 if(state.screen==='muestras')renderMuestras();
 }catch(e){toast(e.message,true);$('traslado-summary').textContent=e.message}}
function renderMuestras(){const r=state.results.muestras;if(!r)return;
 const positive=r.minutos_ahorrados>0;
 $('traslado-summary').innerHTML=`<div class="result-label">${positive?'REDUCCIÓN SIMULADA DE TIEMPO':'DIFERENCIA FRENTE A LA REFERENCIA'}</div><div class="result-hero"><div class="big">${fmt(r.porcentaje_ahorro)}<span>%</span></div><small>comparado con el paso obligatorio por ${safe(name(r.referencia.via))}<br>en esta red de ensayo</small></div><span class="${positive?'status-good':'status-bad'}">${icon(positive?'check':'info')} ${positive?'Traslado más corto en el escenario':'Sin reducción de tiempo en el escenario'}</span><div class="result-metrics"><div class="metric-mini"><span>Ruta recomendada</span><strong>${fmt(r.optima.costo_minutos)} <em>min</em></strong></div><div class="metric-mini"><span>Ruta de referencia</span><strong>${fmt(r.referencia.costo_minutos)} <em>min</em></strong></div><div class="metric-mini"><span>Minutos estimados ahorrados</span><strong>${fmt(r.minutos_ahorrados)} <em>min</em></strong></div><div class="metric-mini"><span>Municipios de la ruta</span><strong>${r.optima.ruta.length}</strong></div></div><div class="result-label">Secuencia recomendada</div><div class="route-pills">${r.optima.ruta.map((id,i)=>`${i?'<i>→</i>':''}<span>${safe(name(id))}</span>`).join('')}</div>`;
 renderMap('map-muestras',{network:true,highlight:r.optima.ruta,paths:[{seq:r.referencia.ruta,kind:'baseline'},{seq:r.optima.ruta,kind:'main'}],selected:$('traslado-origen').value});
 $('traslado-paths').innerHTML=`<div class="path-box"><div class="path-head"><span><i></i> Menor tiempo calculado</span><b>${fmt(r.optima.costo_minutos)} min</b></div><p>${r.optima.ruta.map(name).map(safe).join(' → ')}</p></div><div class="path-box orange"><div class="path-head"><span><i></i> Con consolidación</span><b>${fmt(r.referencia.costo_minutos)} min</b></div><p>${r.referencia.ruta.map(name).map(safe).join(' → ')}</p></div>`;
}

async function runAlertas(){try{
 const r=await api('operaciones/alerta',{origen:$('alerta-origen').value,saltos:$('alerta-saltos').value});
 state.results.alertas=r;if(state.screen==='alertas')renderAlertas();
 }catch(e){toast(e.message,true);$('alerta-summary').textContent=e.message}}
function renderAlertas(){const r=state.results.alertas;if(!r)return;
 $('alerta-summary').innerHTML=`<div class="result-label">COBERTURA OPERATIVA EN EL ESCENARIO</div><div class="result-hero"><div class="big">${fmt(r.total_zonas)}<span> / ${state.red.zonas.length}</span></div><small>municipios dentro del alcance de ${r.max_conexiones} conexiones<br>incluyendo el punto de origen</small></div><span class="status-good">${icon('check')} Plan de comunicación construido</span><div class="result-metrics"><div class="metric-mini"><span>Vecinos directos</span><strong>${(r.por_nivel['1']||[]).length}</strong></div><div class="metric-mini"><span>Cobertura de la red</span><strong>${fmt(r.total_zonas*100/state.red.zonas.length)} <em>%</em></strong></div></div><p class="result-note">Inicia en <b>${safe(name(r.origen))}</b>. La secuencia organiza contactos, no contagios, tiempos ni prioridades médicas.</p>`;
 renderMap('map-alertas',{network:true,selected:r.origen,levels:r.niveles,maxLevel:r.max_conexiones});
 $('alerta-levels').innerHTML=Object.entries(r.por_nivel).map(([n,ids])=>`<div class="level-card"><b>${Number(n)===0?'Punto de origen':`Nivel ${n} · ${ids.length} zonas`}</b><small>${ids.map(id=>safe(name(id))).join(', ')}</small></div>`).join('');
}

async function runEnlaces(){try{
 const [desde,hasta]=$('enlace-seleccion').value.split('-');
 const r=await api('operaciones/continuidad',{desde,hasta});state.results.enlaces=r;
 if(state.screen==='enlaces')renderEnlaces();
 }catch(e){toast(e.message,true);$('enlaces-summary').textContent=e.message}}
function renderEnlaces(){const r=state.results.enlaces;if(!r)return;
 const crit=r.enlace_critico;
 $('enlaces-summary').innerHTML=`<div class="result-label">ESTADO DEL ENLACE AL RETIRARLO DEL GRAFO</div><div class="result-hero"><div class="big ${crit?'danger':'neutral'}">${crit?'Crítico':'Alterno'}</div><small>${safe(name(r.desde))} ↔ ${safe(name(r.hasta))}<br>simulación de interrupción</small></div><span class="${crit?'status-bad':'status-good'}">${icon(crit?'shield':'check')} ${crit?'No existe camino alternativo':'La conexión puede restablecerse por otra ruta'}</span><div class="result-metrics"><div class="metric-mini"><span>Enlaces críticos del piloto</span><strong>${r.total_criticos}<em> / ${r.total_enlaces}</em></strong></div><div class="metric-mini"><span>Tiempo alternativo</span><strong>${crit?'—':fmt(r.minutos_respaldo)+' min'}</strong></div></div><p class="result-note">${crit?'Al quitar este enlace se pierde la conexión entre sus extremos dentro de la red modelada.':'Ruta de respaldo: '+r.ruta_respaldo.map(id=>name(id)).join(' → ')+'. Diferencia frente al tramo directo: '+fmt(r.minutos_extra)+' min.'}</p>`;
 renderMap('map-enlaces',{network:true,selected:r.desde,disabled:[r.desde,r.hasta],highlight:[r.desde,r.hasta],paths:crit?[]:[{seq:r.ruta_respaldo,kind:'main'}]});
 $('enlaces-criticos').innerHTML=`<span class="critical-badge">Enlaces críticos del escenario:</span>${r.enlaces_criticos.map(e=>`<span class="critical-badge">${safe(name(e.desde))} – ${safe(name(e.hasta))}</span>`).join('')}`;
}

async function runBrigadas(){try{const r=await api('operaciones/brigadas');state.results.brigadas=r;if(state.screen==='brigadas')renderBrigadas()}catch(e){toast(e.message,true)}}
function renderBrigadas(){const r=state.results.brigadas;if(!r)return;
 $('stats-brigadas').innerHTML=stat('Municipios asignados',r.zonas,'Cada municipio recibe exactamente un bloque','people')+stat('Bloques sugeridos',r.bloques_agrupados,'Grupos compatibles de la heurística','calendar','blue')+stat('Menos bloques a programar',r.reduccion_bloques_pct+'%','Frente a atender cada zona por separado','check','purple');
 renderMap('map-brigadas',{network:true,groups:r.colores});
 $('brigadas-groups').innerHTML=r.grupos.map((g,i)=>`<div class="brigada-block" style="--group:${groupColors[i%groupColors.length]}"><div><strong>Bloque ${String(i+1).padStart(2,'0')}</strong><small>${g.length} municipio${g.length===1?'':'s'}</small></div><p>${g.map(id=>safe(name(id))).join(' · ')}</p></div>`).join('')+`<span class="${r.sin_conflictos?'status-good':'status-bad'}">${icon(r.sin_conflictos?'check':'info')} ${r.sin_conflictos?'No se detectaron vecinos en el mismo bloque':'Atención: revisar conflictos'}</span>`;
}

async function runInsumos(){try{
 const selected=[...$('insumos-destinos').querySelectorAll('input:checked')].map(x=>x.value);
 if(!selected.length){toast('Selecciona al menos un municipio de destino',true);return;}
 const r=await api('operaciones/insumos',{origen:$('insumos-origen').value,destinos:selected.join(',')});state.results.insumos=r;
 if(state.screen==='insumos')renderInsumos();
 }catch(e){toast(e.message,true);$('insumos-summary').textContent=e.message}}
function renderInsumos(){const r=state.results.insumos;if(!r)return;
 const dif=r.minutos_diferencia;const saved=dif>=0;
 $('insumos-summary').innerHTML=`<div class="result-label">TIEMPO TOTAL ESTIMADO DEL CIRCUITO</div><div class="result-hero"><div class="big">${fmt(r.plan.costo_minutos)}<span>min</span></div><small>viaje de ida, visitas y<br>retorno al origen</small></div><span class="${saved?'status-good':'status-bad'}">${icon(saved?'check':'info')} ${saved?'Mejora frente al orden alfabético':'Sin mejora frente al orden alfabético'}</span><div class="result-metrics"><div class="metric-mini"><span>Referencia alfabética</span><strong>${fmt(r.referencia.costo_minutos)} <em>min</em></strong></div><div class="metric-mini"><span>${saved?'Diferencia favorable':'Minutos adicionales'}</span><strong>${fmt(Math.abs(dif))} <em>min</em></strong></div><div class="metric-mini"><span>Diferencia relativa</span><strong>${fmt(r.porcentaje_diferencia)} <em>%</em></strong></div><div class="metric-mini"><span>Destinos programados</span><strong>${r.plan.visitas.length>1?r.plan.visitas.length-2:0}</strong></div></div><p class="result-note">Ruta de referencia: mismos destinos ordenados por código (A–J). El método de vecino más cercano no garantiza el óptimo global.</p>`;
 const stops={};r.plan.visitas.forEach((id,i)=>{if(stops[id]===undefined)stops[id]=i});
 renderMap('map-insumos',{network:true,selected:r.plan.visitas[0],highlight:r.plan.visitas,stops,paths:[{seq:r.plan.recorrido_completo,kind:'main'}]});
 $('insumos-stops').innerHTML=r.plan.visitas.map((z,i)=>`<span class="stop-chip"><b>${i+1}</b>${safe(name(z))}${i===r.plan.visitas.length-1?' · regreso':''}</span>`).join('');
}

function syncEditor(){const z=zone($('edit-zona').value);if(!z)return;for(const key of ['confirmados','recuperados','fallecidos'])$('edit-'+key).value=z[key]}
function renderRegistros(){
 const changed=state.red.modificaciones||0;
 $('modificaciones').textContent=changed?`${changed} registro${changed===1?'':'s'} modificado${changed===1?'':'s'}`:'Sin modificaciones';
 $('registros-corte').textContent=`Evento seleccionado: ${state.enfermedad} · simulación académica`;
 $('registros-body').innerHTML=state.red.zonas.map(z=>`<tr><td><strong>${safe(z.nombre)}</strong></td><td>${fmt(z.confirmados)}</td><td>${fmt(z.recuperados)}</td><td>${fmt(z.fallecidos)}</td><td><strong>${fmt(z.activos)}</strong></td><td>${badge(z.carga)}</td><td><button class="tiny-edit" data-edit="${z.id}">Editar</button></td></tr>`).join('');
 syncEditor();
}
function download(file,mime,body){const blob=new Blob([body],{type:mime});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download=file;document.body.appendChild(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(u),1200)}
function exportData(type){
 const r=state.red;if(!r)return;
 const stamp=state.enfermedad.toLowerCase().replace(/[^a-z0-9]/g,'-');
 if(type==='json')return download(`epired_${stamp}_simulado.json`,'application/json;charset=utf-8',JSON.stringify(r,null,2));
 const rows=[['enfermedad','codigo','municipio','confirmados','recuperados','fallecidos','activos','carga','latitud','longitud'],...r.zonas.map(z=>[state.enfermedad,z.id,z.nombre,z.confirmados,z.recuperados,z.fallecidos,z.activos,z.carga,z.lat,z.lon])];
 const csv='\ufeff'+rows.map(a=>a.map(v=>'"'+String(v).replace(/"/g,'""')+'"').join(';')).join('\r\n');
 download(`epired_${stamp}_simulado.csv`,'text/csv;charset=utf-8',csv);
}
async function saveReport(){try{
 const values=['confirmados','recuperados','fallecidos'].map(k=>Number($('edit-'+k).value));
 if(values.some(x=>!Number.isInteger(x)||x<0)){toast('Usa enteros no negativos',true);return}
 const r=await post('registros/actualizar',{enfermedad:state.enfermedad,zona:$('edit-zona').value,confirmados:values[0],recuperados:values[1],fallecidos:values[2]});
 await reloadData();toast(r.mensaje);
 }catch(e){toast(e.message,true)}}
async function resetReports(){if(!confirm('¿Restaurar todos los reportes agregados del escenario de demostración?'))return;
 try{const r=await post('registros/restablecer',{});await reloadData();toast(r.mensaje)}catch(e){toast(e.message,true)}}

function bind(){
 document.querySelectorAll('[data-screen]').forEach(e=>e.addEventListener('click',()=>navigate(e.dataset.screen)));
 document.querySelectorAll('[data-screen-link]').forEach(e=>e.addEventListener('click',ev=>{ev.preventDefault();navigate(e.dataset.screenLink)}));
 $('menu-button').addEventListener('click',()=>$('sidebar').classList.toggle('open'));
 $('global-enfermedad').addEventListener('change',async e=>{state.enfermedad=e.target.value;try{await reloadData()}catch(err){toast(err.message,true)}});
 document.querySelectorAll('#layer-chooser [data-map-layer]').forEach(e=>e.addEventListener('click',()=>{state.mapLayer=e.dataset.mapLayer;renderVigilancia()}));
 $('form-muestras').addEventListener('submit',e=>{e.preventDefault();runMuestras()});
 $('form-alertas').addEventListener('submit',e=>{e.preventDefault();runAlertas()});
 $('form-enlaces').addEventListener('submit',e=>{e.preventDefault();runEnlaces()});
 $('form-insumos').addEventListener('submit',e=>{e.preventDefault();runInsumos()});
 $('btn-brigadas').addEventListener('click',runBrigadas);
 $('form-edit').addEventListener('submit',e=>{e.preventDefault();saveReport()});
 $('edit-zona').addEventListener('change',syncEditor);
 $('btn-restablecer').addEventListener('click',resetReports);
 $('btn-json').addEventListener('click',()=>exportData('json'));
 $('btn-csv').addEventListener('click',()=>exportData('csv'));
 $('btn-download-map-data').addEventListener('click',()=>exportData('csv'));
 $('btn-all-dest').addEventListener('click',()=>{document.querySelectorAll('#insumos-destinos input').forEach(e=>e.checked=true);updateDestCounter()});
 $('btn-none-dest').addEventListener('click',()=>{document.querySelectorAll('#insumos-destinos input').forEach(e=>e.checked=false);updateDestCounter()});
 $('insumos-destinos').addEventListener('change',updateDestCounter);
 document.addEventListener('click',e=>{
  const target=e.target.closest('[data-mapzoom]');
  if(target){const id=target.dataset.target;const area=$(id);const baseZoom=area.clientWidth<450?9.55:area.clientHeight<355?10.05:area.clientHeight<430?10.2:10.4;const cur=state.maps[id]?.zoom??baseZoom;const zoom=target.dataset.mapzoom==='reset'?baseZoom:Math.max(9.2,Math.min(12.2,cur+(target.dataset.mapzoom==='plus'?.6:-.6)));state.maps[id]={zoom};renderCurrent();return}
  const node=e.target.closest('[data-point]');if(node){state.selected=node.dataset.point;if(state.screen==='vigilancia'){renderVigilancia()}else if(state.screen==='inicio')renderHome();else toast(`${name(state.selected)}: ${fmt(zone(state.selected)?.activos)} casos activos (simulados)`);return}
  const row=e.target.closest('[data-select]');if(row){state.selected=row.dataset.select;navigate('vigilancia');return}
  const edit=e.target.closest('[data-edit]');if(edit){$('edit-zona').value=edit.dataset.edit;syncEditor();$('edit-confirmados').focus();return}
 });
 document.addEventListener('keydown',e=>{if(e.target?.matches('.town-node')&&(e.key==='Enter'||e.key===' ')){e.preventDefault();e.target.dispatchEvent(new MouseEvent('click',{bubbles:true}))}});
 document.addEventListener('error',e=>{if(e.target.classList?.contains('map-tile'))e.target.style.display='none'},true);
 let resizeTimeout;window.addEventListener('resize',()=>{clearTimeout(resizeTimeout);resizeTimeout=setTimeout(renderCurrent,150)});
}
async function start(){bind();try{await reloadData()}catch(e){toast(e.message,true);$('stats-home').textContent='No se pudo conectar con el motor de EpiRed. Ejecuta python server.py y recarga.'}}
start();

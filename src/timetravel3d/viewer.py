"""Offline interactive point-cloud viewer for a presentation demo."""
import json
from pathlib import Path

import numpy as np


def save_viewer(path, data, mask, title='TimeTravel3D'):
    points = data['points']
    center = np.median(points, axis=0)
    scale = max(float(np.percentile(np.linalg.norm(points - center, axis=1), 95)), 1e-9)
    normalized = (points - center) / scale
    packed = np.column_stack([normalized, data['colors'], mask.astype(int)]).round(5).tolist()
    template = '''<!doctype html><html><head><meta charset="utf-8"><title>TimeTravel3D demo</title>
<style>*{box-sizing:border-box}body{margin:0;background:#101d2b;color:#edf5fa;font:18px Segoe UI,sans-serif}header{padding:24px 32px}h1{font-size:30px;margin:0 0 10px}button{font:inherit;padding:9px 16px;border:1px solid #8496a8;background:transparent;color:white;cursor:pointer;margin-right:12px}button.active{background:#087e8b;border-color:#23bcc7}canvas{width:100%;height:72vh;display:block}p{color:#bdcbd6}#status{position:absolute;bottom:28px;left:32px} </style></head>
<body><header><h1>TITLE</h1><p>Drag to rotate. Scroll to zoom. Both modes use the same cameras and triangulated points.</p><button id="baseline" class="active">All baseline points</button><button id="proposed">Coverage-preserving confidence</button><button id="reset">Reset view</button></header><canvas></canvas><div id="status"></div>
<script>const points=PACKED;let mode=0,yaw=.2,pitch=-.15,zoom=1,drag=false,previous=null;const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d');function render(){canvas.width=canvas.clientWidth*devicePixelRatio;canvas.height=canvas.clientHeight*devicePixelRatio;const w=canvas.width,h=canvas.height;ctx.fillStyle='#101d2b';ctx.fillRect(0,0,w,h);let shown=0;const cy=Math.cos(yaw),sy=Math.sin(yaw),cp=Math.cos(pitch),sp=Math.sin(pitch);let projected=[];for(const p of points){if(mode&&!p[6])continue;const x=cy*p[0]+sy*p[2],z=-sy*p[0]+cy*p[2],y=cp*p[1]-sp*z,zz=sp*p[1]+cp*z;const scale=Math.min(w,h)*.8*zoom/Math.max(1,3+zz);projected.push([w/2+x*scale,h/2+y*scale,zz,p]);shown++}projected.sort((a,b)=>b[2]-a[2]);for(const [x,y,z,p] of projected){ctx.fillStyle=`rgb(${p[3]},${p[4]},${p[5]})`;ctx.fillRect(x,y,2*devicePixelRatio,2*devicePixelRatio)}document.querySelector('#status').textContent=`${mode?'Proposed':'Baseline'}: ${shown.toLocaleString()} / ${points.length.toLocaleString()} points. Monocular reconstruction uses arbitrary display scale.`}
document.querySelector('#baseline').onclick=()=>{mode=0;toggle()};document.querySelector('#proposed').onclick=()=>{mode=1;toggle()};function toggle(){document.querySelector('#baseline').classList.toggle('active',!mode);document.querySelector('#proposed').classList.toggle('active',!!mode);render()}document.querySelector('#reset').onclick=()=>{yaw=.2;pitch=-.15;zoom=1;render()};canvas.onpointerdown=e=>{drag=true;previous=[e.clientX,e.clientY];canvas.setPointerCapture(e.pointerId)};canvas.onpointerup=()=>drag=false;canvas.onpointermove=e=>{if(drag){yaw+=(e.clientX-previous[0])*.008;pitch+=(e.clientY-previous[1])*.008;previous=[e.clientX,e.clientY];render()}};canvas.onwheel=e=>{e.preventDefault();zoom=Math.min(5,Math.max(.2,zoom*Math.exp(-e.deltaY*.001)));render()};window.onresize=render;render();</script></body></html>'''
    from html import escape
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(template.replace('TITLE', escape(title)).replace('PACKED', json.dumps(packed, separators=(',', ':'))), encoding='utf-8')

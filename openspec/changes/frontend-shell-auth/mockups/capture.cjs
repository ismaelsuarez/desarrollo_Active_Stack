const fs = require('fs');
const path = require('path');
const { pathToFileURL } = require('url');
const http = require('http');
const names = ['acceso','registro','enlaces','cuenta','roles'];
const port = 19246;
const output = path.join(__dirname,'previews');
fs.mkdirSync(output,{recursive:true});
async function run() {
 const target = await fetch(`http://127.0.0.1:${port}/json/new?about:blank`, {method:'PUT'}).then(r=>r.json());
 const socket = new WebSocket(target.webSocketDebuggerUrl);
 await new Promise((ok,fail)=>{socket.onopen=ok;socket.onerror=fail});
 let seq=0; const pending=new Map();
 socket.onmessage = e=>{const data=JSON.parse(e.data);if(data.id&&pending.has(data.id)){const p=pending.get(data.id);pending.delete(data.id);data.error?p.reject(data.error):p.resolve(data.result)}};
 const call=(method,params={})=>new Promise((resolve,reject)=>{const id=++seq;pending.set(id,{resolve,reject});socket.send(JSON.stringify({id,method,params}))});
 await call('Page.enable');
 for (const [viewport,width,height] of [['desktop',1440,900],['mobile',390,844]]) {
  await call('Emulation.setDeviceMetricsOverride',{width,height,deviceScaleFactor:1,mobile:false});
  for(const name of names){
   await call('Page.navigate',{url:pathToFileURL(path.join(__dirname,name+'.html')).href});
   await new Promise(r=>setTimeout(r,700));
   const metrics=await call('Page.getLayoutMetrics');
   const {width:w,height:h}=metrics.cssContentSize;
   const shot=await call('Page.captureScreenshot',{format:'png',captureBeyondViewport:true,clip:{x:0,y:0,width:Math.ceil(w),height:Math.ceil(h),scale:1}});
   fs.writeFileSync(path.join(output,`${name}-${viewport}.png`),Buffer.from(shot.data,'base64'));
   console.log(name,viewport,Math.ceil(w),Math.ceil(h));
  }
 }
 socket.close();
}
run().catch(e=>{console.error(e);process.exitCode=1});

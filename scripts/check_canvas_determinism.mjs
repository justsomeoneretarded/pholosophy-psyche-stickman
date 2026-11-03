import fs from 'node:fs';
import path from 'node:path';
import {pathToFileURL} from 'node:url';
import {createHash} from 'node:crypto';
import {chromium} from 'playwright';
const film=JSON.parse(fs.readFileSync(process.argv[2],'utf8'));
let time=2,total=0;
for(const shot of film.shots){if(shot.camera?.frame==='phone'){time=total+2;break;}total+=shot.dur;}
const browser=await chromium.launch({args:['--disable-gpu-vsync','--force-device-scale-factor=1']});
try{
 const page=await browser.newPage({viewport:{width:960,height:540}});
 await page.goto(pathToFileURL(path.resolve('engine/index.html')).href);
 await page.evaluate(()=>loadFilmFonts());
 const result=await page.evaluate(([film,time])=>{
  setup(film,960);
  drawFrame(time);const first=document.getElementById('film').toDataURL('image/png');
  drawFrame(time);const second=document.getElementById('film').toDataURL('image/png');
  return {first,second,fonts:[...document.fonts].map(face=>({family:face.family,status:face.status}))};
 },[film,time]);
 if(process.argv[3]){
  const folder=path.dirname(process.argv[3]);fs.mkdirSync(folder,{recursive:true});
  for(const [name,value] of [['first',result.first],['second',result.second]]){
   fs.writeFileSync(path.join(folder,name+'.png.b64'),value.split(',')[1]);
  }
 }
 if(result.first!==result.second)throw new Error('Repeated rendering of the same timeline position changed pixels');
 const report={passed:true,time,sha256:createHash('sha256').update(result.first).digest('hex'),fonts:result.fonts};
 if(process.argv[3])fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2));
 console.log('All film fonts loaded before first capture; repeated frame pixels match.');
}finally{await browser.close();}

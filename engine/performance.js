// Articulated performances for writing, reading, conversation and chair transitions.
'use strict';
const PAPER_PATHS = {
  seedling: [[0,14],[0,0],[-14,-3],[-11,6],[0,5],[14,-2],[10,7],[0,3]],
  writing: [[-32,1],[-24,5],[-18,0],[-12,5],[-6,0],[0,5],[6,0],[12,5],[18,1],[26,5]]
};
function artworkPoint(kind,progress) {
  const points=PAPER_PATHS[kind]||PAPER_PATHS.writing;
  const q=clamp(progress,0,1)*(points.length-1),i=Math.min(points.length-2,Math.floor(q)),k=q-i;
  return [lerp(points[i][0],points[i+1][0],k),lerp(points[i][1],points[i+1][1],k)];
}
function drawWritingPad(ctx,P) {
  ctx.save();ctx.translate(P.paperX,P.paperY);
  ctx.fillStyle='#efe9db';ctx.strokeStyle='#756859';ctx.lineWidth=2;
  ctx.beginPath();ctx.moveTo(-58,-6);ctx.lineTo(58,-6);ctx.lineTo(50,18);ctx.lineTo(-50,18);ctx.closePath();ctx.fill();ctx.stroke();
  ctx.strokeStyle=P.artwork==='seedling'?'#3e8d55':'#414651';ctx.lineWidth=2.2;ctx.lineCap='round';
  ctx.beginPath();
  for(let i=0;i<=80;i++){
    const p=artworkPoint(P.artwork,P.drawProgress*i/80);
    if(i===0)ctx.moveTo(...p);else ctx.lineTo(...p);
  }
  ctx.stroke();ctx.restore();
}
function drawOpenBook(ctx,P,hands) {
  const x=(hands[0][0]+hands[1][0])/2,y=(hands[0][1]+hands[1][1])/2-6;
  ctx.save();ctx.translate(x,y);ctx.fillStyle='#efe7d4';ctx.strokeStyle='#62806a';ctx.lineWidth=3;
  ctx.beginPath();ctx.moveTo(-38,-22);ctx.lineTo(-3,-18);ctx.lineTo(0,-14);ctx.lineTo(3,-18);ctx.lineTo(38,-22);ctx.lineTo(35,22);ctx.lineTo(0,17);ctx.lineTo(-35,22);ctx.closePath();ctx.fill();ctx.stroke();
  ctx.strokeStyle='#b4ac99';ctx.lineWidth=1.5;
  for(let y0=-9;y0<=8;y0+=7){ctx.beginPath();ctx.moveTo(-30,y0);ctx.lineTo(-8,y0+2);ctx.moveTo(8,y0+2);ctx.lineTo(30,y0);ctx.stroke();}
  if(P.artwork==='seedling'){ctx.strokeStyle='#3e8d55';ctx.lineWidth=2.2;ctx.beginPath();ctx.moveTo(18,13);ctx.lineTo(18,-8);ctx.moveTo(18,1);ctx.quadraticCurveTo(2,-10,9,-7);ctx.moveTo(18,-2);ctx.quadraticCurveTo(34,-12,27,-5);ctx.stroke();}
  ctx.restore();
}
Object.assign(POSES,{
  write(P,a,u,d,w) {
    POSES.sit(P,a,u,d,w);
    P.paperX=(P.sideSit||0)*48;P.paperY=w.desk?-w.desk-20:P.pelvis[1]-18;
    P.artwork=a.artwork==='seedling'?'seedling':'writing';
    P.drawProgress=clamp((u-.55)/Math.max(1,Math.min(3,d-.8)),0,1);
    const point=artworkPoint(P.artwork,P.drawProgress),k=easeOut(u/.55);
    const target=[P.paperX+point[0]+Math.sin(.6)*6.5,P.paperY+point[1]-Math.cos(.6)*6.5];
    P.hands[1]=[lerp(P.hands[1][0],target[0],k),lerp(P.hands[1][1],target[1],k)];
    P.hands[0]=[lerp(P.hands[0][0],P.paperX-44,k),lerp(P.hands[0][1],P.paperY+10,k)];
    P.writingPad=true;P.hold='pencil';P.look=[(P.sideSit||0)*.4,4];P.headDy=4;
  },
  read(P,a,u,d,w) {
    if(a.seated)POSES.sit(P,a,u,d,w);else POSES.stand(P,a,u,d,w);
    const x=(P.sideSit||0)*35,y=P.pelvis[1]-80;
    P.hands=[[x-28,y],[x+28,y]];P.hold='book';P.bookOpen=true;
    P.look=[(P.sideSit||0)*.4,4];P.headTilt=.025*Math.sin(u*.9);
    P.artwork=a.artwork;
  },
  show(P,a,u,d,w) {
    POSES.read(P,a,u,d,w);
    const dir=w.targetDx===undefined?(a.facing||1):(w.targetDx>=0?1:-1),k=easeOut(u/.65);
    const x=dir*lerp(25,60,k),y=P.pelvis[1]-lerp(80,110,k);
    P.hands=[[x-28,y],[x+28,y]];P.faceDx=dir*.7;P.look=[dir*.5,0];
  },
  think(P,a,u,d,w) {
    if(a.seated)POSES.sit(P,a,u,d,w);else POSES.stand(P,a,u,d,w);
    const k=easeOut(u/.5),target=[36,P.pelvis[1]-112+Math.sin(u*1.8)*1.5];
    P.hands[1]=[lerp(P.hands[1][0],target[0],k),lerp(P.hands[1][1],target[1],k)];
    P.look=[.2,-2];P.headTilt=.04+Math.sin(u*.8)*.025;
  },
  talk(P,a,u,d,w) {
    if(a.seated)POSES.sit(P,a,u,d,w);else POSES.stand(P,a,u,d,w);
    const dir=a.facing||1,k=easeOut(u/.4),gesture=.5+.5*Math.sin(u*3.2);
    const target=[dir*(62+gesture*16),P.pelvis[1]-75-gesture*30];
    const hand=dir>0?1:0;
    P.hands[hand]=[lerp(P.hands[hand][0],target[0],k),lerp(P.hands[hand][1],target[1],k)];
    P.faceDx=dir*.6;P.speaking=true;P.headTilt=Math.sin(u*2.2)*.025;
  },
  standup(P,a,u,d,w) {
    const k=easeInOut(clamp(u/1.6,0,1)),seat=w.seat||58,dir=a.facing||1;
    POSES.stand(P,a,u,d,w);
    P.profile=dir;P.faceDx=dir*.7;P.pelvis=[0,lerp(-seat-10,RIG.pelvisY,k)];
    P.feet=[[lerp(dir*50,-24,k),0],[lerp(dir*62,24,k),0]];
    P.lean=dir*.13*Math.sin(Math.PI*k);
    P.hands=[[lerp(dir*30-10,-53,k),lerp(-seat-16,-106,k)],[lerp(dir*44,53,k),lerp(-seat-18,-106,k)]];
  },
  sitdown(P,a,u,d,w) { POSES.standup(P,a,Math.max(0,1.6-u),d,w); }
});
function allocateSeatActors(shot,set) {
  const actors=(shot.actors||[]).map(a=>({...a}));
  if(!set.seatAnchors?.length)return actors;
  const available=[...set.seatAnchors];
  const seated=actors.filter(a=>['sit','slump','type','write','standup','sitdown'].includes(a.pose)||a.seated===true).sort((a,b)=>(a.x??50)-(b.x??50));
  for(const actor of seated){
    if(!available.length){actor._fallback_seat=true;continue;}
    const x=actor.x??50;let best=0;
    for(let i=1;i<available.length;i++)if(Math.abs(available[i]-x)<Math.abs(available[best]-x))best=i;
    actor._seat_anchor=available.splice(best,1)[0];
  }
  return actors;
}

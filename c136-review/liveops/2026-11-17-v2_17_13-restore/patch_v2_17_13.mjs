import fs from 'node:fs';
import path from 'node:path';

const mapsDir = path.resolve(process.argv[2] || '../c116/maps');
const targetJs = path.resolve(process.argv[3] || '../c116/live_game_js.js');
const outJs = path.resolve(process.argv[4] || 'live_game_js_1774.js');

const b64Maps = [];
for (let eT = 0; eT < 25; eT++) {
  const buf = fs.readFileSync(path.join(mapsDir, `${eT}-1.bin`));
  b64Maps.push(buf.toString('base64'));
}

const liveOrig = fs.readFileSync(targetJs, 'utf8');

const oldVer = 'this.dw=2;this.dx=1773;this.dy=0;var dz=2;var e0=17;var e1=9;this.rVersion=26;';
const newVer = 'this.dw=2;this.dx=1774;this.dy=0;var dz=2;var e0=17;var e1=13;this.rVersion=26;';
if (!liveOrig.includes(oldVer)) throw new Error('oldVer not found');

const oldDh = 'function dH(){this.aOj=25;this.aOk=13;';
const newDh = 'function dH(){this.aOj=37;this.aOk=25;';
if (!liveOrig.includes(oldDh)) throw new Error('oldDh not found');

const oldWh = 'L(168),L(169),"Mare Nostrum"];';
const newWh = 'L(168),L(169),"Mare Nostrum","Denmark","Iberia","Japan","India","Black Sea","Italy","Iceland","Anatolia","Falklands","Antarctica","Hong Kong","Singapore"];';
if (!liveOrig.includes(oldWh)) throw new Error('oldWh not found');

const oldZ24 = 'this.zX[24]={zy:a5w,zz:aQ3,aP6:w4,a9u:"[OG] Neutronian"};';
const newZ24 =
  'var aSK=[210,210,210];var aSL=[12,12,76];var aSM=[240,120,1024,45,19,30,70,8,20,3,9];' +
  'this.zX[24]={zy:a5w,zz:aQ3,aP6:w4,a9u:"[OG] Neutronian"};' +
  'this.zX[25]={zy:aPx,zz:aPy,aP6:aPz};' +
  'this.zX[26]={zy:aPv,zz:cos,aP6:aPw};' +
  'this.zX[27]={zy:aQ0,zz:aQ1,aP6:aQ2};' +
  'this.zX[28]={zy:aPv,zz:cos,aP6:aPw};' +
  'this.zX[29]={zy:aQ0,zz:aQ1,aP6:aQ2};' +
  'this.zX[30]={zy:aQ0,zz:aQ1,aP6:aQ2};' +
  'this.zX[31]={zy:aPx,zz:aPy,aP6:aPz};' +
  'this.zX[32]={zy:aPv,zz:cos,aP6:aPw};' +
  'this.zX[33]={zy:aPx,zz:aPy,aP6:aPz};' +
  'this.zX[34]={zy:aSK,zz:aSL,aP6:aSM};' +
  'this.zX[35]={zy:aPv,zz:cos,aP6:aPw};' +
  'this.zX[36]={zy:aPv,zz:cos,aP6:aPw};';
if (!liveOrig.includes(oldZ24)) throw new Error('oldZ24 not found');

const oldApu = 'this.aPu[11]=23;this.aPu[12]=24}}';
const newApu = 'this.aPu[11]=23;this.aPu[12]=24;for(aC=13;aC<bV.aOk;aC++){this.aPu[aC]=12+aC}}}';
if (!liveOrig.includes(oldApu)) throw new Error('oldApu not found');

const startOt = liveOrig.indexOf('function aOt(){');
const endOt = liveOrig.indexOf('function aOm(){');
if (startOt < 0 || endOt < startOt) throw new Error('aOt bounds not found: ' + startOt + ' .. ' + endOt);

const newAot = `var __MAP_B64_1774=${JSON.stringify(b64Maps)};function __decMapBin1774(aJQ){if(!aJQ||aJQ.length<11||aJQ[0]!==2)return null;var j=(aJQ[1]<<8)|aJQ[2],k=(aJQ[3]<<8)|aJQ[4],hD=aJQ[5];if(j<1||k<1||hD<1||hD>2)return null;var aUO=j*(k+1),aUN=new Uint8Array(aUO+(j+1)*k),aUK=new Uint16Array(27).fill(1024),aUL=new Uint16Array(27).fill(1024),aU8=new Uint16Array(2).fill(1024),aUA=new Uint16Array(64).fill(1024),dx=[1,0,-1,0],dy=[0,1,0,-1],fr=0,ft=0,fn=0,history=0,pos=7,aUT=4294967295,aUU=0;function rd(){return pos<aJQ.length?aJQ[pos++]:0}for(var _i=0;_i<4;_i++)aUU=aUU*256+rd();function rBit(pr,idx){var hI=pr[idx],aUY=(aUT>>>11)*hI,p3;if(aUU<aUY){aUT=aUY;pr[idx]=hI+(2048-hI>>5);p3=0}else{aUU-=aUY;aUT-=aUY;pr[idx]=hI-(hI>>5);p3=1}while(aUT<16777216){aUT*=256;aUU=aUU*256+rd()}return p3}function rDir(n){var gC=0;for(var aC=0;aC<n;aC++){aUT=Math.floor(aUT/2);var p3=0;if(aUU>=aUT){aUU-=aUT;p3=1}gC=gC*2+p3;while(aUT<16777216){aUT*=256;aUU=aUU*256+rd()}}return gC}function rGol(pr,p4){var hJ=0;while(rBit(pr,p4+hJ)){if(++hJ>30)return-1}return Math.pow(2,hJ)+rDir(hJ)-1}function eIdx(x,y,d){if(d===0)return x<j&&y>0&&y<k?y*j+x:-1;if(d===2)return x>0&&y>0&&y<k?y*j+x-1:-1;if(d===1)return y<k&&x>0&&x<j?aUO+y*(j+1)+x:-1;return y>0&&x>0&&x<j?aUO+(y-1)*(j+1)+x:-1}function canG(d){var c=eIdx(fr,ft,d);return c>=0&&aUN[c]!==2}function isB(x,y){return x===0||y===0||x===j||y===k}function tDir(el){return el===0?fn:fn+(el===1?3:1)&3}function stp(d){aUN[eIdx(fr,ft,d)]=2;fr+=dx[d];ft+=dy[d];fn=d}function trc(sx,sy,sd,ex,ey){fr=sx;ft=sy;if(!canG(sd))return false;history=0;stp(sd);while(!(fr===ex&&ft===ey||isB(fr,ft))){var iq=history,fOk=canG(fn),lOk=canG(tDir(1)),rOk=canG(tDir(2)),el;if(fOk&&!(lOk||rOk))el=0;else if(fOk&&rBit(aUK,iq))el=0;else if(lOk&&rOk)el=rBit(aUL,iq)?1:2;else if(lOk||rOk)el=lOk?1:2;else return false;history=(history*3+el)%27;stp(tDir(el))}return true}var pA=rDir(1),gC=-1;while(rBit(aU8,0)){var g3=rGol(aUA,0);if(g3<0)return null;gC+=g3+1;var bx0=gC%(j+1),by0=Math.floor(gC/(j+1));if(by0>k||!isB(bx0,by0))return null;var bd=by0===0?1:by0===k?3:bx0===0?0:2;if(eIdx(bx0,by0,bd)<0||!trc(bx0,by0,bd,-1,-1))return null}gC=-1;while(rBit(aU8,1)){var g4=rGol(aUA,32);if(g4<0)return null;gC+=g4+1;var ix0=gC%(j+1),iy0=Math.floor(gC/(j+1));if(iy0>=k||ix0===0||ix0>=j||iy0===0)return null;if(!trc(ix0,iy0,0,ix0,iy0))return null}var a2I=new Uint8Array(j*k),eu=pA;for(var y=0;y<k;y++){var hJ2=y*j;if(y>0)eu=a2I[hJ2-j]^(aUN[hJ2]>>1);a2I[hJ2]=eu;var vB=aUO+y*(j+1);for(var x=1;x<j;x++){eu^=aUN[vB+x]>>1;a2I[hJ2+x]=eu}}return{j:j,k:k,a2I:a2I}}function aOt(){var fF=bV.fF,eT=-1,h=bV.wG.aPu;for(var i=0;i<h.length;i++){if(h[i]===fF){eT=i;break}}if(eT<0||!__MAP_B64_1774[eT])return;var binStr=atob(__MAP_B64_1774[eT]),bin=new Uint8Array(binStr.length);for(var u=0;u<binStr.length;u++)bin[u]=binStr.charCodeAt(u);var q5=__decMapBin1774(bin);if(!q5)return;var zX=bV.wG.zX[fF];zX.j=bV.fk=q5.j;zX.k=bV.fl=q5.k;bV.zg=document.createElement("canvas");bV.zg.width=bV.fk;bV.zg.height=bV.fl;bV.zc=bV.zg.getContext("2d",{alpha:false});bV.zd=bV.zh=null;bV.zd=bV.zc.getImageData(0,0,bV.fk,bV.fl);bV.zh=bV.zd.data;var zj=bV.zh,src=q5.a2I,zy=zX.zy,zz=zX.zz,r1=zy[0],g1=zy[1],b1c=zy[2],r0=zz[0],g0=zz[1],b0c=zz[2];for(var p=0,n=src.length;p<n;p++){var o=p<<2;if(src[p]){zj[o]=r1;zj[o+1]=g1;zj[o+2]=b1c}else{zj[o]=r0;zj[o+1]=g0;zj[o+2]=b0c}zj[o+3]=255}bV.zc.putImageData(bV.zd,0,0);bV.ze=true;bV.zf.dk();bi.ds=true}`;

let patched = liveOrig.slice(0, startOt) + newAot + liveOrig.slice(endOt);
patched = patched
  .replace(oldVer, newVer)
  .replace(oldDh, newDh)
  .replace(oldWh, newWh)
  .replace(oldZ24, newZ24)
  .replace(oldApu, newApu);

fs.writeFileSync(outJs, patched, 'utf8');
console.log('Generated', outJs, 'size=', patched.length, '(orig=', liveOrig.length, ')');

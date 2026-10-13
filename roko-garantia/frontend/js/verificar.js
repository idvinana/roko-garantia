// Verificador de autenticidade (Backend de Verificação) — digitar ID, escanear QR, ler QR de uma foto
(function(){var RK=window.RK,$=RK.$,esc=RK.esc;
var COL={ativa:"var(--ok)",pendente:"var(--gold)",expirada:"var(--mu)",revogada:"var(--red)",nao_encontrado:"var(--red)"};
var TIT={ativa:"✓ AUTÊNTICA · GARANTIA ATIVA",pendente:"✓ AUTÊNTICA · AGUARDANDO ATIVAÇÃO",expirada:"✓ AUTÊNTICA · GARANTIA EXPIRADA",revogada:"✕ GARANTIA CANCELADA",nao_encontrado:"✕ CÓDIGO NÃO ENCONTRADO"};
function verify(raw,origem){var id=String(raw||"").trim().toUpperCase();
 if(!/^RKO-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(id)){$("verr").textContent="Formato inválido. Ex.: RKO-AB12-CD34";$("vres").innerHTML="";return}
 $("verr").textContent="";$("vin").value=id;
 RK.pubB("/api/verificar/"+encodeURIComponent(id)+"?origem="+encodeURIComponent(origem||"manual")).then(function(j){
  $("vres").innerHTML='<div class="card"><div class="st" style="color:'+COL[j.estado]+'">'+TIT[j.estado]+'</div><p class="hint center">'+esc(j.mensagem)+'</p>'+(j.autentica?RK.card(j):'')+'</div>'}).catch(function(e){$("verr").textContent=e.message})}
RK.verify=verify;
RK.goVerify=function(vid,orig){RK.go("sec-ver");verify(vid,orig||"manual")};
// ---- leitor de QR ----
var camStream=null,camTimer=null,qrReady=null;
function loadScript(u){return new Promise(function(ok,no){var s=document.createElement("script");s.src=u;s.onload=ok;s.onerror=no;document.head.appendChild(s)})}
function ensureJsQR(){if(typeof jsQR==="function")return Promise.resolve(true);
 if(!qrReady)qrReady=loadScript("https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js").catch(function(){return loadScript("https://cdnjs.cloudflare.com/ajax/libs/jsqr/1.4.0/jsQR.min.js")}).then(function(){return typeof jsQR==="function"}).catch(function(){qrReady=null;return false});
 return qrReady}
function idFrom(t){var m=String(t||"").toUpperCase().match(/RKO-[A-Z0-9]{4}-[A-Z0-9]{4}/);return m?m[0]:null}
async function decodeCv(cv){
 try{if("BarcodeDetector" in window){var bd=new BarcodeDetector({formats:["qr_code"]});var r=await bd.detect(cv);if(r.length)return r[0].rawValue}}catch(e){}
 if(await ensureJsQR()){var im=cv.getContext("2d",{willReadFrequently:true}).getImageData(0,0,cv.width,cv.height);var q=jsQR(im.data,im.width,im.height,{inversionAttempts:"attemptBoth"});if(q)return q.data}
 return null}
function scanErr(m){$("verr").textContent=m;$("vres").innerHTML=""}
function handleQR(t,orig){if(!t){scanErr("Não encontramos um QR Code na imagem. Aproxime, deixe o QR centralizado e bem iluminado.");return}
 var id=idFrom(t);if(!id){scanErr("Este QR Code não é de um certificado ROKO IKIGAI.");return}verify(id,orig||"qr")}
var scanners=[];
// leitor de QR reutilizável: o=ids dos elementos, onId(id,origem) recebe o ID lido, onErr(msg) mostra erros
function makeScanner(o,onId,onErr){var camStream=null,camTimer=null;
 function stop(){if(camTimer){clearInterval(camTimer);camTimer=null}if(camStream){camStream.getTracks().forEach(function(t){t.stop()});camStream=null}$(o.wrap).classList.add("hide")}
 function handle(t,orig){if(!t){onErr("Não encontramos um QR Code na imagem. Aproxime, deixe o QR centralizado e bem iluminado.");return}
  var id=idFrom(t);if(!id){onErr("Este QR Code não é de um certificado ROKO IKIGAI.");return}onId(id,orig)}
 async function decodeImage(img){var W=img.naturalWidth||img.width,H=img.naturalHeight||img.height,big=Math.max(W,H);
  for(var mx of [2000,1200,800]){var sc=Math.min(1,mx/big),cv=document.createElement("canvas");cv.width=Math.max(1,Math.round(W*sc));cv.height=Math.max(1,Math.round(H*sc));
   cv.getContext("2d",{willReadFrequently:true}).drawImage(img,0,0,cv.width,cv.height);var t=await decodeCv(cv);if(t)return t;if(sc===1&&mx>=big)break}
  return null}
 function readFile(inp){var f=inp.files&&inp.files[0];if(!f)return;stop();onErr("Lendo imagem…");var img=new Image(),u=URL.createObjectURL(f);
  img.onload=async function(){try{var t=await decodeImage(img);URL.revokeObjectURL(u);onErr("");handle(t,"foto")}catch(e){onErr("Não foi possível ler a imagem.")}};
  img.onerror=function(){onErr("Não foi possível abrir a imagem. Tente uma foto em JPG ou PNG.")};img.src=u;inp.value=""}
 function openCam(){var md=navigator.mediaDevices;if(!md||!md.getUserMedia||window.isSecureContext===false)return Promise.reject(new Error("indisponivel"));
  return md.getUserMedia({video:{facingMode:{ideal:"environment"},width:{ideal:1280},height:{ideal:720}},audio:false}).catch(function(){return md.getUserMedia({video:true,audio:false})})}
 function init(){
  $(o.stop).onclick=stop;$(o.img).onclick=function(){$(o.file).click()};
  $(o.file).onchange=function(){readFile(this)};$(o.snap).onchange=function(){readFile(this)};
  $(o.snapbtn).onclick=function(){onErr("Abrindo a câmera do celular…");$(o.snap).click()};
  $(o.cam).onclick=function(){onErr("");$(o.snapbtn).classList.add("hide");
   var pp=document.permissionsPolicy||document.featurePolicy;
   if(pp&&pp.allowsFeature&&!pp.allowsFeature("camera")){onErr("A câmera ao vivo está bloqueada neste ambiente. Toque em “Tirar foto do QR” abaixo, ou use “Ler QR de uma foto”.");$(o.snapbtn).classList.remove("hide");return}
   openCam().then(function(st){
    camStream=st;var v=$(o.video);v.setAttribute("playsinline","");v.setAttribute("muted","");v.muted=true;v.autoplay=true;v.srcObject=st;
    $(o.wrap).classList.remove("hide");v.onloadedmetadata=function(){var p=v.play();if(p&&p.catch)p.catch(function(){})};var p0=v.play();if(p0&&p0.catch)p0.catch(function(){});
    var cv=document.createElement("canvas"),busy=false;
    camTimer=setInterval(async function(){if(busy||v.readyState<2||!v.videoWidth)return;busy=true;
     try{var sc=Math.min(1,960/v.videoWidth);cv.width=Math.round(v.videoWidth*sc);cv.height=Math.round(v.videoHeight*sc);
     cv.getContext("2d",{willReadFrequently:true}).drawImage(v,0,0,cv.width,cv.height);var t=await decodeCv(cv);if(t&&idFrom(t)){stop();handle(t,"camera")}}catch(e){}busy=false},300)})
   .catch(function(e){onErr("A câmera ao vivo não está disponível aqui"+(e&&e.name?" ("+e.name+")":"")+". Toque em “Tirar foto do QR” para usar a câmera do celular.");$(o.snapbtn).classList.remove("hide")})}}
 var sc={stop:stop,init:init};scanners.push(sc);return sc}
RK.makeScanner=makeScanner;RK.idFrom=idFrom;RK.ensureJsQR=ensureJsQR;
RK.stopCam=function(){scanners.forEach(function(s){s.stop()})};
RK.initVerificar=function(){
 ensureJsQR().then(function(ok){$("vstat").textContent=ok?"Leitor de QR: pronto ✓":"Leitor de QR: não carregou. Verifique a internet e recarregue; você ainda pode digitar o ID."});
 $("vgo").onclick=function(){verify($("vin").value,"manual")};$("vin").onkeydown=function(e){if(e.key==="Enter")verify($("vin").value,"manual")};
 makeScanner({cam:"vcam",img:"vimg",file:"vfile",snap:"vsnap",snapbtn:"vsnapbtn",wrap:"camwrap",video:"camv",stop:"camstop"},
  function(id,orig){verify(id,orig)},function(m){$("verr").textContent=m;if(m)$("vres").innerHTML=""}).init()};
})();

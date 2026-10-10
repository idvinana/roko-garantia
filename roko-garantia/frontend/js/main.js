// Inicialização, navegação, login (um por backend) e rotas por hash
(function(){var RK=window.RK,$=RK.$,C=RK.cfg,NAMES={admin:"Backend Admin",verif:"Backend de Verificação"};
function chip(id,label,url){fetch(url+"/saude").then(function(r){return r.ok?r.json():null},function(){return null}).then(function(j){var e=$(id),ok=!!j;e.className=ok?"on":"off";e.textContent=label+(ok?" ● online":" ● sem conexão");
  var L=/\/\/(localhost|127\.0\.0\.1)/;if(ok&&j.frontend_url&&L.test(j.frontend_url)&&!L.test(location.origin)){e.className="off";e.textContent=label+" ● FRONTEND_URL aponta para localhost: os QR Codes não abrem no celular"}})}
function showView(v){["view-app","view-login-admin","view-login-verif"].forEach(function(id){$(id).classList.toggle("hide",id!==v)})}
function render(){var a=RK.auth;
 $("sec-admin").classList.toggle("hide",!a.admin);$("sec-vlog").classList.toggle("hide",!a.verif);
 [].forEach.call(document.querySelectorAll("#nav .adm"),function(b){var g=b.dataset.go;b.classList.toggle("hide",g==="sec-vlog"?!a.verif:!a.admin)});
 ["admin","verif"].forEach(function(k){$("st-"+k).textContent=a[k]?"Conectado ✓":"Não conectado";$("in-"+k).classList.toggle("hide",a[k]);$("out-"+k).classList.toggle("hide",!a[k])});
 $("pwbox").classList.toggle("hide",!(a.admin||a.verif));
 $("pw0").innerHTML=(a.admin?"<option value='admin'>Backend Admin</option>":"")+(a.verif?"<option value='verif'>Backend de Verificação</option>":"");
 if(a.admin)RK.adminRefresh();if(a.verif)RK.vlogRefresh()}
function check(){RK.auth={admin:false,verif:false};var p=[];
 ["admin","verif"].forEach(function(k){if(RK.keys[k])p.push((k==="admin"?RK.A:RK.B)("/api/admin/estatisticas").then(function(){RK.auth[k]=true},function(e){if(e.unauth)RK.keys[k]=""}))});
 return Promise.all(p).then(function(){RK.saveKeys();render()})}
RK.onUnauth=function(k){RK.keys[k]="";RK.auth[k]=false;RK.saveKeys();render();RK.toast("Sessão do "+NAMES[k]+" expirada. Entre novamente.")};
function goHash(h){if(location.hash===h)route();else location.hash=h}
function doLogin(k){var pre=k==="admin"?"la":"lv",u=$(pre+"-user").value.trim(),p=$(pre+"-pass").value,e=$(pre+"-err");
 if(!u||!p){e.textContent="Informe usuário e senha.";return}
 e.textContent="";$(pre+"-go").disabled=true;
 (k==="admin"?RK.pubA:RK.pubB)("/api/auth/login",{method:"POST",headers:RK.JH,body:JSON.stringify({usuario:u,senha:p})}).then(function(j){
  $(pre+"-go").disabled=false;$(pre+"-pass").value="";RK.keys[k]=j.token;RK.saveKeys();
  check().then(function(){goHash(k==="admin"?"#/admin":"#/verificacoes")})}).catch(function(x){$(pre+"-go").disabled=false;e.textContent=x.message})}
function route(){var h=location.hash||"",m=h.match(/^#\/verificar\/(.+)$/);
 if(h==="#/login/admin"){RK.stopCam();showView("view-login-admin");window.scrollTo(0,0);return}
 if(h==="#/login/verificacao"){RK.stopCam();showView("view-login-verif");window.scrollTo(0,0);return}
 showView("view-app");
 if(m){RK.go("sec-ver");RK.verify(decodeURIComponent(m[1]),"qr");return}
 if(/^#\/ativar/.test(h)){RK.go("sec-ativar");return}
 if(h==="#/admin"){RK.go(RK.auth.admin?"sec-admin":"sec-login");return}
 if(h==="#/verificacoes"){RK.go(RK.auth.verif?"sec-vlog":"sec-login");return}
 if(/^#\/administracao/.test(h))RK.go("sec-login")}
document.addEventListener("DOMContentLoaded",function(){
 RK.loadKeys();RK.initVerificar();RK.initAtivar();RK.initAdmin();RK.initVlog();
 chip("c-admin",NAMES.admin,C.ADMIN_API);chip("c-verif",NAMES.verif,C.VERIF_API);
 $("nav").onclick=function(e){var b=e.target.closest("button");if(!b)return;if(b.dataset.go!=="sec-ver")RK.stopCam();RK.go(b.dataset.go)};
 $("fm-admin").onsubmit=function(e){e.preventDefault();doLogin("admin")};$("fm-verif").onsubmit=function(e){e.preventDefault();doLogin("verif")};
 $("in-admin").onclick=function(){goHash("#/login/admin")};$("in-verif").onclick=function(){goHash("#/login/verificacao")};
 ["admin","verif"].forEach(function(k){$("out-"+k).onclick=function(){RK.keys[k]="";RK.auth[k]=false;RK.saveKeys();render();RK.toast("Você saiu do "+NAMES[k]+".")}});
 $("pwgo").onclick=function(){var k=$("pw0").value,e=$("pwerr");if(!k)return;if(!$("pw1").value||!$("pw2").value){e.textContent="Preencha as duas senhas.";return}if($("pw2").value.length<8){e.textContent="A nova senha precisa ter ao menos 8 caracteres.";return}
  (k==="admin"?RK.A:RK.B)("/api/auth/trocar-senha",{method:"POST",headers:RK.JH,body:JSON.stringify({atual:$("pw1").value,nova:$("pw2").value})}).then(function(){e.textContent="";$("pw1").value="";$("pw2").value="";RK.toast("Senha alterada.")}).catch(function(x){if(x.unauth)RK.fail(x);else e.textContent=x.message})};
 window.addEventListener("hashchange",route);
 check().then(route)});
})();

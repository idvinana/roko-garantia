(function(){
var RK=window.RK=window.RK||{},C=RK.cfg=window.RK_CONFIG||{};
RK.$=function(i){return document.getElementById(i)};
RK.esc=function(s){return String(s==null?"":s).replace(/[&<>"']/g,function(c){return{"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[c]})};
RK.fmt=function(s){return s?new Date(s.slice(0,10)+"T12:00:00").toLocaleDateString("pt-BR"):"-"};
RK.dt=function(s){return s?new Date(s).toLocaleString("pt-BR"):"-"};
RK.toast=function(m){var t=RK.$("toast");t.textContent=m;t.style.display="block";clearTimeout(RK.toast.t);RK.toast.t=setTimeout(function(){t.style.display="none"},5000)};
RK.keys={admin:"",verif:""};RK.auth={admin:false,verif:false};
RK.loadKeys=function(){try{RK.keys.admin=sessionStorage.getItem("rk_a")||"";RK.keys.verif=sessionStorage.getItem("rk_v")||""}catch(e){}};
RK.saveKeys=function(){try{sessionStorage.setItem("rk_a",RK.keys.admin);sessionStorage.setItem("rk_v",RK.keys.verif)}catch(e){}};
RK.feUrl=function(){return(C.FRONTEND_URL||(location.origin+location.pathname.replace(/index\.html$/,""))).replace(/\/$/,"")};
// Se config.js ainda aponta para "localhost" mas o site foi aberto por outro endereço (ex.: celular na mesma rede), usa o endereço do site
["ADMIN_API","VERIF_API"].forEach(function(k){try{var u=new URL(C[k]),L=/^(localhost|127\.0\.0\.1)$/;if(L.test(u.hostname)&&!L.test(location.hostname)){u.hostname=location.hostname;C[k]=u.origin}}catch(e){}});
RK.JH={"Content-Type":"application/json"};
RK.go=function(id){var t=RK.$(id);if(t&&t.scrollIntoView)t.scrollIntoView({behavior:"smooth",block:"start"})};
// requisições: base = endereço do backend; keyName = "admin" | "verif" | undefined (público)
RK.http=function(base,path,opt,keyName){opt=opt||{};opt.headers=Object.assign({},opt.headers||{});if(keyName&&RK.keys[keyName])opt.headers["Authorization"]="Bearer "+RK.keys[keyName];
 return fetch(base+path,opt).then(function(r){if(r.status===401&&keyName){var e=new Error("Sessão expirada ou inválida.");e.unauth=keyName;throw e}return r},
  function(){throw new Error("Sem conexão com o backend ("+base+"). Confira se ele está no ar, o CORS (ALLOWED_ORIGINS) e js/config.js.")})};
RK.json=function(base,path,opt,keyName){return RK.http(base,path,opt,keyName).then(function(r){return r.json().then(function(j){if(!r.ok)throw new Error(typeof j.detail==="string"?j.detail:"Erro "+r.status);return j},function(){throw new Error("Erro "+r.status)})})};
RK.A=function(p,o){return RK.json(C.ADMIN_API,p,o,"admin")};
RK.B=function(p,o){return RK.json(C.VERIF_API,p,o,"verif")};
RK.pubA=function(p,o){return RK.json(C.ADMIN_API,p,o)};
RK.pubB=function(p,o){return RK.json(C.VERIF_API,p,o)};
RK.blob=function(base,path,keyName,name){RK.http(base,path,null,keyName).then(function(r){if(!r.ok)return r.json().then(function(j){throw new Error(j.detail||"Erro")});return r.blob()}).then(function(b){var u=URL.createObjectURL(b);
 if(name){var a=document.createElement("a");a.href=u;a.download=name;document.body.appendChild(a);a.click();a.remove()}else if(!window.open(u,"_blank"))location.href=u;setTimeout(function(){URL.revokeObjectURL(u)},60000)}).catch(RK.fail)};
RK.fail=function(e){if(e&&e.unauth){RK.onUnauth&&RK.onUnauth(e.unauth)}else RK.toast(e&&e.message||"Erro")};
})();

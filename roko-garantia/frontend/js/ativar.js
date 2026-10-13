// Ativação da garantia pelo cliente (Backend Admin)
(function(){var RK=window.RK,$=RK.$;
RK.initAtivar=function(){
 var vid="";
 function setVid(id){vid=id||"";$("aqok").classList.toggle("hide",!vid);$("aqid").textContent=vid;$("aped").disabled=!!vid;if(vid)$("aped").value="";$("aerr").textContent=""}
 var sc=RK.makeScanner({cam:"aqcam",img:"aqimg",file:"aqfile",snap:"aqsnap",snapbtn:"aqsnapbtn",wrap:"aqwrap",video:"aqv",stop:"aqstop"},
  function(id){setVid(id);RK.toast("QR lido: "+id+". Agora informe o e-mail da compra.");$("amail").focus()},function(m){$("aerr").textContent=m});sc.init();
 $("aqclear").onclick=function(){setVid("")};
 RK.ensureJsQR().then(function(ok){$("aqstat").textContent=ok?"":"Leitor de QR não carregou. Verifique a internet ou informe o número do pedido."});
 RK.ativarSetVid=function(id){setVid(id);RK.toast("Peça "+id+" identificada. Informe o e-mail da compra.")};
 $("ago").onclick=function(){var p=$("aped").value.trim().replace(/^#/,""),m=$("amail").value.trim(),e=$("aerr");
  if(!vid&&!/^\d{3,}$/.test(p)){e.textContent="Leia o QR da peça ou informe o número do pedido (somente números).";return}
  if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(m)){e.textContent="Informe um e-mail válido.";return}
  e.textContent="";$("ago").disabled=true;
  RK.pubA("/api/validar",{method:"POST",headers:RK.JH,body:JSON.stringify(vid?{vid:vid,email:m}:{pedido:p,email:m})}).then(function(j){$("ago").disabled=false;
   $("aunits").innerHTML=j.garantias.map(function(g){return RK.card(g,true)}).join("");$("aem").textContent=j.email;
   $("af").classList.add("hide");$("ares").classList.remove("hide");$("atitle").textContent="Tudo certo!";
   $("asub").textContent=j.ja_ativada?"Esta garantia já estava ativa. Aqui estão seus dados.":"Seu óculos é original e está protegido.";
   if(RK.auth.admin&&RK.adminRefresh)RK.adminRefresh()}).catch(function(x){$("ago").disabled=false;e.textContent=x.message})};
 $("aunits").onclick=function(ev){var b=ev.target.closest("button");if(b&&b.dataset.vf)RK.goVerify(b.dataset.vf,"manual")};
 $("aagain").onclick=function(){setVid("");$("aped").value="";$("amail").value="";$("ares").classList.add("hide");$("af").classList.remove("hide");$("atitle").textContent="Ative sua garantia.";$("asub").textContent="Valide a autenticidade do seu óculos em segundos."}};
})();

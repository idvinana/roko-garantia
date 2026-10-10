// Administração (Backend Admin): pedidos, catálogo de modelos, garantias, certificados e sincronização
(function(){var RK=window.RK,$=RK.$,esc=RK.esc,MOD=[],editN=null,editC=null,tm=null;
function opts(sel){return MOD.map(function(m){return"<option value='"+m.id+"'"+(m.id===sel?" selected":"")+">"+esc(m.nome+" — "+m.cor)+"</option>"}).join("")}
function fillSel(){var v=$("f5").value;$("f5").innerHTML=opts();if(v)$("f5").value=v}
function renderCat(){$("cat").innerHTML=MOD.map(function(m){return"<div class='brow'><div><b>"+esc(m.nome)+"</b><br><small><span class='sw' style='background:"+esc(m.cor_hex)+"'></span><span class='sw' style='background:"+esc(m.lente_hex)+"'></span>"+esc(m.cor)+" · "+esc(m.lente)+"<br>"+esc(m.material)+" · "+esc(m.tamanho)+" · "+esc(m.protecao)+" · em uso: "+m.em_uso+"</small></div><div class='btns'><button class='ghost sm' data-ce='"+m.id+"'>Editar</button><button class='ghost sm' data-cd='"+m.id+"'>Excluir</button></div></div>"}).join("")}
function loadSync(){RK.A("/api/admin/verificacao").then(function(s){var ok=s.configurado&&!s.ultimo_erro,b=$("async");b.className="sync "+(!s.configurado?"":ok?"ok":"bad");
 b.innerHTML="<span><b>Backend de verificação:</b> "+(!s.configurado?"não configurado (defina VERIF_URL e SYNC_KEY no Backend Admin)":ok?"conectado ✓ · última sincronização "+(s.ultimo_ok?RK.dt(s.ultimo_ok):"—")+" · "+s.enviadas+" peça(s) enviada(s)":"falha: "+esc(s.ultimo_erro))+"</span><button class='ghost sm' id='dosync'>Sincronizar agora</button>";
 $("dosync").onclick=function(){$("dosync").textContent="Sincronizando…";RK.A("/api/admin/verificacao/sincronizar",{method:"POST"}).then(function(){RK.toast("Sincronização concluída.");loadSync();RK.vlogRefresh&&RK.vlogRefresh()}).catch(function(e){RK.fail(e);loadSync()})}}).catch(function(){})}
function loadTable(){var qs="?limit=500"+($("ast").value?"&status="+encodeURIComponent($("ast").value):"")+($("aq").value.trim()?"&q="+encodeURIComponent($("aq").value.trim()):"");
 RK.A("/api/admin/garantias"+qs).then(function(rows){$("atb").innerHTML=rows.map(function(g){var tg=g.status==="revogada"?"ativa":"revogada",lb=g.status==="revogada"?"Reativar":"Revogar";
  return"<tr><td>"+esc(g.numero)+"</td><td>"+esc(g.cliente||g.email)+"<br><span class='hint'>"+esc(g.email)+"</span></td><td><select data-m='"+esc(g.vid)+"'>"+opts(g.modelo_id)+"</select></td><td>"+esc(g.serial)+"</td><td>"+esc(g.vid)+"</td><td><span class='badge b-"+g.status+"'>"+g.status+"</span></td><td>"+RK.fmt(g.valida_ate)+"</td><td><div class='act'>"+
  "<button class='ghost sm' data-a='ver' data-v='"+esc(g.vid)+"'>Verificar</button><button class='ghost sm' data-a='pdf' data-v='"+esc(g.vid)+"'>PDF</button>"+
  "<button class='ghost sm' data-a='edit' data-n='"+esc(g.numero)+"' data-e='"+esc(g.email)+"' data-c='"+esc(g.cliente||"")+"' data-d='"+esc(g.data_compra)+"' data-mi='"+(g.modelo_id||"")+"'>Editar</button>"+
  "<button class='ghost sm' data-a='st' data-v='"+esc(g.vid)+"' data-s='"+tg+"'>"+lb+"</button><button class='ghost sm' style='color:var(--red)' data-a='del' data-n='"+esc(g.numero)+"' data-c='"+esc(g.cliente||g.email)+"'>Excluir pedido</button></div></td></tr>"}).join("")||"<tr><td colspan='8' class='hint'>Nenhum registro.</td></tr>"}).catch(RK.fail)}
function refresh(){loadSync();
 RK.A("/api/admin/estatisticas").then(function(s){$("astats").innerHTML=[["Pedidos",s.pedidos],["Pendentes",s.pendentes],["Ativas",s.ativas],["Revogadas",s.revogadas],["Ativação",Math.round(s.taxa_ativacao*100)+"%"]].map(function(x){return"<div class='stat'><b>"+x[1]+"</b><span>"+x[0]+"</span></div>"}).join("")}).catch(function(){});
 RK.A("/api/admin/modelos").then(function(m){MOD=m;renderCat();fillSel();loadTable()}).catch(RK.fail)}
RK.adminRefresh=refresh;
function endEdit(){editN=null;["f1","f2","f3","f4"].forEach(function(i){$(i).value=""});$("f6").value=1;$("f1").disabled=false;$("f6").disabled=false;$("fh").textContent="Cadastrar pedido";$("save").textContent="CADASTRAR";$("pdfp").classList.add("hide");$("cancel").classList.add("hide");$("ferr").textContent=""}
function endC(){editC=null;["c1","c2","c3"].forEach(function(i){$(i).value=""});$("c4").value="Acetato";$("c5").value="52 · 20 · 145 mm";$("c6").value="UV400";$("c7").value="#0b0b0c";$("c8").value="#3b3b40";$("cth").textContent="Novo modelo";$("ccancel").classList.add("hide");$("cerr").textContent=""}
RK.initAdmin=function(){
 $("aq").oninput=function(){clearTimeout(tm);tm=setTimeout(loadTable,300)};$("ast").onchange=loadTable;
 $("cancel").onclick=endEdit;$("pdfp").onclick=function(){if(editN)RK.blob(RK.cfg.ADMIN_API,"/api/admin/pedidos/"+encodeURIComponent(editN)+"/certificados.pdf","admin")};
 $("atb").onclick=function(ev){var b=ev.target.closest("button");if(!b)return;var d=b.dataset;
  if(d.a==="ver")RK.goVerify(d.v,"manual");
  else if(d.a==="pdf")RK.blob(RK.cfg.ADMIN_API,"/api/admin/garantias/"+encodeURIComponent(d.v)+"/certificado.pdf","admin");
  else if(d.a==="st")RK.A("/api/admin/garantias/"+encodeURIComponent(d.v),{method:"PATCH",headers:RK.JH,body:JSON.stringify({status:d.s})}).then(refresh).catch(RK.fail);
  else if(d.a==="del"){if(!confirm("Excluir o pedido "+d.n+" ("+d.c+") e TODAS as garantias dele, inclusive as já ativadas?\n\nAs peças também saem do verificador de autenticidade: QR Codes já impressos deixarão de ser reconhecidos.\n\nNão dá para desfazer."))return;
   RK.A("/api/admin/pedidos/"+encodeURIComponent(d.n),{method:"DELETE"}).then(function(r){if(editN===d.n)endEdit();RK.toast("Pedido "+r.numero+" excluído ("+r.garantias_removidas+" garantia(s)).");refresh();if(RK.vlogRefresh)RK.vlogRefresh()}).catch(function(x){if(x.unauth)RK.fail(x);else RK.toast(x.message)})}
  else if(d.a==="edit"){editN=d.n;$("f1").value=d.n;$("f1").disabled=true;$("f2").value=d.e;$("f3").value=d.c;$("f4").value=d.d;if(d.mi)$("f5").value=d.mi;$("f6").disabled=true;$("fh").textContent="Editar pedido "+d.n;$("save").textContent="SALVAR ALTERAÇÕES";$("pdfp").classList.remove("hide");$("cancel").classList.remove("hide");$("ferr").textContent="";RK.go("sec-ped")}};
 $("atb").onchange=function(ev){var t=ev.target;if(!t.dataset.m)return;RK.A("/api/admin/garantias/"+encodeURIComponent(t.dataset.m),{method:"PATCH",headers:RK.JH,body:JSON.stringify({modelo_id:parseInt(t.value,10)})}).then(refresh).catch(RK.fail)};
 $("save").onclick=function(){var n=$("f1").value.trim(),m=$("f2").value.trim(),d=$("f4").value,e=$("ferr"),mi=parseInt($("f5").value,10)||null;
  if(!n){e.textContent="Informe o número do pedido.";return}if(!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(m)){e.textContent="E-mail inválido.";return}if(!d){e.textContent="Informe a data da compra.";return}
  var p=editN?RK.A("/api/admin/pedidos/"+encodeURIComponent(editN),{method:"PATCH",headers:RK.JH,body:JSON.stringify({email:m,cliente:$("f3").value.trim(),data_compra:d,modelo_id:mi})}):
   RK.A("/api/admin/pedidos",{method:"POST",headers:RK.JH,body:JSON.stringify({numero:n,email:m,cliente:$("f3").value.trim()||null,data_compra:d,modelo_id:mi,quantidade:parseInt($("f6").value,10)||1})});
  p.then(function(){endEdit();refresh()}).catch(function(x){if(x.unauth)RK.fail(x);else e.textContent=x.message})};
 $("ccancel").onclick=endC;
 $("csave").onclick=function(){var f=function(i){return $(i).value.trim()};if(!f("c1")){$("cerr").textContent="Informe o nome do modelo.";return}
  var o={nome:f("c1"),cor:f("c2")||"-",lente:f("c3")||"-",material:f("c4")||"-",tamanho:f("c5")||"-",protecao:f("c6")||"-",cor_hex:$("c7").value,lente_hex:$("c8").value};
  RK.A(editC?"/api/admin/modelos/"+editC:"/api/admin/modelos",{method:editC?"PATCH":"POST",headers:RK.JH,body:JSON.stringify(o)}).then(function(){endC();refresh()}).catch(function(x){if(x.unauth)RK.fail(x);else $("cerr").textContent=x.message})};
 $("cat").onclick=function(ev){var b=ev.target.closest("button");if(!b)return;var d=b.dataset;
  if(d.ce){var m=MOD.filter(function(x){return String(x.id)===d.ce})[0];editC=m.id;$("c1").value=m.nome;$("c2").value=m.cor;$("c3").value=m.lente;$("c4").value=m.material;$("c5").value=m.tamanho;$("c6").value=m.protecao;$("c7").value=m.cor_hex;$("c8").value=m.lente_hex;$("cth").textContent="Editar modelo";$("ccancel").classList.remove("hide");$("cerr").textContent="";$("c1").scrollIntoView({behavior:"smooth",block:"center"})}
  else if(d.cd)RK.A("/api/admin/modelos/"+d.cd,{method:"DELETE"}).then(function(){$("cerr").textContent="";refresh()}).catch(function(x){if(x.unauth)RK.fail(x);else $("cerr").textContent=x.message})};
 $("acsv").onclick=function(){RK.blob(RK.cfg.ADMIN_API,"/api/admin/exportar.csv","admin","garantias.csv")};$("aimp").onclick=function(){$("aimpf").click()};
 $("aimpf").onchange=function(){var f=this.files[0];if(!f)return;var fd=new FormData();fd.append("arquivo",f);this.value="";$("aimpr").textContent="Importando…";
  RK.A("/api/admin/pedidos/importar",{method:"POST",body:fd}).then(function(r){$("aimpr").textContent="Criados: "+r.criados+" · Duplicados ignorados: "+r.ignorados_duplicados.length+" · Erros: "+r.erros.length+(r.erros.length?" ("+r.erros.map(function(x){return"linha "+x.linha+": "+x.erro}).join("; ")+")":"");refresh()}).catch(function(e){$("aimpr").textContent="Falha: "+e.message})}};
})();

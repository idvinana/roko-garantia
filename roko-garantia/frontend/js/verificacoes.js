// Registro de verificações (Backend de Verificação): consultas, alertas e peças sincronizadas
(function(){var RK=window.RK,$=RK.$,esc=RK.esc,tm=null,UN=[],editU=null;
function mais12(){var d=new Date();d.setFullYear(d.getFullYear()+1);return d.toISOString().slice(0,10)}
function endU(){editU=null;["u1","u2","u4","u5","u6","u7","u14"].forEach(function(i){$(i).value=""});$("u3").value="pendente";$("u8").value="Acetato";$("u9").value="52 · 20 · 145 mm";$("u10").value="UV400";$("u11").value="#0b0b0c";$("u12").value="#3b3b40";$("u13").value=mais12();
 $("u1").disabled=false;$("uth").textContent="Cadastrar peça";$("ucancel").classList.add("hide");$("ulibw").classList.add("hide");$("ulib").checked=false;$("uerr").textContent=""}
function hx(v,d){return/^#[0-9a-fA-F]{6}$/.test(v||"")?v:d}
function refresh(){
 RK.B("/api/admin/estatisticas").then(function(s){var e=s.por_estado||{};
  $("vstats").innerHTML=[["Consultas",s.consultas_total],["Autênticas ativas",e.ativa||0],["Não encontradas",e.nao_encontrado||0],["Peças registradas",s.unidades_total]].map(function(x){return"<div class='stat'><b>"+x[1]+"</b><span>"+x[0]+"</span></div>"}).join("");
  $("vsyncinfo").textContent="Última sincronização com o Backend Admin: "+RK.dt(s.ultima_sincronizacao);
  $("valerta").innerHTML=s.nao_encontrados_24h>0?"<div class='alert'>⚠ "+s.nao_encontrados_24h+" consulta(s) a códigos NÃO encontrados nas últimas 24 h — possível tentativa de falsificação.</div>":""}).catch(RK.fail);
 var qs="?limit=100"+($("ves").value?"&estado="+$("ves").value:"")+($("vq").value.trim()?"&vid="+encodeURIComponent($("vq").value.trim()):"");
 RK.B("/api/admin/consultas"+qs).then(function(r){$("vtb").innerHTML=r.map(function(c){return"<tr><td>"+RK.dt(c.quando)+"</td><td>"+esc(c.vid)+"</td><td><span class='badge b-"+esc(c.estado)+"'>"+esc(c.estado)+"</span></td><td>"+esc(c.origem)+"</td></tr>"}).join("")||"<tr><td colspan='4' class='hint'>Nenhuma consulta.</td></tr>"}).catch(function(){});
 RK.B("/api/admin/unidades?limit=100"+($("vuq").value.trim()?"&q="+encodeURIComponent($("vuq").value.trim()):"")).then(function(r){UN=r;$("vub").innerHTML=r.map(function(u){var o=u.origem_cadastro==="manual"?"cadastro manual":(u.travado?"sincronizada 🔒 editada":"sincronizada");
  return"<tr><td>"+esc(u.vid)+"</td><td>"+esc(u.serial)+"</td><td>"+esc(u.modelo.n)+"</td><td><span class='badge b-"+esc(u.status)+"'>"+esc(u.status)+"</span></td><td>"+RK.fmt(u.valida_ate)+"</td><td class='hint'>"+o+"</td><td><div class='act'><button class='ghost sm' data-ue='"+esc(u.vid)+"'>Editar</button>"+(u.origem_cadastro==="manual"?"<button class='ghost sm' data-ud='"+esc(u.vid)+"'>Excluir</button>":"")+"</div></td></tr>"}).join("")||"<tr><td colspan='7' class='hint'>Nenhuma peça registrada.</td></tr>"}).catch(function(){})}
RK.vlogRefresh=function(){if(RK.auth.verif)refresh()};
RK.initVlog=function(){
 $("vq").oninput=$("vuq").oninput=function(){clearTimeout(tm);tm=setTimeout(refresh,300)};$("ves").onchange=refresh;$("vrefresh").onclick=refresh;
 endU();
 $("usave").onclick=function(){var f=function(i){return $(i).value.trim()},e=$("uerr"),vid=f("u1").toUpperCase();
  if(!f("u2")){e.textContent="Informe o nº de série.";return}if(!f("u5")){e.textContent="Informe o nome do modelo.";return}if(!f("u13")){e.textContent="Informe até quando a garantia é válida.";return}
  if(!editU&&vid&&!/^RKO-[A-Z0-9]{4}-[A-Z0-9]{4}$/.test(vid)){e.textContent="ID inválido. Use o formato RKO-AB12-CD34 ou deixe vazio para gerar.";return}
  var b={serial:f("u2"),status:$("u3").value,produto:f("u4")||null,modelo:{n:f("u5"),cor:f("u6"),lente:f("u7"),material:f("u8"),tam:f("u9"),uv:f("u10"),hex:$("u11").value,lh:$("u12").value},valida_ate:f("u13"),ativada_em:f("u14")||null};
  if(editU)b.voltar_a_sincronizar=$("ulib").checked;else if(vid)b.vid=vid;
  e.textContent="";RK.B(editU?"/api/admin/unidades/"+encodeURIComponent(editU):"/api/admin/unidades",{method:editU?"PATCH":"POST",headers:RK.JH,body:JSON.stringify(b)}).then(function(u){RK.toast(editU?"Peça "+u.vid+" atualizada.":"Peça cadastrada: "+u.vid);endU();refresh()}).catch(function(x){if(x.unauth)RK.fail(x);else e.textContent=x.message})};
 $("ucancel").onclick=endU;
 $("vub").onclick=function(ev){var t=ev.target.closest("button");if(!t)return;
  if(t.dataset.ue){var u=UN.filter(function(x){return x.vid===t.dataset.ue})[0];if(!u)return;editU=u.vid;var m=u.modelo||{};
   $("u1").value=u.vid;$("u1").disabled=true;$("u2").value=u.serial;$("u3").value=u.status;$("u4").value=u.produto||"";$("u5").value=m.n||"";$("u6").value=m.cor||"";$("u7").value=m.lente||"";$("u8").value=m.material||"";$("u9").value=m.tam||"";$("u10").value=m.uv||"";$("u11").value=hx(m.hex,"#0b0b0c");$("u12").value=hx(m.lh,"#3b3b40");$("u13").value=(u.valida_ate||"").slice(0,10);$("u14").value=(u.ativada_em||"").slice(0,10);
   $("uth").textContent="Editar peça "+u.vid;$("ucancel").classList.remove("hide");$("ulib").checked=false;$("ulibw").classList.toggle("hide",!(u.origem_cadastro==="sync"&&u.travado));$("uerr").textContent="";$("ufm").scrollIntoView({behavior:"smooth",block:"start"})}
  else if(t.dataset.ud){if(!confirm("Excluir a peça "+t.dataset.ud+"? O código deixará de ser reconhecido como autêntico."))return;
   RK.B("/api/admin/unidades/"+encodeURIComponent(t.dataset.ud),{method:"DELETE"}).then(function(){RK.toast("Peça excluída.");if(editU===t.dataset.ud)endU();refresh()}).catch(function(x){if(x.unauth)RK.fail(x);else RK.toast(x.message)})}};
 $("vcsv").onclick=function(){RK.blob(RK.cfg.VERIF_API,"/api/admin/exportar-consultas.csv","verif","consultas.csv")}};
})();

"""ROKO IKIGAI STUDIO — BACKEND DE VERIFICAÇÃO DE AUTENTICIDADE (somente API).
Guarda apenas o necessário para confirmar a peça (sem nome, e-mail ou CPF) e registra cada consulta.
Recebe os dados do Backend Admin por sincronização autenticada (X-Sync-Key)."""
import os, csv, io, re, hmac, hashlib, sqlite3, secrets, time, logging, json
from datetime import date, datetime, timezone
from contextlib import contextmanager
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Request, Header, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from auth import instalar

log = logging.getLogger("roko-verif"); logging.basicConfig(level=logging.INFO)
DB_PATH = os.getenv("VERIF_DB_PATH", "./data/verificacao.db")
ADMIN_KEY = os.getenv("VERIF_ADMIN_KEY") or secrets.token_urlsafe(24)
if not os.getenv("VERIF_ADMIN_KEY"): log.warning("VERIF_ADMIN_KEY não definida. Chave temporária: %s", ADMIN_KEY)
SYNC_KEY = os.getenv("SYNC_KEY", "")
ADMIN_USER = os.getenv("VERIF_USER", "admin"); ADMIN_PASSWORD = os.getenv("VERIF_PASSWORD", "")
TOKEN_SECRET = os.getenv("VERIF_TOKEN_SECRET") or secrets.token_urlsafe(32)
if not os.getenv("VERIF_TOKEN_SECRET"): log.warning("VERIF_TOKEN_SECRET não definido: as sessões de login serão perdidas a cada reinício.")
TOKEN_TTL = int(os.getenv("TOKEN_TTL_MIN", "480"))
if not SYNC_KEY: log.warning("SYNC_KEY não definida: a sincronização com o Backend Admin ficará DESATIVADA.")
IP_SALT = (os.getenv("IP_SALT") or ADMIN_KEY).encode()
TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"
ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
BASE = os.path.dirname(os.path.abspath(__file__))
VID_RE = re.compile(r"^RKO-[A-Z0-9]{4}-[A-Z0-9]{4}$")
ORIGENS = {"manual", "qr", "foto", "camera"}

app = FastAPI(title="ROKO IKIGAI — Backend de Verificação", version="1.0.0")
if not ORIGINS: log.warning("ALLOWED_ORIGINS vazio: o frontend NÃO conseguirá chamar esta API (CORS). Defina o endereço do site.")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET", "POST", "PATCH", "DELETE"], allow_headers=["*"])

SCHEMA = """
CREATE TABLE IF NOT EXISTS unidades(vid TEXT PRIMARY KEY, serial TEXT NOT NULL, status TEXT NOT NULL, produto TEXT, modelo TEXT NOT NULL,
  ativada_em TEXT, valida_ate TEXT NOT NULL, atualizado_em TEXT NOT NULL, origem_cadastro TEXT NOT NULL DEFAULT 'sync', travado INTEGER NOT NULL DEFAULT 0);
CREATE TABLE IF NOT EXISTS consultas(id INTEGER PRIMARY KEY AUTOINCREMENT, quando TEXT NOT NULL, vid TEXT NOT NULL, estado TEXT NOT NULL, origem TEXT NOT NULL, ip_hash TEXT);
CREATE INDEX IF NOT EXISTS ix_c_quando ON consultas(quando);
CREATE INDEX IF NOT EXISTS ix_c_estado ON consultas(estado);
CREATE TABLE IF NOT EXISTS meta(k TEXT PRIMARY KEY, v TEXT);
"""
@contextmanager
def db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15); conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn; conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

admin, seed_usuario = instalar(app, db, "verificacao", TOKEN_SECRET, TOKEN_TTL, ADMIN_USER, ADMIN_PASSWORD, ADMIN_KEY, log)

@app.on_event("startup")
def _init():
    with db() as c:
        c.executescript(SCHEMA)
        cols = {r["name"] for r in c.execute("PRAGMA table_info(unidades)")}   # bancos criados antes do cadastro manual
        if "origem_cadastro" not in cols: c.execute("ALTER TABLE unidades ADD COLUMN origem_cadastro TEXT NOT NULL DEFAULT 'sync'")
        if "travado" not in cols: c.execute("ALTER TABLE unidades ADD COLUMN travado INTEGER NOT NULL DEFAULT 0")
    seed_usuario()

def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def client_ip(req):
    if TRUST_PROXY and req.headers.get("x-forwarded-for"): return req.headers["x-forwarded-for"].split(",")[0].strip()
    return req.client.host if req.client else "?"
def ip_hash(req): return hmac.new(IP_SALT, client_ip(req).encode(), hashlib.sha256).hexdigest()[:16]
_hits: dict = {}
def rate_limit(req, limit=60, window=600):
    ip, t = client_ip(req), time.time(); arr = [x for x in _hits.get(ip, []) if t - x < window]
    if len(arr) >= limit: raise HTTPException(429, "Muitas consultas. Aguarde alguns minutos.")
    arr.append(t); _hits[ip] = arr

# ---------- sincronização (interno) ----------
class UnidadeIn(BaseModel):
    vid: str = Field(pattern=r"^RKO-[A-Z0-9]{4}-[A-Z0-9]{4}$")
    serial: str = Field(min_length=1, max_length=40)
    status: str = Field(pattern="^(pendente|ativa|revogada)$")
    produto: Optional[str] = None
    modelo: dict
    ativada_em: Optional[str] = None
    valida_ate: str
class SyncIn(BaseModel):
    unidades: List[UnidadeIn] = Field(max_length=500)

def _checa_sync(x):
    if not SYNC_KEY or not x or not hmac.compare_digest(x, SYNC_KEY): raise HTTPException(401, "Chave de sincronização inválida.")
class RemoverIn(BaseModel):
    vids: List[str] = Field(max_length=500)

@app.post("/api/interno/remover", tags=["Interno"])
def remover(b: RemoverIn, x_sync_key: Optional[str] = Header(None)):
    """Chamado pelo Backend Admin ao excluir um pedido: esquece as peças sincronizadas (peças cadastradas manualmente aqui não são tocadas)."""
    _checa_sync(x_sync_key); n = 0
    with db() as c:
        for v in b.vids: n += c.execute("DELETE FROM unidades WHERE vid=? AND origem_cadastro='sync'", (v.strip().upper(),)).rowcount
    return {"removidas": n}

@app.post("/api/interno/sincronizar", tags=["Interno"])
def sincronizar(b: SyncIn, x_sync_key: Optional[str] = Header(None)):
    """Chamado pelo Backend Admin. Atualiza (upsert) as unidades verificáveis."""
    _checa_sync(x_sync_key)
    t = now_iso()   # peças travadas (cadastradas ou editadas aqui) não são sobrescritas
    with db() as c:
        c.executemany("""INSERT INTO unidades(vid,serial,status,produto,modelo,ativada_em,valida_ate,atualizado_em) VALUES(?,?,?,?,?,?,?,?)
            ON CONFLICT(vid) DO UPDATE SET serial=excluded.serial,status=excluded.status,produto=excluded.produto,modelo=excluded.modelo,
            ativada_em=excluded.ativada_em,valida_ate=excluded.valida_ate,atualizado_em=excluded.atualizado_em
            WHERE unidades.travado=0""" ,
            [(u.vid, u.serial, u.status, u.produto, json.dumps(u.modelo, ensure_ascii=False), u.ativada_em, u.valida_ate, t) for u in b.unidades])
        c.execute("INSERT INTO meta(k,v) VALUES('ultima_sincronizacao',?) ON CONFLICT(k) DO UPDATE SET v=excluded.v", (t,))
    return {"recebidas": len(b.unidades)}

# ---------- público: verificação ----------
def estado_de(g):
    hoje = date.today().isoformat()
    if g["status"] == "revogada": return "revogada", "Peça registrada, mas a garantia foi cancelada. Fale com a ROKO IKIGAI STUDIO."
    if g["status"] == "pendente": return "pendente", "Peça original. A garantia ainda não foi ativada: use o QR Code do cartão."
    if hoje > g["valida_ate"]: return "expirada", f"Peça original. O prazo de garantia terminou em {g['valida_ate']}."
    return "ativa", f"Peça original com garantia vigente até {g['valida_ate']}."

@app.get("/api/verificar/{vid}", tags=["Público"])
def verificar(vid: str, req: Request, origem: str = "manual"):
    """Verifica uma peça pelo ID. Não expõe dados pessoais. Cada consulta é registrada."""
    rate_limit(req)
    vid = vid.strip().upper(); origem = origem if origem in ORIGENS else "manual"
    with db() as c:
        g = c.execute("SELECT * FROM unidades WHERE vid=?", (vid,)).fetchone() if VID_RE.match(vid) else None
        if not g:
            estado = "nao_encontrado"
            c.execute("INSERT INTO consultas(quando,vid,estado,origem,ip_hash) VALUES(?,?,?,?,?)", (now_iso(), vid if VID_RE.match(vid) else "(formato inválido)", estado, origem, ip_hash(req)))
            return {"autentica": False, "valida": False, "estado": estado, "mensagem": "Não foi possível confirmar a autenticidade desta peça."}
        estado, msg = estado_de(g)
        c.execute("INSERT INTO consultas(quando,vid,estado,origem,ip_hash) VALUES(?,?,?,?,?)", (now_iso(), vid, estado, origem, ip_hash(req)))
    return {"autentica": True, "valida": estado == "ativa", "estado": estado, "mensagem": msg, "produto": g["produto"], "modelo": json.loads(g["modelo"]),
            "serial": g["serial"], "vid": g["vid"], "status": g["status"], "ativada_em": g["ativada_em"], "valida_ate": g["valida_ate"]}

# ---------- admin da verificação ----------
A = [Depends(admin)]   # login (/api/auth/login) ou chave de serviço (X-API-Key)

@app.get("/api/admin/estatisticas", tags=["Admin"], dependencies=A)
def stats():
    with db() as c:
        q = lambda s, *a: c.execute(s, a).fetchall()
        por_estado = {r["estado"]: r["n"] for r in q("SELECT estado, COUNT(*) n FROM consultas GROUP BY estado")}
        por_origem = {r["origem"]: r["n"] for r in q("SELECT origem, COUNT(*) n FROM consultas GROUP BY origem")}
        dias = [dict(r) for r in q("SELECT substr(quando,1,10) dia, COUNT(*) n FROM consultas WHERE quando >= datetime('now','-7 days') GROUP BY dia ORDER BY dia")]
        n24 = c.execute("SELECT COUNT(*) FROM consultas WHERE estado='nao_encontrado' AND quando >= datetime('now','-1 day')").fetchone()[0]
        top = [dict(r) for r in q("SELECT vid, COUNT(*) n FROM consultas WHERE estado!='nao_encontrado' GROUP BY vid ORDER BY n DESC LIMIT 5")]
        un = {r["status"]: r["n"] for r in q("SELECT status, COUNT(*) n FROM unidades GROUP BY status")}
        sync = c.execute("SELECT v FROM meta WHERE k='ultima_sincronizacao'").fetchone()
    return {"consultas_total": sum(por_estado.values()), "por_estado": por_estado, "por_origem": por_origem, "ultimos_7_dias": dias,
            "nao_encontrados_24h": n24, "mais_consultadas": top, "unidades_total": sum(un.values()), "unidades_por_status": un,
            "ultima_sincronizacao": sync["v"] if sync else None}

@app.get("/api/admin/consultas", tags=["Admin"], dependencies=A)
def consultas(estado: Optional[str] = None, origem: Optional[str] = None, vid: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    sql, a = "SELECT id,quando,vid,estado,origem FROM consultas WHERE 1=1", []
    if estado: sql += " AND estado=?"; a.append(estado)
    if origem: sql += " AND origem=?"; a.append(origem)
    if vid: sql += " AND vid LIKE ?"; a.append(f"%{vid.upper()}%")
    with db() as c: return [dict(r) for r in c.execute(sql + " ORDER BY id DESC LIMIT ? OFFSET ?", [*a, limit, offset])]

@app.get("/api/admin/unidades", tags=["Admin"], dependencies=A)
def unidades(q: Optional[str] = None, status: Optional[str] = None, limit: int = Query(100, le=500)):
    sql, a = "SELECT vid,serial,status,produto,modelo,ativada_em,valida_ate,atualizado_em,origem_cadastro,travado FROM unidades WHERE 1=1", []
    if status: sql += " AND status=?"; a.append(status)
    if q: sql += " AND (vid LIKE ? OR serial LIKE ? OR modelo LIKE ?)"; a += [f"%{q}%"] * 3
    with db() as c:
        return [{**dict(r), "modelo": json.loads(r["modelo"])} for r in c.execute(sql + " ORDER BY atualizado_em DESC LIMIT ?", [*a, limit])]

# ---------- admin: cadastro e edição de peças ----------
DEFAULT_PRODUCT = "Óculos — Drop 01 Coastal Purpose"
ALFA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
HEX = r"^#[0-9a-fA-F]{6}$"
class ModeloIn(BaseModel):
    n: str = Field(min_length=1, max_length=80); cor: str = Field("", max_length=60); lente: str = Field("", max_length=60)
    material: str = Field("Acetato", max_length=60); tam: str = Field("", max_length=40); uv: str = Field("UV400", max_length=30)
    hex: str = Field("#0b0b0c", pattern=HEX); lh: str = Field("#3b3b40", pattern=HEX)
class UnidadeNova(BaseModel):
    vid: Optional[str] = Field(None, pattern=r"^RKO-[A-Z0-9]{4}-[A-Z0-9]{4}$")   # vazio = gera automaticamente
    serial: str = Field(min_length=1, max_length=40)
    status: str = Field("pendente", pattern="^(pendente|ativa|revogada)$")
    produto: Optional[str] = Field(None, max_length=120)
    modelo: ModeloIn
    ativada_em: Optional[date] = None
    valida_ate: date
class UnidadePatch(BaseModel):
    serial: Optional[str] = Field(None, min_length=1, max_length=40)
    status: Optional[str] = Field(None, pattern="^(pendente|ativa|revogada)$")
    produto: Optional[str] = Field(None, max_length=120)
    modelo: Optional[ModeloIn] = None
    ativada_em: Optional[date] = None
    valida_ate: Optional[date] = None
    voltar_a_sincronizar: bool = False   # só para peças vindas do Backend Admin: libera para receber atualizações de novo

def _un(r): return {**dict(r), "modelo": json.loads(r["modelo"])}
def _vid_novo(c):
    while True:
        v = "RKO-" + "".join(secrets.choice(ALFA) for _ in range(4)) + "-" + "".join(secrets.choice(ALFA) for _ in range(4))
        if not c.execute("SELECT 1 FROM unidades WHERE vid=?", (v,)).fetchone(): return v
def _serial_livre(c, serial, vid=None):
    r = c.execute("SELECT vid FROM unidades WHERE serial=? AND vid!=?", (serial, vid or "")).fetchone()
    if r: raise HTTPException(409, f"O nº de série {serial} já está cadastrado na peça {r['vid']}.")

@app.post("/api/admin/unidades", tags=["Admin · Peças"], dependencies=A, status_code=201)
def criar_unidade(b: UnidadeNova):
    """Cadastra uma peça manualmente. Peças manuais nunca são sobrescritas pela sincronização."""
    with db() as c:
        vid = b.vid or _vid_novo(c)
        if c.execute("SELECT 1 FROM unidades WHERE vid=?", (vid,)).fetchone(): raise HTTPException(409, f"O ID {vid} já está cadastrado.")
        _serial_livre(c, b.serial.strip())
        ativ = (b.ativada_em or date.today()).isoformat() if b.status == "ativa" else (b.ativada_em.isoformat() if b.ativada_em else None)
        c.execute("INSERT INTO unidades(vid,serial,status,produto,modelo,ativada_em,valida_ate,atualizado_em,origem_cadastro,travado) VALUES(?,?,?,?,?,?,?,?,?,?)",
                  (vid, b.serial.strip(), b.status, b.produto or DEFAULT_PRODUCT, json.dumps(b.modelo.model_dump(), ensure_ascii=False), ativ, b.valida_ate.isoformat(), now_iso(), "manual", 1))
        return _un(c.execute("SELECT * FROM unidades WHERE vid=?", (vid,)).fetchone())

@app.patch("/api/admin/unidades/{vid}", tags=["Admin · Peças"], dependencies=A)
def editar_unidade(vid: str, b: UnidadePatch):
    """Edita uma peça. Ao editar uma peça sincronizada ela fica 'travada' (a sincronização deixa de sobrescrevê-la) até você liberar."""
    vid = vid.strip().upper()
    with db() as c:
        r = c.execute("SELECT * FROM unidades WHERE vid=?", (vid,)).fetchone()
        if not r: raise HTTPException(404, "Peça não encontrada.")
        d = b.model_dump(exclude_unset=True); d.pop("voltar_a_sincronizar", None)
        serial = d["serial"].strip() if d.get("serial") else r["serial"]
        if serial != r["serial"]: _serial_livre(c, serial, vid)
        status = d.get("status", r["status"])
        ativ = d["ativada_em"].isoformat() if d.get("ativada_em") else r["ativada_em"]
        if status == "ativa" and not ativ: ativ = date.today().isoformat()
        modelo = json.dumps(d["modelo"], ensure_ascii=False) if "modelo" in d and d["modelo"] is not None else r["modelo"]
        valida = d["valida_ate"].isoformat() if d.get("valida_ate") else r["valida_ate"]
        travado = 0 if (b.voltar_a_sincronizar and r["origem_cadastro"] == "sync") else 1
        c.execute("UPDATE unidades SET serial=?,status=?,produto=?,modelo=?,ativada_em=?,valida_ate=?,atualizado_em=?,travado=? WHERE vid=?",
                  (serial, status, d.get("produto") or r["produto"], modelo, ativ, valida, now_iso(), travado, vid))
        return _un(c.execute("SELECT * FROM unidades WHERE vid=?", (vid,)).fetchone())

@app.delete("/api/admin/unidades/{vid}", tags=["Admin · Peças"], dependencies=A)
def excluir_unidade(vid: str):
    """Exclui só peças cadastradas manualmente. Peças sincronizadas voltariam na próxima sincronização: use o status 'revogada'."""
    vid = vid.strip().upper()
    with db() as c:
        r = c.execute("SELECT origem_cadastro FROM unidades WHERE vid=?", (vid,)).fetchone()
        if not r: raise HTTPException(404, "Peça não encontrada.")
        if r["origem_cadastro"] != "manual": raise HTTPException(409, "Esta peça veio do Backend Admin e voltaria na próxima sincronização. Mude o status para 'revogada' em vez de excluir.")
        c.execute("DELETE FROM unidades WHERE vid=?", (vid,))
    return {"ok": True}

@app.get("/api/admin/exportar-consultas.csv", tags=["Admin"], dependencies=A)
def exportar():
    buf = io.StringIO(); w = csv.writer(buf); w.writerow(["quando", "vid", "estado", "origem"])
    with db() as c:
        for r in c.execute("SELECT quando,vid,estado,origem FROM consultas ORDER BY id"): w.writerow(list(r))
    return StreamingResponse(iter(["\ufeff" + buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=consultas.csv"})

# ---------- raiz / saúde ----------
@app.get("/", include_in_schema=False)
def raiz(): return {"servico": "ROKO IKIGAI — Backend de Verificação", "docs": "/docs", "saude": "/saude"}
@app.get("/saude", include_in_schema=False)
def saude(): return {"ok": True}

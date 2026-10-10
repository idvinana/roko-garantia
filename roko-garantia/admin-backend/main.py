"""ROKO IKIGAI STUDIO — BACKEND ADMIN (somente API): pedidos, catálogo de modelos, garantias, ativação e certificados.
Sincroniza o que é público (sem dados pessoais) com o BACKEND DE VERIFICAÇÃO."""
import os, re, csv, io, hmac, hashlib, sqlite3, secrets, smtplib, time, calendar, logging, json, threading, urllib.request
from datetime import date, datetime, timezone
from email.message import EmailMessage
from contextlib import contextmanager
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks, UploadFile, File, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, RedirectResponse, StreamingResponse, Response
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field
from certificado import build_pdf
from auth import instalar

log = logging.getLogger("roko-admin"); logging.basicConfig(level=logging.INFO)
DB_PATH = os.getenv("DB_PATH", "./data/admin.db")
ADMIN_KEY = os.getenv("ADMIN_API_KEY") or secrets.token_urlsafe(24)
if not os.getenv("ADMIN_API_KEY"): log.warning("ADMIN_API_KEY não definida. Chave temporária: %s", ADMIN_KEY)
PEPPER = (os.getenv("CPF_PEPPER") or ADMIN_KEY).encode()
MONTHS = int(os.getenv("WARRANTY_MONTHS", "12"))
TRUST_PROXY = os.getenv("TRUST_PROXY", "0") == "1"
FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:3000").rstrip("/")   # site (frontend): usado nos QR Codes e e-mails
VERIF_URL = os.getenv("VERIF_URL", "").rstrip("/")
SYNC_KEY = os.getenv("SYNC_KEY", "")
ADMIN_USER = os.getenv("ADMIN_USER", "admin"); ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "")
TOKEN_SECRET = os.getenv("TOKEN_SECRET") or secrets.token_urlsafe(32)
if not os.getenv("TOKEN_SECRET"): log.warning("TOKEN_SECRET não definido: as sessões de login serão perdidas a cada reinício.")
TOKEN_TTL = int(os.getenv("TOKEN_TTL_MIN", "480"))
if re.search(r"//(localhost|127\.0\.0\.1)", FRONTEND_URL): log.warning("FRONTEND_URL=%s aponta para esta máquina: os QR Codes dos certificados NÃO abrirão no celular dos clientes. Defina o endereço público do site.", FRONTEND_URL)
if VERIF_URL and not SYNC_KEY: log.warning("VERIF_URL definida, mas SYNC_KEY vazia: a sincronização será recusada.")
ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "").split(",") if o.strip()]
DEFAULT_PRODUCT = "Óculos — Drop 01 Coastal Purpose"
BASE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_MODELOS = [("Atlantic Current","Midnight Black","Fumê degradê","#0B0B0C","#3b3b40"),
                   ("Golden Horizon","Sand Stone","Âmbar","#D8CDB8","#b9803a"),
                   ("Endless Tide","Ocean Deep","Azul espelhada","#0E2A3F","#2f6f9c"),
                   ("Salt Ritual","Salt White","Cinza","#F5F2EA","#6b6b70")]

app = FastAPI(title="ROKO IKIGAI — Backend Admin", version="2.0.0")
if not ORIGINS: log.warning("ALLOWED_ORIGINS vazio: o frontend NÃO conseguirá chamar esta API (CORS). Defina o endereço do site.")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_methods=["GET","POST","PATCH","DELETE"], allow_headers=["*"])

SCHEMA = """
CREATE TABLE IF NOT EXISTS modelos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, nome TEXT NOT NULL UNIQUE,
  cor TEXT NOT NULL DEFAULT '-', lente TEXT NOT NULL DEFAULT '-', material TEXT NOT NULL DEFAULT 'Acetato',
  tamanho TEXT NOT NULL DEFAULT '52 · 20 · 145 mm', protecao TEXT NOT NULL DEFAULT 'UV400',
  cor_hex TEXT NOT NULL DEFAULT '#0B0B0C', lente_hex TEXT NOT NULL DEFAULT '#3b3b40');
CREATE TABLE IF NOT EXISTS pedidos(
  id INTEGER PRIMARY KEY AUTOINCREMENT, numero TEXT NOT NULL UNIQUE, email TEXT NOT NULL, cpf_hash TEXT,
  cliente TEXT, data_compra TEXT NOT NULL, criado_em TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS garantias(
  id INTEGER PRIMARY KEY AUTOINCREMENT, pedido_id INTEGER NOT NULL REFERENCES pedidos(id),
  modelo_id INTEGER REFERENCES modelos(id), produto TEXT NOT NULL, serial TEXT NOT NULL UNIQUE, vid TEXT NOT NULL UNIQUE,
  status TEXT NOT NULL DEFAULT 'pendente' CHECK(status IN ('pendente','ativa','revogada')),
  valida_ate TEXT NOT NULL, ativada_em TEXT, ip TEXT, nota TEXT);
CREATE INDEX IF NOT EXISTS ix_g_pedido ON garantias(pedido_id);
CREATE INDEX IF NOT EXISTS ix_g_status ON garantias(status);
"""
UNIT_SQL = ("SELECT g.*, p.numero, p.email, p.cliente, p.data_compra, m.nome AS m_nome, m.cor AS m_cor, m.lente AS m_lente, "
            "m.material AS m_material, m.tamanho AS m_tamanho, m.protecao AS m_protecao, m.cor_hex AS m_hex, m.lente_hex AS m_lh "
            "FROM garantias g JOIN pedidos p ON p.id=g.pedido_id LEFT JOIN modelos m ON m.id=g.modelo_id")

@contextmanager
def db():
    os.makedirs(os.path.dirname(os.path.abspath(DB_PATH)), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=15); conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON"); conn.execute("PRAGMA journal_mode=WAL")
    try:
        yield conn; conn.commit()
    except Exception:
        conn.rollback(); raise
    finally: conn.close()

admin, seed_usuario = instalar(app, db, "admin", TOKEN_SECRET, TOKEN_TTL, ADMIN_USER, ADMIN_PASSWORD, ADMIN_KEY, log)

@app.on_event("startup")
def _init():
    with db() as c:
        c.executescript(SCHEMA)
        if "modelo_id" not in [r["name"] for r in c.execute("PRAGMA table_info(garantias)")]:
            c.execute("ALTER TABLE garantias ADD COLUMN modelo_id INTEGER REFERENCES modelos(id)")
        if not c.execute("SELECT 1 FROM modelos LIMIT 1").fetchone():
            c.executemany("INSERT INTO modelos(nome,cor,lente,cor_hex,lente_hex) VALUES(?,?,?,?,?)", DEFAULT_MODELOS)
    seed_usuario()
    push()   # sincroniza tudo com o backend de verificação ao subir

# ---------- utilidades ----------
def now_iso(): return datetime.now(timezone.utc).isoformat(timespec="seconds")
def add_months(d: date, n: int) -> date:
    m = d.month - 1 + n; y, m = d.year + m // 12, m % 12 + 1
    return date(y, m, min(d.day, calendar.monthrange(y, m)[1]))
def norm_pedido(v): return v.strip().lstrip("#").strip()
def norm_email(v): return v.strip().lower()
def only_digits(v): return "".join(ch for ch in v if ch.isdigit())
def cpf_hash(cpf): return hmac.new(PEPPER, only_digits(cpf).encode(), hashlib.sha256).hexdigest()
def valid_email(v): return "@" in v and "." in v.split("@")[-1] and " " not in v and len(v) <= 254
ALPHA = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
def new_vid(c):
    while True:
        v = "RKO-" + "".join(secrets.choice(ALPHA) for _ in range(4)) + "-" + "".join(secrets.choice(ALPHA) for _ in range(4))
        if not c.execute("SELECT 1 FROM garantias WHERE vid=?", (v,)).fetchone(): return v
def new_serial(c):
    return f"RK-{datetime.now().year}-{c.execute('SELECT COALESCE(MAX(id),0)+1 FROM garantias').fetchone()[0]:05d}"

def modelo_dict(r):
    return {"n": r["m_nome"] or "Modelo não definido", "cor": r["m_cor"] or "-", "lente": r["m_lente"] or "-",
            "material": r["m_material"] or "-", "tam": r["m_tamanho"] or "-", "uv": r["m_protecao"] or "-",
            "hex": r["m_hex"] or "#555555", "lh": r["m_lh"] or "#777777"}
def unit_public(r):
    return {"serial": r["serial"], "vid": r["vid"], "produto": r["produto"], "status": r["status"],
            "ativada_em": r["ativada_em"], "valida_ate": r["valida_ate"], "modelo": modelo_dict(r)}
def v_payload(r):   # SEM dados pessoais: é o que vai para o backend de verificação
    return {**unit_public(r)}
def admin_row(r):
    return {"numero": r["numero"], "cliente": r["cliente"], "email": r["email"], "data_compra": r["data_compra"],
            "produto": r["produto"], "modelo_id": r["modelo_id"], "modelo": r["m_nome"], "serial": r["serial"], "vid": r["vid"],
            "status": r["status"], "ativada_em": r["ativada_em"], "valida_ate": r["valida_ate"], "nota": r["nota"]}

# ---------- sincronização com o backend de verificação ----------
SYNC = {"configurado": bool(VERIF_URL), "ultimo_ok": None, "ultimo_erro": None, "enviadas": 0}
def _post_sync(units):
    if not VERIF_URL or not units: return
    try:
        for i in range(0, len(units), 200):
            req = urllib.request.Request(VERIF_URL + "/api/interno/sincronizar", method="POST",
                data=json.dumps({"unidades": units[i:i+200]}).encode(),
                headers={"Content-Type": "application/json", "X-Sync-Key": SYNC_KEY})
            urllib.request.urlopen(req, timeout=10).read()
        SYNC.update(ultimo_ok=now_iso(), ultimo_erro=None); SYNC["enviadas"] += len(units)
    except Exception as e:
        SYNC["ultimo_erro"] = f"{now_iso()} — {e}"; log.error("Falha ao sincronizar: %s", e)

def push(where="", args=(), wait=False):
    if not VERIF_URL: return
    with db() as c: rows = c.execute(UNIT_SQL + (f" WHERE {where}" if where else ""), args).fetchall()
    units = [v_payload(r) for r in rows]
    if wait: _post_sync(units)
    elif units: threading.Thread(target=_post_sync, args=(units,), daemon=True).start()

def push_in(col, vals):
    vals = list(vals)
    for i in range(0, len(vals), 500):
        ch = vals[i:i+500]; push(f"{col} IN ({','.join('?'*len(ch))})", ch)

# ---------- e-mail ----------
def send_confirmation(to, gs):
    host = os.getenv("SMTP_HOST")
    if not host: return
    try:
        linhas = "\n\n".join(f"{g['modelo']['n']} · {g['modelo']['cor']} · lente {g['modelo']['lente']}\n  Nº de série: {g['serial']}\n  ID de validação: {g['vid']}\n  Válida até: {g['valida_ate']}\n  Verificar: {FRONTEND_URL}/#/verificar/{g['vid']}" for g in gs)
        msg = EmailMessage(); msg["Subject"] = f"Sua garantia está ativa — Certificado nº {gs[0]['vid']}"
        msg["From"] = os.getenv("SMTP_FROM", "ROKO IKIGAI STUDIO <garantia@rokoikigai.com>"); msg["To"] = to
        msg.set_content("Olá!\n\nSua garantia de 12 meses está ativa. Guarde este e-mail junto à nota fiscal.\n\n" + linhas +
                        "\n\nPara acionar a garantia, responda este e-mail ou chame @rookoikigai informando o ID de validação.\n\nCoastal purpose. Made with ikigai.\n— ROKO IKIGAI STUDIO")
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as s:
            s.starttls()
            if os.getenv("SMTP_USER"): s.login(os.getenv("SMTP_USER"), os.getenv("SMTP_PASS", ""))
            s.send_message(msg)
    except Exception as e: log.error("Falha ao enviar e-mail: %s", e)

# ---------- limite de tentativas ----------
_hits: dict = {}
def client_ip(req):
    if TRUST_PROXY and req.headers.get("x-forwarded-for"): return req.headers["x-forwarded-for"].split(",")[0].strip()
    return req.client.host if req.client else "?"
def rate_limit(req, limit=10, window=600):
    ip, t = client_ip(req), time.time(); arr = [x for x in _hits.get(ip, []) if t - x < window]
    if len(arr) >= limit: raise HTTPException(429, "Muitas tentativas. Aguarde alguns minutos e tente novamente.")
    arr.append(t); _hits[ip] = arr

# ---------- pedidos ----------
class PedidoIn(BaseModel):
    numero: str = Field(min_length=1, max_length=40)
    email: str
    cpf: Optional[str] = None
    cliente: Optional[str] = None
    data_compra: date
    produto: str = DEFAULT_PRODUCT
    modelo_id: Optional[int] = None
    quantidade: int = Field(default=1, ge=1, le=20)

def create_pedido(c, p: PedidoIn):
    numero, email = norm_pedido(p.numero), norm_email(p.email)
    if not valid_email(email): raise ValueError("e-mail inválido")
    if c.execute("SELECT 1 FROM pedidos WHERE numero=?", (numero,)).fetchone(): raise FileExistsError("pedido já cadastrado")
    mid = p.modelo_id or (c.execute("SELECT MIN(id) FROM modelos").fetchone()[0])
    if mid is None or not c.execute("SELECT 1 FROM modelos WHERE id=?", (mid,)).fetchone(): raise ValueError("modelo inexistente")
    h = cpf_hash(p.cpf) if p.cpf and len(only_digits(p.cpf)) == 11 else None
    cur = c.execute("INSERT INTO pedidos(numero,email,cpf_hash,cliente,data_compra,criado_em) VALUES(?,?,?,?,?,?)",
                    (numero, email, h, p.cliente, p.data_compra.isoformat(), now_iso()))
    validade = add_months(p.data_compra, MONTHS).isoformat(); un = []
    for _ in range(p.quantidade):
        s, v = new_serial(c), new_vid(c)
        c.execute("INSERT INTO garantias(pedido_id,modelo_id,produto,serial,vid,valida_ate) VALUES(?,?,?,?,?,?)", (cur.lastrowid, mid, p.produto, s, v, validade))
        un.append({"serial": s, "vid": v})
    return {"numero": numero, "email": email, "data_compra": p.data_compra.isoformat(), "valida_ate": validade, "modelo_id": mid, "unidades": un}

# ---------- público: ativação ----------
class ValidarIn(BaseModel):
    pedido: str = Field(min_length=1, max_length=40)
    email: Optional[str] = None
    cpf: Optional[str] = None

@app.post("/api/validar", tags=["Público"])
def validar(body: ValidarIn, req: Request, bg: BackgroundTasks):
    rate_limit(req)
    if not body.email and not body.cpf: raise HTTPException(422, "Informe o e-mail ou CPF da compra.")
    nf = HTTPException(404, "Não encontramos uma compra com esses dados. Confira o número do pedido e o e-mail.")
    with db() as c:
        p = c.execute("SELECT * FROM pedidos WHERE numero=?", (norm_pedido(body.pedido),)).fetchone()
        if not p: raise nf
        ok = (body.email and hmac.compare_digest(norm_email(body.email), p["email"])) or \
             (body.cpf and p["cpf_hash"] and hmac.compare_digest(cpf_hash(body.cpf), p["cpf_hash"]))
        if not ok: raise nf
        Q = UNIT_SQL + " WHERE g.pedido_id=? ORDER BY g.id"
        rows = c.execute(Q, (p["id"],)).fetchall()
        if all(r["status"] == "revogada" for r in rows): raise HTTPException(403, "Esta garantia não está disponível. Fale com a ROKO IKIGAI STUDIO.")
        pend = [r for r in rows if r["status"] == "pendente"]; ja = not pend
        if pend:
            if date.today().isoformat() > pend[0]["valida_ate"]: raise HTTPException(410, "O prazo de garantia desta compra já expirou.")
            ids = [r["id"] for r in pend]
            c.executemany("UPDATE garantias SET status='ativa', ativada_em=?, ip=? WHERE id=?", [(now_iso(), client_ip(req), i) for i in ids])
            rows = c.execute(Q, (p["id"],)).fetchall()
            bg.add_task(push_in, "g.id", ids)
            bg.add_task(send_confirmation, p["email"], [unit_public(r) for r in rows if r["status"] == "ativa"])
        return {"ja_ativada": ja, "email": p["email"],
                "garantias": [unit_public(r) for r in rows if r["status"] != "revogada"]}

# ---------- admin ----------
A = [Depends(admin)]   # login (/api/auth/login) ou chave de serviço (X-API-Key)

@app.post("/api/admin/pedidos", tags=["Admin · Pedidos"], dependencies=A, status_code=201)
def admin_criar_pedido(p: PedidoIn):
    try:
        with db() as c: r = create_pedido(c, p)
    except FileExistsError as e: raise HTTPException(409, str(e))
    except ValueError as e: raise HTTPException(422, str(e))
    push("p.numero=?", (r["numero"],)); return r

def _parse_date(s):
    for f in ("%Y-%m-%d", "%d/%m/%Y"):
        try: return datetime.strptime(s.strip(), f).date()
        except ValueError: pass
    raise ValueError(f"data inválida: {s}")

@app.post("/api/admin/pedidos/importar", tags=["Admin · Pedidos"], dependencies=A)
async def admin_importar(arquivo: UploadFile = File(...)):
    """CSV: numero,email,data_compra (+ cpf,cliente,produto,modelo,quantidade). 'modelo' = nome do modelo do catálogo."""
    txt = (await arquivo.read()).decode("utf-8-sig"); l0 = txt.splitlines()[0]
    sep = ";" if l0.count(";") > l0.count(",") else ","; criados, ign, erros, nums = 0, [], [], []
    with db() as c:
        for i, r in enumerate(csv.DictReader(io.StringIO(txt), delimiter=sep), start=2):
            r = {(k or "").strip().lower(): (v or "").strip() for k, v in r.items()}
            try:
                mid = None
                if r.get("modelo"):
                    m = c.execute("SELECT id FROM modelos WHERE lower(nome)=lower(?)", (r["modelo"],)).fetchone()
                    if not m: raise ValueError(f"modelo não encontrado: {r['modelo']}")
                    mid = m["id"]
                out = create_pedido(c, PedidoIn(numero=r["numero"], email=r["email"], cpf=r.get("cpf") or None, cliente=r.get("cliente") or None,
                    data_compra=_parse_date(r["data_compra"]), produto=r.get("produto") or DEFAULT_PRODUCT, modelo_id=mid, quantidade=int(r.get("quantidade") or 1)))
                criados += 1; nums.append(out["numero"])
            except FileExistsError: ign.append(r.get("numero"))
            except Exception as e: erros.append({"linha": i, "erro": str(e)})
    push_in("p.numero", nums)
    return {"criados": criados, "ignorados_duplicados": ign, "erros": erros}

class PedidoPatch(BaseModel):
    email: Optional[str] = None; cliente: Optional[str] = None; data_compra: Optional[date] = None
    produto: Optional[str] = None; modelo_id: Optional[int] = None

@app.patch("/api/admin/pedidos/{numero}", tags=["Admin · Pedidos"], dependencies=A)
def admin_editar_pedido(numero: str, b: PedidoPatch):
    with db() as c:
        p = c.execute("SELECT * FROM pedidos WHERE numero=?", (norm_pedido(numero),)).fetchone()
        if not p: raise HTTPException(404, "Pedido não encontrado.")
        email = norm_email(b.email) if b.email else p["email"]
        if not valid_email(email): raise HTTPException(422, "E-mail inválido.")
        cliente = b.cliente if b.cliente is not None else p["cliente"]
        dc = b.data_compra.isoformat() if b.data_compra else p["data_compra"]
        c.execute("UPDATE pedidos SET email=?, cliente=?, data_compra=? WHERE id=?", (email, cliente, dc, p["id"]))
        if b.data_compra: c.execute("UPDATE garantias SET valida_ate=? WHERE pedido_id=?", (add_months(b.data_compra, MONTHS).isoformat(), p["id"]))
        if b.produto: c.execute("UPDATE garantias SET produto=? WHERE pedido_id=?", (b.produto.strip(), p["id"]))
        if b.modelo_id is not None:
            if not c.execute("SELECT 1 FROM modelos WHERE id=?", (b.modelo_id,)).fetchone(): raise HTTPException(422, "Modelo inexistente.")
            c.execute("UPDATE garantias SET modelo_id=? WHERE pedido_id=?", (b.modelo_id, p["id"]))
        rows = c.execute(UNIT_SQL + " WHERE g.pedido_id=? ORDER BY g.id", (p["id"],)).fetchall()
    push("p.numero=?", (p["numero"],))
    return {"numero": p["numero"], "email": email, "cliente": cliente, "data_compra": dc, "garantias": [unit_public(r) for r in rows]}

def _post_remove(vids):
    """Pede ao Backend de Verificação para esquecer estas peças (falha = exceção)."""
    for i in range(0, len(vids), 200):
        req = urllib.request.Request(VERIF_URL + "/api/interno/remover", method="POST", data=json.dumps({"vids": vids[i:i+200]}).encode(),
                                     headers={"Content-Type": "application/json", "X-Sync-Key": SYNC_KEY})
        urllib.request.urlopen(req, timeout=10).read()

@app.delete("/api/admin/pedidos/{numero}", tags=["Admin · Pedidos"], dependencies=A)
def admin_excluir_pedido(numero: str):
    """Exclui o pedido e TODAS as suas garantias (inclusive já ativadas) e remove as peças do Backend de Verificação.
    Se o Backend de Verificação não responder, nada é excluído (evita peça 'fantasma' continuar autêntica)."""
    with db() as c:
        p = c.execute("SELECT * FROM pedidos WHERE numero=?", (norm_pedido(numero),)).fetchone()
        if not p: raise HTTPException(404, "Pedido não encontrado.")
        vids = [g["vid"] for g in c.execute("SELECT vid FROM garantias WHERE pedido_id=?", (p["id"],))]
    verif = "não configurado"
    if VERIF_URL and vids:
        try: _post_remove(vids); verif = "removidas"
        except Exception as e:
            log.error("Falha ao remover peças do backend de verificação: %s", e)
            raise HTTPException(502, "Não consegui remover as peças do Backend de Verificação (ele está no ar? SYNC_KEY igual nos dois?). O pedido NÃO foi excluído; tente de novo.")
    with db() as c:
        c.execute("DELETE FROM garantias WHERE pedido_id=?", (p["id"],)); c.execute("DELETE FROM pedidos WHERE id=?", (p["id"],))
    log.info("Pedido %s excluído (%d garantia(s))", p["numero"], len(vids))
    return {"ok": True, "numero": p["numero"], "garantias_removidas": len(vids), "verificacao": verif}

@app.get("/api/admin/garantias", tags=["Admin · Garantias"], dependencies=A)
def admin_listar(status: Optional[str] = None, q: Optional[str] = None, limit: int = Query(50, le=500), offset: int = 0):
    sql, args = UNIT_SQL + " WHERE 1=1", []
    if status: sql += " AND g.status=?"; args.append(status)
    if q:
        sql += " AND (p.numero LIKE ? OR p.email LIKE ? OR p.cliente LIKE ? OR g.serial LIKE ? OR g.vid LIKE ? OR m.nome LIKE ?)"; args += [f"%{q}%"] * 6
    sql += " ORDER BY g.id DESC LIMIT ? OFFSET ?"; args += [limit, offset]
    with db() as c: return [admin_row(r) for r in c.execute(sql, args).fetchall()]

class GarantiaPatch(BaseModel):
    status: Optional[str] = Field(None, pattern="^(pendente|ativa|revogada)$")
    nota: Optional[str] = None
    modelo_id: Optional[int] = None

@app.patch("/api/admin/garantias/{vid}", tags=["Admin · Garantias"], dependencies=A)
def admin_status(vid: str, b: GarantiaPatch):
    with db() as c:
        g = c.execute("SELECT * FROM garantias WHERE vid=?", (vid.upper(),)).fetchone()
        if not g: raise HTTPException(404, "Garantia não encontrada.")
        if b.modelo_id is not None and not c.execute("SELECT 1 FROM modelos WHERE id=?", (b.modelo_id,)).fetchone(): raise HTTPException(422, "Modelo inexistente.")
        st = b.status or g["status"]; ativ = g["ativada_em"] or (now_iso() if st == "ativa" else None)
        c.execute("UPDATE garantias SET status=?, nota=COALESCE(?,nota), ativada_em=?, modelo_id=COALESCE(?,modelo_id) WHERE id=?", (st, b.nota, ativ, b.modelo_id, g["id"]))
        r = c.execute(UNIT_SQL + " WHERE g.id=?", (g["id"],)).fetchone()
    push("g.id=?", (g["id"],)); return unit_public(r)

# ----- catálogo de modelos -----
class ModeloIn(BaseModel):
    nome: str = Field(min_length=1, max_length=80)
    cor: str = "-"; lente: str = "-"; material: str = "Acetato"; tamanho: str = "52 · 20 · 145 mm"; protecao: str = "UV400"
    cor_hex: str = Field("#0B0B0C", pattern=r"^#[0-9a-fA-F]{6}$"); lente_hex: str = Field("#3b3b40", pattern=r"^#[0-9a-fA-F]{6}$")
class ModeloPatch(BaseModel):
    nome: Optional[str] = None; cor: Optional[str] = None; lente: Optional[str] = None; material: Optional[str] = None
    tamanho: Optional[str] = None; protecao: Optional[str] = None
    cor_hex: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$"); lente_hex: Optional[str] = Field(None, pattern=r"^#[0-9a-fA-F]{6}$")

@app.get("/api/admin/modelos", tags=["Admin · Catálogo"], dependencies=A)
def modelos_listar():
    with db() as c:
        return [dict(r) for r in c.execute("SELECT m.*, (SELECT COUNT(*) FROM garantias g WHERE g.modelo_id=m.id) AS em_uso FROM modelos m ORDER BY m.id")]

@app.post("/api/admin/modelos", tags=["Admin · Catálogo"], dependencies=A, status_code=201)
def modelos_criar(m: ModeloIn):
    try:
        with db() as c:
            cur = c.execute("INSERT INTO modelos(nome,cor,lente,material,tamanho,protecao,cor_hex,lente_hex) VALUES(?,?,?,?,?,?,?,?)",
                            (m.nome.strip(), m.cor, m.lente, m.material, m.tamanho, m.protecao, m.cor_hex, m.lente_hex))
            return {"id": cur.lastrowid, **m.model_dump()}
    except sqlite3.IntegrityError: raise HTTPException(409, "Já existe um modelo com esse nome.")

@app.patch("/api/admin/modelos/{mid}", tags=["Admin · Catálogo"], dependencies=A)
def modelos_editar(mid: int, m: ModeloPatch):
    campos = {k: (v.strip() if isinstance(v, str) else v) for k, v in m.model_dump().items() if v is not None}
    if not campos: raise HTTPException(422, "Nada para alterar.")
    try:
        with db() as c:
            if not c.execute("SELECT 1 FROM modelos WHERE id=?", (mid,)).fetchone(): raise HTTPException(404, "Modelo não encontrado.")
            c.execute(f"UPDATE modelos SET {', '.join(k + '=?' for k in campos)} WHERE id=?", [*campos.values(), mid])
            r = dict(c.execute("SELECT * FROM modelos WHERE id=?", (mid,)).fetchone())
    except sqlite3.IntegrityError: raise HTTPException(409, "Já existe um modelo com esse nome.")
    push("g.modelo_id=?", (mid,)); return r

@app.delete("/api/admin/modelos/{mid}", tags=["Admin · Catálogo"], dependencies=A)
def modelos_excluir(mid: int):
    with db() as c:
        n = c.execute("SELECT COUNT(*) FROM garantias WHERE modelo_id=?", (mid,)).fetchone()[0]
        if n: raise HTTPException(409, f"Modelo em uso por {n} garantia(s). Troque o modelo delas antes de excluir.")
        c.execute("DELETE FROM modelos WHERE id=?", (mid,))
    return {"ok": True}

# ----- verificação (estado da sincronização) -----
@app.get("/api/admin/verificacao", tags=["Admin · Verificação"], dependencies=A)
def verif_estado(): return {**SYNC, "url_interna": VERIF_URL}

@app.post("/api/admin/verificacao/sincronizar", tags=["Admin · Verificação"], dependencies=A)
def verif_sync():
    if not VERIF_URL: raise HTTPException(409, "VERIF_URL não configurada.")
    push(wait=True); return {**SYNC, "url_interna": VERIF_URL}

# ----- estatísticas, exportação, certificados -----
@app.get("/api/admin/estatisticas", tags=["Admin · Garantias"], dependencies=A)
def admin_stats():
    with db() as c:
        por = {r["status"]: r["n"] for r in c.execute("SELECT status, COUNT(*) n FROM garantias GROUP BY status")}
        ped = c.execute("SELECT COUNT(*) FROM pedidos").fetchone()[0]
        d30 = c.execute("SELECT COUNT(*) FROM garantias WHERE ativada_em >= datetime('now','-30 days')").fetchone()[0]
    t = sum(por.values())
    return {"pedidos": ped, "unidades": t, "pendentes": por.get("pendente", 0), "ativas": por.get("ativa", 0), "revogadas": por.get("revogada", 0),
            "ativacoes_ultimos_30_dias": d30, "taxa_ativacao": round(por.get("ativa", 0) / t, 3) if t else 0}

@app.get("/api/admin/exportar.csv", tags=["Admin · Garantias"], dependencies=A)
def admin_export():
    buf = io.StringIO(); w = csv.writer(buf)
    w.writerow(["pedido","cliente","email","data_compra","produto","modelo","serial","vid","status","ativada_em","valida_ate","nota"])
    with db() as c:
        for r in c.execute(UNIT_SQL + " ORDER BY g.id"):
            w.writerow([r["numero"], r["cliente"], r["email"], r["data_compra"], r["produto"], r["m_nome"], r["serial"], r["vid"], r["status"], r["ativada_em"], r["valida_ate"], r["nota"]])
    return StreamingResponse(iter(["\ufeff" + buf.getvalue()]), media_type="text/csv", headers={"Content-Disposition": "attachment; filename=garantias.csv"})

def _units(rows):
    return [{"produto": r["produto"], "serial": r["serial"], "vid": r["vid"], "data_compra": r["data_compra"], "valida_ate": r["valida_ate"], "modelo": modelo_dict(r)} for r in rows]
def _pdf(rows, nome): return Response(build_pdf(_units(rows), FRONTEND_URL), media_type="application/pdf", headers={"Content-Disposition": f"inline; filename={nome}"})

@app.get("/api/admin/garantias/{vid}/certificado.pdf", tags=["Admin · Certificados"], dependencies=A)
def cert_unidade(vid: str):
    with db() as c: rows = c.execute(UNIT_SQL + " WHERE g.status!='revogada' AND g.vid=?", (vid.upper(),)).fetchall()
    if not rows: raise HTTPException(404, "Garantia não encontrada ou revogada.")
    return _pdf(rows, f"certificado-{vid.upper()}.pdf")

@app.get("/api/admin/pedidos/{numero}/certificados.pdf", tags=["Admin · Certificados"], dependencies=A)
def cert_pedido(numero: str):
    with db() as c: rows = c.execute(UNIT_SQL + " WHERE g.status!='revogada' AND p.numero=? ORDER BY g.id", (norm_pedido(numero),)).fetchall()
    if not rows: raise HTTPException(404, "Pedido não encontrado ou sem garantias válidas.")
    return _pdf(rows, f"certificados-{norm_pedido(numero)}.pdf")

# ---------- raiz / saúde ----------
@app.get("/", include_in_schema=False)
def raiz(): return {"servico": "ROKO IKIGAI — Backend Admin", "docs": "/docs", "saude": "/saude"}
@app.get("/saude", include_in_schema=False)
def saude(): return {"ok": True, "frontend_url": FRONTEND_URL}

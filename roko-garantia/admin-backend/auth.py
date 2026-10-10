"""Autenticação (somente biblioteca padrão): senha com PBKDF2-SHA256 e token assinado (JWT HS256).
Cada backend usa seu próprio segredo e 'aud', então o token de um não vale no outro."""
import base64, hashlib, hmac, json, os, secrets, time
from datetime import datetime, timezone
from typing import Optional
from fastapi import Depends, HTTPException, Request
from fastapi.security import APIKeyHeader, HTTPBearer
from pydantic import BaseModel, Field

ITER = 200_000
def hash_senha(s: str) -> str:
    salt = secrets.token_bytes(16); h = hashlib.pbkdf2_hmac("sha256", s.encode(), salt, ITER)
    return f"pbkdf2${ITER}${base64.b64encode(salt).decode()}${base64.b64encode(h).decode()}"
def verifica_senha(s: str, stored: str) -> bool:
    try:
        _, it, salt, h = stored.split("$")
        return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", s.encode(), base64.b64decode(salt), int(it)), base64.b64decode(h))
    except Exception: return False
_DUMMY = hash_senha(secrets.token_urlsafe(8))   # evita revelar, pelo tempo de resposta, se o usuário existe

def _b64(b: bytes) -> str: return base64.urlsafe_b64encode(b).rstrip(b"=").decode()
def _unb64(s: str) -> bytes: return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))
def _sig(secret: str, msg: str) -> str: return _b64(hmac.new(secret.encode(), msg.encode(), hashlib.sha256).digest())
def criar_token(secret, sub, aud, ttl_min):
    now = int(time.time()); exp = now + ttl_min * 60
    head = _b64(json.dumps({"alg": "HS256", "typ": "JWT"}, separators=(",", ":")).encode())
    body = _b64(json.dumps({"sub": sub, "aud": aud, "iat": now, "exp": exp}, separators=(",", ":")).encode())
    return f"{head}.{body}.{_sig(secret, head + '.' + body)}", exp
def ler_token(secret, token, aud) -> Optional[str]:
    try:
        head, body, sig = token.split(".")
        if not hmac.compare_digest(_sig(secret, head + "." + body), sig): return None
        p = json.loads(_unb64(body))
        if p.get("aud") != aud or p.get("exp", 0) < time.time(): return None
        return p.get("sub")
    except Exception: return None

def instalar(app, db, aud, secret, ttl_min, user, password, admin_key, log):
    """Cria rotas /api/auth/*, devolve (dependência 'admin', função 'seed' que cria a tabela e o usuário inicial)."""
    key_h = APIKeyHeader(name="X-API-Key", auto_error=False); bearer = HTTPBearer(auto_error=False); falhas = {}
    class LoginIn(BaseModel):
        usuario: str = Field(min_length=1, max_length=60); senha: str = Field(min_length=1, max_length=200)
    class SenhaIn(BaseModel):
        atual: str = Field(max_length=200); nova: str = Field(min_length=8, max_length=200)
    def ip(req: Request):
        if os.getenv("TRUST_PROXY", "0") == "1" and req.headers.get("x-forwarded-for"): return req.headers["x-forwarded-for"].split(",")[0].strip()
        return req.client.host if req.client else "?"
    def seed():
        with db() as c:
            c.execute("CREATE TABLE IF NOT EXISTS usuarios(id INTEGER PRIMARY KEY AUTOINCREMENT, usuario TEXT NOT NULL UNIQUE, senha_hash TEXT NOT NULL, criado_em TEXT NOT NULL)")
            if not c.execute("SELECT 1 FROM usuarios WHERE usuario=?", (user,)).fetchone():
                pw = password or secrets.token_urlsafe(10)
                if not password: log.warning("Senha do usuário '%s' não definida no .env. Senha temporária: %s", user, pw)
                c.execute("INSERT INTO usuarios(usuario,senha_hash,criado_em) VALUES(?,?,?)", (user, hash_senha(pw), datetime.now(timezone.utc).isoformat(timespec="seconds")))
    def usuario_atual(cred=Depends(bearer)):
        u = ler_token(secret, cred.credentials, aud) if cred else None
        if not u: raise HTTPException(401, "Sessão inválida ou expirada.")
        return u
    def admin(k: Optional[str] = Depends(key_h), cred=Depends(bearer)):
        if cred and ler_token(secret, cred.credentials, aud): return
        if k and hmac.compare_digest(k, admin_key): return   # chave de serviço (scripts/integrações)
        raise HTTPException(401, "Não autorizado.")
    @app.post("/api/auth/login", tags=["Autenticação"])
    def login(b: LoginIn, req: Request):
        i, t = ip(req), time.time(); arr = [x for x in falhas.get(i, []) if t - x < 600]
        if len(arr) >= 5: raise HTTPException(429, "Muitas tentativas de login. Aguarde 10 minutos.")
        with db() as c: r = c.execute("SELECT * FROM usuarios WHERE usuario=?", (b.usuario.strip(),)).fetchone()
        ok = verifica_senha(b.senha, r["senha_hash"] if r else _DUMMY) and r is not None
        if not ok:
            arr.append(t); falhas[i] = arr; raise HTTPException(401, "Usuário ou senha inválidos.")
        falhas.pop(i, None); tok, exp = criar_token(secret, r["usuario"], aud, ttl_min)
        return {"token": tok, "tipo": "Bearer", "expira_em": exp, "usuario": r["usuario"]}
    @app.get("/api/auth/eu", tags=["Autenticação"])
    def eu(u: str = Depends(usuario_atual)): return {"usuario": u}
    @app.post("/api/auth/trocar-senha", tags=["Autenticação"])
    def trocar(b: SenhaIn, u: str = Depends(usuario_atual)):
        with db() as c:
            r = c.execute("SELECT * FROM usuarios WHERE usuario=?", (u,)).fetchone()
            if not r or not verifica_senha(b.atual, r["senha_hash"]): raise HTTPException(400, "Senha atual incorreta.")
            c.execute("UPDATE usuarios SET senha_hash=? WHERE id=?", (hash_senha(b.nova), r["id"]))
        return {"ok": True}
    return admin, seed

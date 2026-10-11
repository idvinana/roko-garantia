"""ROKO IKIGAI STUDIO — SERVIÇO ÚNICO: roda o Backend Admin e o Backend de Verificação no mesmo serviço (1 hospedagem + 1 disco).

Cada um continua separado: código, banco de dados, login, chaves e variáveis próprios.
  https://SEU-SERVICO/admin/...  → Backend Admin        (config.js: ADMIN_API = https://SEU-SERVICO/admin)
  https://SEU-SERVICO/verif/...  → Backend de Verificação (config.js: VERIF_API = https://SEU-SERVICO/verif)

Variáveis de ambiente: as mesmas dos dois backends (veja admin-backend/.env.example e verificacao-backend/.env.example), mais:
  DATA_DIR   pasta do disco persistente (ex.: /data). Os bancos ficam em DATA_DIR/admin.db e DATA_DIR/verificacao.db
  VERIF_URL  (opcional) por padrão o Admin fala com a Verificação por dentro, em http://127.0.0.1:PORTA/verif
Comando: uvicorn app:app --host 0.0.0.0 --port $PORT   (a partir da pasta servico-unico)
"""
import asyncio, importlib.util, inspect, logging, os, sys, threading, time
from contextlib import asynccontextmanager
from fastapi import FastAPI

log = logging.getLogger("roko.unico")
AQUI = os.path.dirname(os.path.abspath(__file__))
RAIZ = os.path.dirname(AQUI)

# --- caminhos dos bancos (uma pasta de disco para os dois) e endereço interno da Verificação ---
DATA_DIR = os.getenv("DATA_DIR", "").strip()
if DATA_DIR:
    os.makedirs(DATA_DIR, exist_ok=True)
    os.environ.setdefault("DB_PATH", os.path.join(DATA_DIR, "admin.db"))
    os.environ.setdefault("VERIF_DB_PATH", os.path.join(DATA_DIR, "verificacao.db"))
else:
    log.warning("DATA_DIR não definido: os bancos ficam dentro do projeto e SOMEM quando o serviço reinicia (a menos que haja disco persistente).")
os.environ.setdefault("VERIF_URL", f"http://127.0.0.1:{os.getenv('PORT', '8000')}/verif")


def _carregar(nome, pasta):
    """Importa o main.py de uma pasta com um nome próprio (os dois se chamam 'main' e usam um 'auth.py' cada)."""
    pasta = os.path.join(RAIZ, pasta); sys.path.insert(0, pasta)
    try:
        for m in ("auth", "certificado"): sys.modules.pop(m, None)
        spec = importlib.util.spec_from_file_location(nome, os.path.join(pasta, "main.py"))
        mod = importlib.util.module_from_spec(spec); sys.modules[nome] = mod; spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(pasta)

verif = _carregar("roko_verificacao", "verificacao-backend")
admin = _carregar("roko_admin", "admin-backend")


async def _rodar(handlers):
    for h in list(handlers):
        r = h()
        if inspect.isawaitable(r): await r

@asynccontextmanager
async def lifespan(_):
    # Apps montados não recebem 'startup' sozinhos: roda aqui (Verificação antes, pois o Admin sincroniza com ela).
    await _rodar(verif.app.router.on_startup); await _rodar(admin.app.router.on_startup)
    def _ressincroniza():   # o 1º envio do Admin ocorre antes do servidor aceitar conexões; repete assim que estiver no ar
        time.sleep(4); admin.push()
    threading.Thread(target=_ressincroniza, daemon=True).start()
    yield
    await _rodar(admin.app.router.on_shutdown); await _rodar(verif.app.router.on_shutdown)

app = FastAPI(title="ROKO IKIGAI — Serviço único", lifespan=lifespan, docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/admin", admin.app)
app.mount("/verif", verif.app)

@app.get("/", include_in_schema=False)
def raiz(): return {"servico": "ROKO IKIGAI — Serviço único", "admin": "/admin", "verificacao": "/verif", "saude": "/saude"}

@app.get("/saude", include_in_schema=False)
def saude(): return {"ok": True, "admin": "/admin/saude", "verificacao": "/verif/saude"}

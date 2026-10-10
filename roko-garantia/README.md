# ROKO IKIGAI STUDIO — Garantia de óculos

Três projetos **separados**:

```
 frontend/             site estático (HTML/CSS/JS) — nada de regra de negócio
      │  HTTP (CORS)
      ├──────────────► admin-backend/        API: pedidos · catálogo · garantias · ativação · certificados (:8000)
      │                        │  sync autenticado (X-Sync-Key), sem dados pessoais
      └──────────────► verificacao-backend/  API: autenticidade · registro de consultas (:8001)
```

- **frontend/** — telas: verificar autenticidade, ativar garantia e administração (pedidos, catálogo, garantias, verificações). Configure os endereços em `frontend/js/config.js`. Veja `frontend/README.md`.
- **admin-backend/** — API com os dados do negócio e do cliente (pedido, e-mail, CPF só em hash), catálogo de modelos e geração do certificado em PDF.
- **verificacao-backend/** — API com o mínimo para confirmar a peça (ID, série, modelo, status, validade; **sem nome, e-mail ou CPF**) e o registro de cada consulta (data, ID, resultado, origem, hash do IP).

A cada mudança (novo pedido, ativação, revogação, edição de modelo) o Admin envia a atualização ao Verificação. Se o Verificação estiver fora do ar, o painel mostra o erro e há o botão **Sincronizar agora**.

## Rodar (desenvolvimento)
```bash
./iniciar.sh        # Windows: iniciar.bat
```
Na primeira vez cria `admin-backend/.env` e `verificacao-backend/.env`. **Edite antes de usar**: `ADMIN_PASSWORD`, `VERIF_PASSWORD`, `TOKEN_SECRET`, `VERIF_TOKEN_SECRET`, `ADMIN_API_KEY`, `VERIF_ADMIN_KEY` e `SYNC_KEY` (a **mesma** `SYNC_KEY` nos dois).

| Onde | Endereço |
|---|---|
| Frontend | http://localhost:3000 |
| API Admin (documentação) | http://localhost:8000/docs |
| API Verificação (documentação) | http://localhost:8001/docs |

## Login (um por backend)
Cada backend tem **a sua página de login** e as suas credenciais, independentes:

| Página de login | Backend | Usuário/senha vêm de |
|---|---|---|
| `SEU-SITE/#/login/admin` | Backend Admin | `ADMIN_USER` / `ADMIN_PASSWORD` |
| `SEU-SITE/#/login/verificacao` | Backend de Verificação | `VERIF_USER` / `VERIF_PASSWORD` |

- A senha do `.env` só cria o usuário na primeira subida; o banco guarda apenas o **hash** (PBKDF2-SHA256). Depois, troque a senha em **Administração → Alterar senha**.
- O login devolve um **token assinado** com validade (`TOKEN_TTL_MIN`, padrão 8 h). O token de um backend **não vale** no outro. Defina `TOKEN_SECRET` e `VERIF_TOKEN_SECRET` fixos, senão as sessões caem a cada reinício.
- Proteção contra força bruta: após 5 senhas erradas, o IP fica bloqueado por 10 min.
- As chaves `ADMIN_API_KEY`/`VERIF_ADMIN_KEY` (header `X-API-Key`) continuam valendo só para scripts e integrações.
- Rotas: `POST /api/auth/login` · `GET /api/auth/eu` · `POST /api/auth/trocar-senha`.

## Produção
- Três publicações independentes, todas com HTTPS. Exemplo: site `rokoikigai.com` (frontend estático), API `api.rokoikigai.com` (Admin), `verifica.rokoikigai.com` (Verificação).
- **Backend Admin:** `FRONTEND_URL=https://rokoikigai.com` (vai nos QR e e-mails), `ALLOWED_ORIGINS=https://rokoikigai.com`, `VERIF_URL` = endereço que o Admin alcança (pode ser interno), `SYNC_KEY`.
- **Backend Verificação:** `ALLOWED_ORIGINS=https://rokoikigai.com`, a mesma `SYNC_KEY`.
- **Frontend:** `js/config.js` com os dois endereços das APIs.
- Cada backend usa um arquivo SQLite (`DB_PATH` / `VERIF_DB_PATH`): use disco persistente e faça backup.
- Os backends **não servem páginas**, só API. `TRUST_PROXY=1` atrás de proxy/Cloudflare. O acesso às rotas `/api/admin/*` exige login (token) ou a chave de serviço: guarde senhas e chaves com cuidado e, se possível, restrinja essas rotas por IP no proxy.

## Backend Admin — rotas (header `X-API-Key`)
Público: `POST /api/validar`.
Login: `POST /api/auth/login`. Admin: `POST/PATCH /api/admin/pedidos[/{n}]` · `POST /api/admin/pedidos/importar` (CSV) · `GET/POST/PATCH/DELETE /api/admin/modelos` · `GET /api/admin/garantias` · `PATCH /api/admin/garantias/{vid}` (status/modelo) · `GET /api/admin/pedidos/{n}/certificados.pdf` · `GET /api/admin/garantias/{vid}/certificado.pdf` · `GET /api/admin/verificacao` · `POST /api/admin/verificacao/sincronizar` · `GET /api/admin/exportar.csv` · `GET /api/admin/estatisticas`

## Backend Verificação — rotas
Público: `GET /api/verificar/{vid}?origem=manual|qr|foto|camera`.
Interno: `POST /api/interno/sincronizar` (header `X-Sync-Key`).
Login: `POST /api/auth/login`. Admin (token do login ou `X-API-Key` = `VERIF_ADMIN_KEY`): `GET /api/admin/estatisticas` · `/consultas` · `/unidades` · `/exportar-consultas.csv`.

## Catálogo e CSV
O catálogo vem com 4 modelos **de exemplo** (Atlantic Current, Golden Horizon, Endless Tide, Salt Ritual): edite ou exclua em **Administração → Catálogo**.
CSV de importação: `numero,email,data_compra` + opcionais `cpf,cliente,produto,modelo,quantidade` (`modelo` = nome do catálogo).

## Regras
Garantia = 12 meses da data da compra (90 dias legais + complemento contratual, CDC arts. 26 e 50). Ativar duas vezes não duplica. Erros de pedido/e-mail usam mensagem genérica. Limite de tentativas por IP. CPF só em hash. Revogada não ativa.

## Excluir pedido
No Backend Admin, o botão **Excluir pedido** (na tabela de pedidos) apaga o pedido e **todas** as garantias dele, inclusive as já ativadas, e também remove as peças do Backend de Verificação (QR Codes já impressos deixam de ser reconhecidos). Pede confirmação e não dá para desfazer.
- Se o Backend de Verificação estiver fora do ar (ou a `SYNC_KEY` for diferente), **nada é excluído** e o site avisa: assim nenhuma peça continua "autêntica" depois do pedido apagado. Tente de novo quando ele voltar.
- Peças cadastradas manualmente no Backend de Verificação não são afetadas.
- Para só cancelar a garantia mantendo o histórico, use **Revogar** em vez de excluir.
- API: `DELETE /api/admin/pedidos/{numero}` (login ou chave de serviço).

## Cadastro e edição de peças (Backend de Verificação)
Em **Backend de Verificação → Peças registradas** você pode **cadastrar, editar e excluir** peças direto no registro de autenticidade (ID, nº de série, status, modelo, cores, validade).
- **Cadastro manual:** deixe o ID vazio para gerar automaticamente (`RKO-XXXX-XXXX`). Serve para peças que não passaram pelo Backend Admin.
- **Travadas:** peça cadastrada ou editada aqui **não é sobrescrita** pela sincronização do Backend Admin. Para uma peça sincronizada, marque "Voltar a receber atualizações" ao editar se quiser desfazer a trava.
- **Excluir** só vale para peças cadastradas manualmente. Peça vinda do Backend Admin voltaria na próxima sincronização: mude o status para `revogada`.
- API: `POST /api/admin/unidades` · `PATCH /api/admin/unidades/{vid}` · `DELETE /api/admin/unidades/{vid}` (login ou chave de serviço).
- Bancos antigos são atualizados sozinhos na primeira subida.

## QR Codes e teste no celular
Os QR Codes dos certificados guardam o endereço do site (`FRONTEND_URL` do Backend Admin). Se ele for `localhost`, o QR **não abre no celular** (para o celular, "localhost" é ele mesmo).
- **Produção:** `FRONTEND_URL=https://seu-site.com` no `.env` do Backend Admin, e o mesmo endereço em `ALLOWED_ORIGINS` dos dois backends. Gere os certificados de novo: PDFs impressos com `localhost` não funcionam.
- **Teste em casa:** use o IP do computador na mesma rede Wi-Fi (ex.: `FRONTEND_URL=http://192.168.0.10:3000`), inclua-o em `ALLOWED_ORIGINS` e abra o site pelo celular nesse endereço. A câmera ao vivo só funciona em HTTPS; em HTTP use "Tirar foto do QR".
- O topo do site avisa em vermelho quando `FRONTEND_URL` ainda é `localhost`.

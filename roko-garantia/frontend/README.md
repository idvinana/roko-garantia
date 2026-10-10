# Frontend — ROKO IKIGAI STUDIO (site estático)

Projeto **separado** dos backends: só HTML, CSS e JavaScript (sem build, sem servidor próprio).
Ele conversa com os dois backends por HTTP:

| O que | Backend |
|---|---|
| Ativar garantia (cliente), pedidos, catálogo, garantias, certificados | **Backend Admin** |
| Verificar autenticidade (ID, QR, foto), registro de consultas | **Backend de Verificação** |

## Configurar
Edite **`js/config.js`**:
```js
window.RK_CONFIG = {
  ADMIN_API: "https://api.rokoikigai.com",      // Backend Admin
  VERIF_API: "https://verifica.rokoikigai.com", // Backend de Verificação
  FRONTEND_URL: ""                              // endereço público do site (QR). Vazio = endereço atual
};
```
No servidor de cada backend, o endereço do site precisa estar em `ALLOWED_ORIGINS` (CORS), e em `FRONTEND_URL` (Backend Admin) para os QR dos certificados.

## Rodar local
`python3 -m http.server 3000` dentro desta pasta (ou use `../iniciar.sh`) e abra http://localhost:3000.

## Publicar
Qualquer hospedagem estática: Netlify, Vercel, Cloudflare Pages, GitHub Pages ou Nginx. Use **HTTPS** (a câmera do verificador exige).
Os QR dos certificados usam rotas por hash, então não precisa configurar redirecionamentos:
- `https://SEU-SITE/#/verificar/RKO-XXXX-XXXX` → abre o verificador já consultando a peça
- `https://SEU-SITE/#/ativar` → ativação da garantia

## Estrutura
`index.html` · `css/style.css` · `js/config.js` (endereços) · `util.js` (chamadas às APIs) · `card.js` (cartão da peça e QR) · `verificar.js` (verificador + leitor de QR) · `ativar.js` · `admin.js` · `verificacoes.js` · `main.js` (login, navegação, rotas).

## Administração e login
Cada backend tem a sua página de login (usuário e senha), dentro deste mesmo site:
- `#/login/admin` → **Backend Admin** (pedidos, catálogo, garantias)
- `#/login/verificacao` → **Backend de Verificação** (consultas e peças)

Depois de entrar, aparecem as seções de administração correspondentes. O token da sessão fica só na aba do navegador (`sessionStorage`) e expira no tempo definido no backend. Em **Administração** há também "Alterar senha". Sem login, o site mostra apenas as áreas públicas (verificar e ativar).

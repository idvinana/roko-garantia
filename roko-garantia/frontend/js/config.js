// ===== CONFIGURAÇÃO DO FRONTEND =====
// Endereços dos dois backends (sem barra no final). Em produção, use HTTPS.
window.RK_CONFIG = {
  ADMIN_API: "http://localhost:8000",   // Backend Admin (pedidos, catálogo, garantias, ativação, certificados)
  VERIF_API: "http://localhost:8001",   // Backend de Verificação (autenticidade e registro de consultas)
  FRONTEND_URL: ""                      // endereço público deste site (vai nos QR Codes). Vazio = endereço atual
};

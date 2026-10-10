"""Geração do certificado de garantia em PDF, com QR Code único ligado ao verificador."""
import io
import qrcode
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

W, H = 148 * mm, 210 * mm
BLACK = HexColor("#0B0B0C"); GOLD = HexColor("#C9A961"); SAND = HexColor("#D8CDB8"); RED = HexColor("#C8452B"); WHITE = HexColor("#F5F2EA")

def _qr(url: str) -> ImageReader:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=1, box_size=12)
    q.add_data(url); q.make(fit=True)
    buf = io.BytesIO(); q.make_image(fill_color="#0B0B0C", back_color="#FFFFFF").convert("RGB").save(buf, "PNG"); buf.seek(0)
    return ImageReader(buf)

def _br(d: str) -> str:
    try: return date.fromisoformat(d[:10]).strftime("%d/%m/%Y")
    except Exception: return d or "-"

def _seal(c, cx, cy, r, col):
    c.setStrokeColor(col); c.setLineWidth(1.2); c.circle(cx, cy, r, stroke=1, fill=0)
    c.setLineWidth(0.4); c.circle(cx, cy, r - 2 * mm, stroke=1, fill=0)
    c.setFillColor(RED); p = c.beginPath(); p.arc(cx - r * 0.45, cy - r * 0.05, cx + r * 0.45, cy + r * 0.85, 0, 180); p.close(); c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(col); c.setLineWidth(0.8); c.line(cx - r * 0.7, cy - r * 0.05, cx + r * 0.7, cy - r * 0.05)
    c.setLineWidth(0.4)
    for i, dy in enumerate([0.18, 0.3, 0.42]):
        w = r * (0.55 - 0.12 * i); c.line(cx - w, cy - r * dy - r * 0.05, cx + w, cy - r * dy - r * 0.05)
    c.setFillColor(col); c.setFont("Times-Bold", r * 0.42); c.drawCentredString(cx, cy - r * 0.88, "RK")

def _border(c, col):
    c.setStrokeColor(col); c.setLineWidth(1); c.rect(7 * mm, 7 * mm, W - 14 * mm, H - 14 * mm)
    c.setLineWidth(0.3); c.rect(9 * mm, 9 * mm, W - 18 * mm, H - 18 * mm)

TERMS = [
 ("1. PRAZO", "12 meses contados da data da compra (nota fiscal/pedido): 90 dias de garantia legal (art. 26, II, CDC) acrescidos de garantia contratual complementar (art. 50, CDC). A ativação digital registra o certificado e agiliza o atendimento."),
 ("2. COBERTURA", "Defeitos de fabricação em armação, hastes, dobradiças, parafusos, acabamento e lentes (tratamento e proteção UV conforme descrição do produto)."),
 ("3. NÃO COBRE", "Quedas, impactos, torção, riscos nas lentes, desgaste natural, exposição a calor excessivo (ex.: painel de carro), produtos químicos, ajustes ou reparos feitos por terceiros, perda, furto ou roubo."),
 ("4. COMO ACIONAR", "Entre em contato pelo site rokoikigai.com ou Instagram @rookoikigai informando o nº do pedido ou ID de validação. O produto passará por análise técnica, com reparo, troca ou restituição conforme o Código de Defesa do Consumidor."),
 ("5. AUTENTICIDADE", "Cada peça possui nº de série único. Confirme a originalidade escaneando o QR Code “Autenticidade” desta página ou digitando o ID de validação na página de verificação do site."),
]

def _front(c, u, fe):
    c.setFillColor(BLACK); c.rect(0, 0, W, H, stroke=0, fill=1); _border(c, GOLD)
    _seal(c, W / 2, H - 36 * mm, 15 * mm, GOLD)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 9); c.drawCentredString(W / 2, H - 60 * mm, "R O K O   I K I G A I   S T U D I O")
    c.setFillColor(WHITE); c.setFont("Times-Bold", 21); c.drawCentredString(W / 2, H - 72 * mm, "CERTIFICADO DE GARANTIA")
    c.setFillColor(SAND); c.setFont("Helvetica", 7.5); c.drawCentredString(W / 2, H - 78 * mm, "ÓCULOS  ·  DROP 01 — COASTAL PURPOSE  ·  12 MESES")
    c.setStrokeColor(GOLD); c.setLineWidth(0.5); c.line(W / 2 - 12 * mm, H - 82 * mm, W / 2 + 12 * mm, H - 82 * mm)
    # QR de autenticidade (canto superior direito)
    qx, qy, qs = W - 38 * mm, H - 44 * mm, 22 * mm
    c.setFillColor(HexColor("#FFFFFF")); c.roundRect(qx - 1.5 * mm, qy - 1.5 * mm, qs + 3 * mm, qs + 3 * mm, 1.5 * mm, stroke=0, fill=1)
    c.drawImage(_qr(f"{fe}/#/verificar/{u['vid']}"), qx, qy, qs, qs)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 5.5); c.drawCentredString(qx + qs / 2, qy - 5 * mm, "AUTENTICIDADE")
    m = u.get("modelo") or {}
    fields = [("MODELO", m.get("n", u["produto"])), ("COR / LENTE", f"{m.get('cor', '-')} · {m.get('lente', '-')}"), ("Nº DE SÉRIE", u["serial"]),
              ("ID DE VALIDAÇÃO", u["vid"]), ("DATA DA COMPRA", _br(u["data_compra"])), ("VÁLIDA ATÉ", _br(u["valida_ate"]))]
    y = H - 93 * mm; x0, x1 = 18 * mm, W - 18 * mm
    for lab, val in fields:
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 6.5); c.drawString(x0, y + 1.5 * mm, lab)
        c.setFillColor(WHITE); c.setFont("Helvetica", 8.5); c.drawString(x0 + 32 * mm, y + 1.5 * mm, str(val))
        c.setStrokeColor(HexColor("#5A5140")); c.setLineWidth(0.4); c.line(x0 + 30 * mm, y, x1, y)
        y -= 6.2 * mm
    st = ParagraphStyle("t", fontName="Helvetica", fontSize=6.6, leading=8.6, textColor=SAND)
    sh = ParagraphStyle("h", fontName="Helvetica-Bold", fontSize=6.6, leading=8.6, textColor=GOLD)
    y = H - 131 * mm
    for h, t in TERMS:
        p1 = Paragraph(h, sh); _, hh = p1.wrap(W - 36 * mm, 100); p1.drawOn(c, x0, y - hh); y -= hh
        p2 = Paragraph(t, st); _, hh = p2.wrap(W - 36 * mm, 100); p2.drawOn(c, x0, y - hh); y -= hh + 2.2 * mm
    c.setFillColor(GOLD); c.setFont("Times-Italic", 8); c.drawCentredString(W / 2, 12.5 * mm, "Coastal purpose. Made with ikigai.")
    c.showPage()

def _back(c, fe):
    c.setFillColor(SAND); c.rect(0, 0, W, H, stroke=0, fill=1); _border(c, BLACK)
    c.setFillColor(BLACK); c.setFont("Helvetica-Bold", 8); c.drawCentredString(W / 2, H - 22 * mm, "R O K O   I K I G A I   S T U D I O")
    c.setFont("Times-Bold", 19); c.drawCentredString(W / 2, H - 33 * mm, "ATIVE SUA GARANTIA")
    c.setFont("Helvetica", 7.5); c.drawCentredString(W / 2, H - 39 * mm, "Escaneie o QR Code e ative o certificado da sua peça")
    q = 52 * mm; qx = (W - q) / 2; qy = H - 100 * mm
    c.setFillColor(WHITE); c.setStrokeColor(BLACK); c.setLineWidth(1); c.roundRect(qx - 4 * mm, qy - 4 * mm, q + 8 * mm, q + 8 * mm, 3 * mm, stroke=1, fill=1)
    c.drawImage(_qr(f"{fe}/#/ativar"), qx, qy, q, q)
    c.setFillColor(BLACK); c.setFont("Helvetica-Bold", 8.5)
    c.drawCentredString(W / 2, qy - 11 * mm, fe.replace("https://", "").replace("http://", "") + "/#/ativar")
    steps = [("1", "Escaneie o QR Code", "Aponte a câmera do celular para o código acima."),
             ("2", "Identifique a compra", "Informe o número do pedido e o e-mail da compra."),
             ("3", "Verificação", "Conferimos o registro da venda em nosso sistema."),
             ("4", "Garantia ativada", "Você recebe na tela e por e-mail o Certificado Digital de Autenticidade.")]
    y = qy - 26 * mm
    for n, t, d in steps:
        c.setFillColor(BLACK); c.circle(20 * mm, y + 1.2 * mm, 3.4 * mm, stroke=0, fill=1)
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8); c.drawCentredString(20 * mm, y - 0.3 * mm, n)
        c.setFillColor(BLACK); c.setFont("Helvetica-Bold", 8); c.drawString(27 * mm, y + 2 * mm, t)
        p = Paragraph(d, ParagraphStyle("d", fontName="Helvetica", fontSize=7, leading=8.8, textColor=HexColor("#2A2620")))
        _, hh = p.wrap(W - 43 * mm, 50); p.drawOn(c, 27 * mm, y - hh + 0.5 * mm); y -= hh + 9 * mm
    c.setFillColor(BLACK); c.setFont("Helvetica", 6.5)
    c.drawCentredString(W / 2, 19 * mm, "ROKO IKIGAI STUDIO  ·  Porto Seguro — BA  ·  @rookoikigai")
    c.drawCentredString(W / 2, 15 * mm, "Guarde este cartão junto à nota fiscal/pedido.")
    c.showPage()

def build_pdf(unidades: list, frontend_url: str) -> bytes:
    """unidades: dicts com produto, serial, vid, data_compra, valida_ate. 2 páginas (frente/verso) por unidade."""
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle("ROKO IKIGAI STUDIO — Certificado de Garantia"); c.setAuthor("ROKO IKIGAI STUDIO")
    for u in unidades:
        _front(c, u, frontend_url); _back(c, frontend_url)
    c.save(); return buf.getvalue()

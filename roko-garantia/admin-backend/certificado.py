"""Certificado de garantia em PDF (A4, 2 páginas por peça), com QR Codes únicos: autenticidade (frente) e ativação (verso)."""
import io, math, base64
from certificado_arte import PALM_PNG, MONT_PNG, SEA_JPG, BAND2_JPG, ICONES
import certificado_fontes as F
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.graphics import renderPDF
from svglib.svglib import svg2rlg
import qrcode
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.utils import ImageReader
from reportlab.platypus import Paragraph
from reportlab.lib.styles import ParagraphStyle

W, H = 210 * mm, 297 * mm
CREAM = HexColor("#F1EDE7"); NAVY = HexColor("#0E3A5A"); INK = HexColor("#1B2B3A"); MUTED = HexColor("#5B7083"); LINE = HexColor("#9DB1C0")
RED = HexColor("#C8452B"); WHITE = HexColor("#FFFFFF"); PALE = HexColor("#E6EDF1")

KANJI = {
 '生': [('M', 270, 801), ('C', 218, 622, 128, 452, 38, 347), ('L', 53, 336), ('C', 119, 394, 181, 473, 234, 565), ('L', 469, 565), ('L', 469, 312), ('L', 156, 312), ('L', 164, 283), ('L', 469, 283), ('L', 469, -6), ('L', 44, -6), ('L', 53, -35), ('L', 933, -35), ('C', 947, -35, 957, -30, 960, -20), ('C', 925, 12, 871, 53, 871, 53), ('L', 823, -6), ('L', 524, -6), ('L', 524, 283), ('L', 835, 283), ('C', 849, 283, 859, 288, 861, 299), ('C', 829, 329, 775, 370, 775, 370), ('L', 729, 312), ('L', 524, 312), ('L', 524, 565), ('L', 873, 565), ('C', 887, 565, 896, 569, 899, 580), ('C', 865, 613, 813, 651, 813, 651), ('L', 766, 594), ('L', 524, 594), ('L', 524, 796), ('C', 549, 800, 558, 810, 561, 825), ('L', 469, 834), ('L', 469, 594), ('L', 250, 594), ('C', 277, 644, 301, 697, 322, 752), ('C', 344, 751, 356, 760, 360, 770), ('Z',)],
 'き': [('M', 359, 560), ('C', 407, 560, 462, 569, 515, 581), ('C', 534, 532, 554, 486, 574, 445), ('C', 510, 428, 439, 417, 366, 417), ('C', 250, 417, 238, 459, 303, 515), ('L', 286, 531), ('C', 180, 457, 216, 373, 356, 373), ('C', 445, 373, 526, 384, 596, 400), ('C', 635, 326, 679, 272, 696, 247), ('C', 703, 237, 703, 234, 689, 238), ('C', 640, 250, 568, 269, 473, 269), ('C', 306, 269, 226, 191, 226, 112), ('C', 226, -6, 375, -44, 493, -44), ('C', 626, -44, 679, -28, 679, -3), ('C', 679, 12, 661, 24, 634, 24), ('C', 599, 24, 572, 14, 501, 14), ('C', 402, 14, 269, 24, 269, 122), ('C', 269, 190, 353, 235, 461, 235), ('C', 544, 235, 624, 209, 662, 191), ('C', 698, 174, 713, 157, 736, 157), ('C', 758, 157, 773, 200, 773, 226), ('C', 773, 249, 715, 278, 637, 410), ('C', 716, 432, 777, 458, 815, 480), ('C', 832, 490, 836, 499, 836, 509), ('C', 836, 524, 819, 530, 797, 530), ('C', 779, 530, 772, 518, 717, 494), ('C', 688, 481, 652, 467, 612, 455), ('C', 586, 505, 568, 552, 555, 592), ('C', 639, 615, 711, 644, 730, 656), ('C', 743, 665, 750, 673, 750, 682), ('C', 749, 698, 727, 703, 708, 703), ('C', 691, 703, 650, 668, 541, 637), ('C', 530, 677, 524, 718, 517, 754), ('C', 513, 779, 475, 786, 443, 786), ('C', 416, 786, 395, 779, 367, 764), ('L', 371, 745), ('C', 386, 746, 402, 747, 419, 747), ('C', 449, 746, 459, 735, 467, 713), ('L', 498, 625), ('C', 449, 613, 394, 604, 359, 604), ('C', 277, 604, 247, 624, 199, 662), ('L', 185, 650), ('C', 239, 565, 296, 560, 359, 560), ('Z',)],
 'が': [('M', 850, 557), ('C', 863, 557, 871, 566, 871, 581), ('C', 871, 601, 860, 618, 835, 642), ('C', 811, 665, 775, 688, 725, 710), ('L', 711, 691), ('C', 753, 663, 782, 632, 803, 607), ('C', 823, 582, 834, 557, 850, 557), ('Z',), ('M', 874, 203), ('C', 900, 203, 911, 234, 911, 270), ('C', 911, 347, 886, 411, 854, 449), ('C', 816, 493, 770, 521, 685, 534), ('L', 672, 510), ('C', 740, 497, 780, 471, 809, 432), ('C', 839, 391, 849, 348, 851, 322), ('C', 852, 297, 850, 287, 829, 280), ('C', 801, 270, 730, 256, 695, 249), ('L', 701, 225), ('C', 735, 230, 800, 237, 821, 234), ('C', 850, 230, 847, 203, 874, 203), ('Z',), ('M', 941, 627), ('C', 955, 627, 963, 635, 963, 651), ('C', 963, 672, 952, 691, 925, 713), ('C', 902, 733, 864, 754, 814, 773), ('L', 801, 755), ('C', 845, 726, 871, 703, 894, 677), ('C', 916, 653, 927, 627, 941, 627), ('Z',), ('M', 388, -12), ('C', 439, -12, 478, 14, 507, 51), ('C', 562, 124, 600, 263, 600, 383), ('C', 600, 497, 559, 537, 486, 537), ('C', 461, 537, 427, 533, 399, 528), ('L', 446, 640), ('C', 456, 664, 474, 673, 474, 695), ('C', 474, 717, 404, 750, 365, 750), ('C', 341, 750, 321, 746, 305, 741), ('L', 305, 718), ('C', 329, 717, 367, 712, 382, 706), ('C', 395, 699, 398, 691, 398, 680), ('C', 398, 662, 375, 594, 344, 516), ('C', 272, 500, 176, 474, 144, 474), ('C', 115, 474, 109, 508, 99, 535), ('L', 78, 531), ('C', 74, 513, 75, 489, 78, 476), ('C', 86, 447, 121, 411, 147, 411), ('C', 171, 411, 183, 422, 229, 440), ('C', 250, 448, 286, 460, 325, 472), ('C', 300, 410, 271, 346, 245, 298), ('C', 187, 188, 145, 123, 89, 50), ('C', 77, 34, 74, 23, 74, 9), ('C', 74, -11, 88, -23, 99, -23), ('C', 112, -23, 122, -17, 136, 4), ('C', 179, 68, 227, 158, 284, 272), ('C', 319, 342, 353, 419, 382, 487), ('C', 418, 496, 452, 502, 476, 502), ('C', 534, 502, 551, 469, 551, 393), ('C', 551, 275, 512, 158, 482, 108), ('C', 455, 63, 430, 53, 400, 53), ('C', 377, 53, 331, 81, 278, 116), ('L', 266, 99), ('C', 323, 52, 331, 40, 338, 26), ('C', 351, 1, 356, -12, 388, -12), ('Z',)],
 'い': [('M', 348, 43), ('C', 385, 27, 408, 42, 408, 65), ('C', 408, 84, 391, 91, 402, 132), ('C', 409, 161, 443, 246, 467, 309), ('L', 439, 321), ('C', 412, 260, 378, 185, 348, 138), ('C', 339, 125, 329, 123, 314, 131), ('C', 269, 154, 208, 223, 208, 359), ('C', 208, 456, 238, 520, 238, 564), ('C', 238, 604, 188, 646, 155, 662), ('C', 138, 670, 123, 674, 100, 679), ('L', 89, 662), ('C', 164, 610, 168, 589, 168, 535), ('C', 168, 496, 162, 431, 163, 361), ('C', 165, 163, 271, 77, 348, 43), ('Z',), ('M', 877, 209), ('C', 898, 209, 910, 222, 910, 256), ('C', 910, 321, 879, 423, 823, 483), ('C', 781, 528, 735, 562, 643, 582), ('L', 634, 556), ('C', 697, 534, 751, 503, 788, 448), ('C', 833, 379, 843, 287, 849, 243), ('C', 852, 221, 862, 209, 877, 209), ('Z',)],
}

for _n, _k in [("JostL", "JOST_L"), ("JostR", "JOST_R"), ("CormM", "CORM_M"), ("CormSB", "CORM_SB"), ("AlegR", "ALEG_R"), ("AlegM", "ALEG_M"), ("AlegB", "ALEG_B")]:
    pdfmetrics.registerFont(TTFont(_n, io.BytesIO(base64.b64decode(getattr(F, _k)))))
from reportlab.pdfbase.pdfmetrics import registerFontFamily
registerFontFamily("AlegR", normal="AlegR", bold="AlegB", italic="AlegR", boldItalic="AlegB"); registerFontFamily("CormM", normal="CormM", bold="CormSB", italic="CormM", boldItalic="CormSB")

def _qr(url: str) -> ImageReader:
    q = qrcode.QRCode(error_correction=qrcode.constants.ERROR_CORRECT_Q, border=1, box_size=12)
    q.add_data(url); q.make(fit=True)
    buf = io.BytesIO(); q.make_image(fill_color="#0E3A5A", back_color="#FFFFFF").convert("RGB").save(buf, "PNG"); buf.seek(0)
    return ImageReader(buf)

def _br(d: str) -> str:
    try: return date.fromisoformat(d[:10]).strftime("%d/%m/%Y")
    except Exception: return d or "-"
def _br2(d: str) -> str:
    try: return date.fromisoformat(d[:10]).strftime("%d/%m/%y")
    except Exception: return d or "-"

def Y(t): return H - t * mm          # t = distância do topo, em mm

def spaced(c, x, y, text, font="AlegR", size=8, sp=1.5, color=NAVY, align="l"):
    c.setFillColor(color); c.setFont(font, size)
    w = c.stringWidth(text, font, size) + sp * max(len(text) - 1, 0)
    if align == "c": x -= w / 2
    elif align == "r": x -= w
    t = c.beginText(x, y); t.setFont(font, size); t.setCharSpace(sp); t.textOut(text); t.setCharSpace(0); c.drawText(t)

def para(c, text, x, ytop, w, size=8, lead=10.4, color=INK, font="AlegR"):
    p = Paragraph(text, ParagraphStyle("p", fontName=font, fontSize=size, leading=lead, textColor=color))
    _, h = p.wrap(w, 200); p.drawOn(c, x, ytop - h); return h

def _kanji_v(c, x, ytop, size, color):
    """生きがい na vertical (contornos vetoriais embutidos: não depende de fonte)."""
    c.setFillColor(color); k = size / 1000.0
    for i, ch in enumerate("生きがい"):
        oy = ytop - (i + 1) * size * 1.12
        p = c.beginPath()
        for op in KANJI[ch]:
            if op[0] == "M": p.moveTo(x + op[1] * k, oy + op[2] * k + size * 0.12)
            elif op[0] == "L": p.lineTo(x + op[1] * k, oy + op[2] * k + size * 0.12)
            elif op[0] == "C": p.curveTo(*[(x + op[j] * k) if j % 2 == 1 else (oy + op[j] * k + size * 0.12) for j in range(1, 7)])
            else: p.close()
        c.drawPath(p, stroke=0, fill=1)

def _seal(c, x, ytop, s):
    c.setStrokeColor(RED); c.setLineWidth(0.9); c.rect(x, ytop - s, s, s, stroke=1, fill=0)
    c.setFillColor(RED); c.setFont("CormSB", s * 0.5); c.drawCentredString(x + s / 2, ytop - s * 0.66, "RK")

# ---------------- ícones (traço fino, estilo linha) ----------------
_IC = {"cal": "calendar-days", "shield": "shield-check", "x": "circle-x", "headset": "headset", "cam": "camera", "ok": "circle-check", "sparkle": "sparkles", "sun": "sun", "gear": "settings", "link": "link"}
_ICD = {}
def _ic(c, kind, cx, cy, r=4.2 * mm, col=NAVY):
    """ícones em traço fino (Lucide, licença ISC) + 'glasses' e 'case' desenhados"""
    if kind in _IC:
        if kind not in _ICD:
            svg = ICONES[_IC[kind]].replace("currentColor", "#0E3A5A").replace('stroke-width="2"', 'stroke-width="1.35"')
            _ICD[kind] = svg2rlg(io.BytesIO(svg.encode()))
        d = _ICD[kind]; sc = (2 * r * 1.12) / 24.0
        c.saveState(); c.translate(cx - r * 1.12, cy - r * 1.12); c.scale(sc, sc); renderPDF.draw(d, c, 0, 0); c.restoreState(); return
    c.saveState(); c.setStrokeColor(col); c.setLineWidth(1.0); c.setLineCap(1); c.setLineJoin(1)
    if kind == "glasses":
        c.setLineWidth(1.1)
        for sx in (-1, 1):
            x0 = cx + sx * r * .95; p = c.beginPath()
            p.moveTo(x0 - r * .82, cy + r * .3)
            p.curveTo(x0 - r * .8, cy - r * .35, x0 - r * .55, cy - r * .62, x0 - r * .25, cy - r * .62)
            p.lineTo(x0 + r * .25, cy - r * .62)
            p.curveTo(x0 + r * .55, cy - r * .62, x0 + r * .8, cy - r * .35, x0 + r * .82, cy + r * .3); c.drawPath(p, stroke=1, fill=0)
        c.line(cx - r * 1.95, cy + r * .3, cx + r * 1.95, cy + r * .3)
        c.line(cx - r * 1.95, cy + r * .3, cx - r * 2.05, cy + r * .45); c.line(cx + r * 1.95, cy + r * .3, cx + r * 2.05, cy + r * .45)
    elif kind == "case":
        c.roundRect(cx - r, cy - r * .5, 2 * r, r, r * .45, stroke=1, fill=0); c.line(cx - r * .55, cy + r * .12, cx + r * .55, cy + r * .12)
    c.restoreState()

# ---------------- decorações ----------------
def _leaf(c, x0, y0, ang, ln, wd, col, col2):
    ca, sa = math.cos(ang), math.sin(ang)
    def pt(u, v): return (x0 + u * ca - v * sa, y0 + u * sa + v * ca)
    p = c.beginPath(); p.moveTo(*pt(0, 0)); p.curveTo(*pt(ln * .3, wd), *pt(ln * .75, wd * .8), *pt(ln, 0)); p.curveTo(*pt(ln * .75, -wd * .8), *pt(ln * .3, -wd), *pt(0, 0)); p.close()
    c.setFillColor(col); c.drawPath(p, stroke=0, fill=1)
    c.setStrokeColor(col2); c.setLineWidth(0.5); a = pt(0, 0); b = pt(ln * .96, 0); c.line(a[0], a[1], b[0], b[1])
    for i in range(1, 9):
        u = ln * i / 9.5; w = wd * .7 * math.sin(math.pi * i / 9.5)
        for s in (-1, 1): q1 = pt(u, 0); q2 = pt(u + ln * .06, s * w); c.line(q1[0], q1[1], q2[0], q2[1])

def _palm(c):
    cols = [(HexColor("#3E5E3A"), HexColor("#26412A")), (HexColor("#56754A"), HexColor("#2E4630")), (HexColor("#2F4A33"), HexColor("#1E3322"))]
    for i, a in enumerate([-15, -38, -60, -82, -104, -126, -148]):
        ln = (44 - abs(i - 3) * 4) * mm; col = cols[i % 3]
        _leaf(c, 3 * mm, Y(2), math.radians(a) + math.radians(8), ln, 4.2 * mm, col[0], col[1])

def _sea(c, y_top, y_bot, wave_seed=0):
    """faixa de mar (vetorial): degradê azul-petróleo + ondas de espuma"""
    h = (y_top - y_bot); n = 36
    for i in range(n):
        t = i / (n - 1); r_, g_, b_ = 0.10 + 0.14 * t, 0.30 + 0.22 * t, 0.42 + 0.20 * t
        c.setFillColor(Color(r_, g_, b_)); c.rect(0, y_top - (i + 1) * h / n, W, h / n + .4, stroke=0, fill=1)
    for k in range(7):
        yy = y_top - h * (0.12 + k * 0.13); c.setStrokeColor(Color(1, 1, 1, alpha=0.30 - k * 0.025)); c.setLineWidth(1.4 - k * 0.12)
        p = c.beginPath(); p.moveTo(0, yy)
        for x in range(0, int(W / mm) + 20, 20):
            p.curveTo(x * mm + 5 * mm, yy + (4 + (k + wave_seed) % 3) * mm, x * mm + 12 * mm, yy - 3 * mm, (x + 20) * mm, yy)
        c.drawPath(p, stroke=1, fill=0)

def _mountains(c, x, ytop, w, h, cols):
    for dx, ww, hh, col in cols:
        c.setFillColor(col); p = c.beginPath(); xs = x + dx * w
        p.moveTo(xs, ytop - h); p.curveTo(xs + ww * w * .25, ytop - h + hh * h * .35, xs + ww * w * .38, ytop - h + hh * h, xs + ww * w * .5, ytop - h + hh * h * .92)
        p.curveTo(xs + ww * w * .66, ytop - h + hh * h * .55, xs + ww * w * .85, ytop - h + hh * h * .2, xs + ww * w, ytop - h); p.close(); c.drawPath(p, stroke=0, fill=1)

def _torii(c, cx, y, s, col):
    c.setFillColor(col); c.rect(cx - s * .5, y, s * .09, s * .9, stroke=0, fill=1); c.rect(cx + s * .41, y, s * .09, s * .9, stroke=0, fill=1)
    c.rect(cx - s * .62, y + s * .88, s * 1.24, s * .1, stroke=0, fill=1); c.rect(cx - s * .55, y + s * .72, s * 1.1, s * .06, stroke=0, fill=1)

def _logo(c, ytop_mm=22):
    size, sp = 28, 8.2; f = "JostL"
    parts = ["ROKO IKIG", "A", "I"]; full = "ROKO IKIGAI"
    w = c.stringWidth(full, f, size) + sp * (len(full) - 1); x = W / 2 - w / 2; y = Y(ytop_mm)
    c.setFillColor(INK); c.setStrokeColor(INK)
    for p in parts:
        if p == "A":   # o "A" do logotipo não tem travessa (Λ)
            aw = c.stringWidth("A", f, size); c.setLineWidth(size * .052); c.setLineCap(0)
            cap = size * .70; c.line(x + aw * .06, y, x + aw * .5, y + cap); c.line(x + aw * .5, y + cap, x + aw * .94, y); x += aw + sp
        else:
            t = c.beginText(x, y); t.setFont(f, size); t.setCharSpace(sp); t.textOut(p); t.setCharSpace(0); c.drawText(t); x += c.stringWidth(p, f, size) + sp * len(p)
    spaced(c, W / 2, Y(ytop_mm + 10.5), "S T U D I O", "JostR", 8.4, 4.2, INK, "c")

def _footer(c, left, page):
    c.setStrokeColor(LINE); c.setLineWidth(.3)
    spaced(c, 14 * mm, Y(289), left, "AlegR", 5.6, 1.1, INK)
    spaced(c, W / 2, Y(289), f"PÁGINA {page} DE 2", "AlegR", 5.6, 1.1, INK, "c")
    spaced(c, W - 14 * mm, Y(289), "ROKOIKIGAI.COM", "AlegR", 5.6, 1.1, INK, "r")

_IMG = {}
def _img(k, b64s):
    if k not in _IMG: _IMG[k] = ImageReader(io.BytesIO(base64.b64decode(b64s)))
    return _IMG[k]

def _bg(c):
    c.setFillColor(CREAM); c.rect(0, 0, W, H, stroke=0, fill=1)

# ---------------- página 1 ----------------
def _front(c, u, fe):
    _bg(c); c.drawImage(_img("palm", PALM_PNG), 0, H - 49.5 * mm, 58.7 * mm, 49.5 * mm, mask="auto")
    _logo(c, 30)
    spaced(c, W / 2, Y(49), "COASTAL PURPOSE   ·   CRAFTED EYEWEAR", "AlegM", 6.6, 2.6, NAVY, "c")
    _kanji_v(c, W - 18 * mm, Y(16), 4.6 * mm, MUTED); _seal(c, W - 19.5 * mm, Y(48), 7 * mm)
    spaced(c, W / 2, Y(72), "CERTIFICADO DE AUTENTICIDADE", "CormSB", 17, 3.0, INK, "c")
    spaced(c, W / 2, Y(82), "Certificado de Garantia & Origem", "CormSB", 15, 1.3, INK, "c")
    x0, x1, yt, yb = 14 * mm, W - 14 * mm, 92, 152
    c.setStrokeColor(NAVY); c.setLineWidth(.6); c.line(x0, Y(yt), x1, Y(yt)); c.line(x0, Y(yb), x1, Y(yb))
    # QR autenticidade
    qs = 26 * mm; qx = x0 + 6 * mm; qy = Y(yt + 6) - qs - 2 * mm
    c.setFillColor(WHITE); c.setStrokeColor(LINE); c.setLineWidth(.6); c.roundRect(qx - 2.5 * mm, qy - 2.5 * mm, qs + 5 * mm, qs + 5 * mm, 3 * mm, stroke=1, fill=1)
    c.drawImage(_qr(f"{fe}/#/verificar/{u['vid']}"), qx, qy, qs, qs)
    spaced(c, qx + qs / 2, qy - 8 * mm, "VERIFIQUE A", "AlegB", 5.6, 1.3, NAVY, "c"); spaced(c, qx + qs / 2, qy - 11.6 * mm, "AUTENTICIDADE", "AlegB", 5.6, 1.3, NAVY, "c")
    c.setStrokeColor(LINE); c.line(x0 + 42 * mm, Y(yt + 4), x0 + 42 * mm, Y(yb - 4))
    m = u.get("modelo") or {}
    cx1, cx2 = x0 + 48 * mm, x0 + 48 * mm + 68 * mm
    def cell(x, ytop, lab, val, big=False):
        spaced(c, x, Y(ytop + 4), lab, "AlegM", 6.2, 1.5, NAVY)
        v = str(val).upper(); sz = 10.5
        while c.stringWidth(v, "AlegR", sz) > 62 * mm and sz > 6: sz -= .3
        c.setFillColor(INK); c.setFont("AlegR", sz); c.drawString(x, Y(ytop + 11.5), v)
    cell(cx1, yt + 2, "COLEÇÃO / DROP", "Drop 01 — Coastal Purpose"); cell(cx2, yt + 2, "MODELO", m.get("n", u["produto"]))
    _ic(c, "glasses", W - 14 * mm - 21 * mm, Y(yt + 11), 4.8 * mm, NAVY)
    c.setStrokeColor(LINE); c.setLineWidth(.3); c.line(x0 + 44 * mm, Y(yt + 19), x1 - 2 * mm, Y(yt + 19))
    cell(cx1, yt + 21, "COR DA ARMAÇÃO / LENTE", f"{m.get('cor', '-')} · {m.get('lente', '-')}"); cell(cx2, yt + 21, "NÚMERO DE SÉRIE", u["serial"])
    c.line(x0 + 44 * mm, Y(yt + 39), x1 - 2 * mm, Y(yt + 39))
    cell(cx1, yt + 40, "ID DE VALIDAÇÃO", u["vid"]); cell(cx2, yt + 40, "PERÍODO DE COBERTURA", f"12 meses ({_br2(u['data_compra'])} – {_br2(u['valida_ate'])})")
    # termos
    spaced(c, x0, Y(166), "TERMOS DE COBERTURA E GARANTIA", "CormSB", 11.5, 2.4, NAVY)
    termos = [("cal", "1. PRAZO E VALIDADE", "12 meses contados a partir da data da compra. Inclui 90 dias de garantia legal (art. 26, II, CDC) acrescidos da garantia contratual Roko Ikigai."),
              ("shield", "2. COBERTURA DO PRODUTO", "Defeitos de fabricação em armações de acetato, hastes, dobradiças, parafusos, tratamentos de lentes e proteção UV 400 integral."),
              ("x", "3. EXCLUSÕES DE GARANTIA", "Danos decorrentes de quedas, riscos acidentais nas lentes, exposição a calor extremo (como painéis de veículos), solventes ou manuseio inadequado."),
              ("headset", "4. SUPORTE E AUTENTICIDADE", "Cada peça possui registro único gravado. Para suporte técnico, utilize o canal oficial informado ou escaneie o código QR de validação.")]
    c.setStrokeColor(LINE); c.setLineWidth(.3); c.line(x0, Y(171), x1, Y(171)); c.line(W / 2, Y(173), W / 2, Y(222)); c.line(x0, Y(197), x1, Y(197))
    for i, (ic, t, d) in enumerate(termos):
        bx = x0 + (i % 2) * 94 * mm + (2 * mm if i % 2 else 0); by = 174 + (i // 2) * 26
        _ic(c, ic, bx + 5.5 * mm, Y(by + 8.5), 5.4 * mm)
        c.setFillColor(NAVY); spaced(c, bx + 14 * mm, Y(by + 4.2), t, "AlegB", 7.8, 1.0, NAVY)
        para(c, d, bx + 14 * mm, Y(by + 7.3), 74 * mm, 8.2, 10.6, INK)
    # faixa de mar + ativação
    c.drawImage(_img("sea", SEA_JPG), 0, Y(281.5), W, 57.5 * mm)
    c.setFillColor(Color(1, 1, 1, alpha=.93)); c.roundRect(34 * mm, Y(274), 149 * mm, 42 * mm, 4 * mm, stroke=0, fill=1)
    qs2 = 18 * mm; qx2 = 41 * mm; qy2 = Y(262)
    c.setFillColor(WHITE); c.setStrokeColor(LINE); c.setLineWidth(.5); c.roundRect(qx2 - 1.5 * mm, qy2 - 1.5 * mm, qs2 + 3 * mm, qs2 + 3 * mm, 2 * mm, stroke=1, fill=1)
    c.drawImage(_qr(f"{fe}/#/ativar/{u['vid']}"), qx2, qy2, qs2, qs2)
    spaced(c, 66 * mm, Y(240), "ATIVAÇÃO DIGITAL INSTANTÂNEA", "AlegB", 7.4, 1.4, NAVY)
    para(c, "Escaneie o QR Code ao lado ou acesse o portal de verificação para registrar seu óculos e agilizar atendimentos futuros.", 66 * mm, Y(243), W - 106 * mm, 7.2, 9.4, INK)
    c.setStrokeColor(LINE); c.setLineWidth(.3); c.line(66 * mm, Y(255.5), W - 40 * mm, Y(255.5))
    for i, (ic, t) in enumerate([("cam", "1. Aponte a Câmera"), ("ok", "2. Confirme a Compra"), ("shield", "3. Garantia Ativada")]):
        sx = 70 * mm + i * 35 * mm; _ic(c, ic, sx + 3.5 * mm, Y(264), 4.2 * mm); c.setFillColor(INK); c.setFont("AlegR", 6); c.drawString(sx + 9 * mm, Y(264.8), t)
        if i: c.line(sx - 3 * mm, Y(260), sx - 3 * mm, Y(268.5))
    _footer(c, "ROKO IKIGAI STUDIO   ·   PORTO SEGURO, BA", 1); c.showPage()

# ---------------- página 2 ----------------
def _back(c, fe, u):
    vid = u["vid"]; _bg(c)
    c.drawImage(_img("mont", MONT_PNG), W - 65 * mm, H - 28.8 * mm, 65 * mm, 28.8 * mm, mask="auto")
    _logo(c, 26); spaced(c, W / 2, Y(46), "GUIA DE ATIVAÇÃO DIGITAL & CUIDADOS COM A PEÇA", "AlegR", 6.6, 2.7, NAVY, "c")
    bx0, bx1, byt, byb = 12 * mm, W - 12 * mm, 54, 182
    c.setFillColor(Color(1, 1, 1, alpha=.55)); c.setStrokeColor(LINE); c.setLineWidth(.5); c.rect(bx0, Y(byb), bx1 - bx0, (byb - byt) * mm, stroke=1, fill=1)
    qs = 28 * mm; qx = bx0 + 8 * mm; qy = Y(byt + 8) - qs - 2 * mm
    c.setFillColor(WHITE); c.setStrokeColor(LINE); c.roundRect(qx - 3 * mm, qy - 3 * mm, qs + 6 * mm, qs + 6 * mm, 3.5 * mm, stroke=1, fill=1)
    c.drawImage(_qr(f"{fe}/#/ativar/{vid}"), qx, qy, qs, qs)
    spaced(c, qx + qs / 2, qy - 8 * mm, "QR Code", "CormM", 7.2, .4, NAVY, "c"); spaced(c, qx + qs / 2, qy - 11.5 * mm, "de Ativação", "CormM", 7.2, .4, NAVY, "c")
    c.setFillColor(NAVY); c.roundRect(qx - 1 * mm, qy - 21 * mm, qs + 2 * mm, 6.5 * mm, 1.5 * mm, stroke=0, fill=1)
    spaced(c, qx + qs / 2, qy - 18.8 * mm, "ESCANEAR", "AlegB", 6.6, 1.6, WHITE, "c")
    tx = bx0 + 52 * mm
    spaced(c, tx, Y(byt + 10), "PASSO A PASSO DE ATIVAÇÃO DO CERTIFICADO", "CormSB", 11, 2.0, NAVY)
    c.setFillColor(INK); c.setFont("CormSB", 15); c.drawString(tx, Y(byt + 21.5), "Ative sua Garantia em 4 Passos")
    h = para(c, f"A validação digital registra o número de série <b>{u['serial']}</b> em nossa base de dados oficial, garantindo a autenticidade da sua peça em qualquer lugar do mundo.", tx, Y(byt + 26), bx1 - tx - 8 * mm, 9.5, 12.5, INK, "CormM")
    ly = Y(byt + 25) - h - 5 * mm
    c.setFillColor(PALE); c.roundRect(tx, ly - 7.5 * mm, bx1 - tx - 8 * mm, 9.5 * mm, 4.7 * mm, stroke=0, fill=1)
    _ic(c, "link", tx + 6 * mm, ly - 2.8 * mm, 3.4 * mm); c.setFillColor(NAVY); c.setFont("AlegR", 8)
    c.drawString(tx + 13 * mm, ly - 3.8 * mm, fe.replace("https://", "").replace("http://", "") + "/#/ativar")
    c.setStrokeColor(LINE); c.setLineWidth(.4); c.line(bx0 + 5 * mm, Y(122), bx1 - 5 * mm, Y(122)); c.line(W / 2, Y(126), W / 2, Y(177)); c.line(bx0 + 5 * mm, Y(150), bx1 - 5 * mm, Y(150))
    passos = [("ESCANEIE O CÓDIGO", "Aponte a câmera do seu smartphone para o QR Code acima ou acesse o link de ativação oficial."),
              ("CONFIRME A COMPRA", "A peça já é identificada pelo QR Code. Informe o e-mail cadastrado no momento da aquisição."),
              ("VERIFICAÇÃO DE DADOS", "O sistema confirmará automaticamente a combinação do ID de validação com seu lote exclusivo."),
              ("CERTIFICADO EMITIDO", "Você receberá a confirmação em tela e a cópia digital do Certificado de Autenticidade no e-mail.")]
    for i, (t, d) in enumerate(passos):
        sx = bx0 + 8 * mm + (i % 2) * 94 * mm; sy = 124 + (i // 2) * 28
        c.setFillColor(NAVY); c.circle(sx + 4 * mm, Y(sy + 6), 4 * mm, stroke=0, fill=1); c.setFillColor(WHITE); c.setFont("AlegB", 10); c.drawCentredString(sx + 4 * mm, Y(sy + 7.4), str(i + 1))
        spaced(c, sx + 12 * mm, Y(sy + 4.5), t, "AlegB", 7.4, 1.3, NAVY); para(c, d, sx + 12 * mm, Y(sy + 7.8), 70 * mm, 8.2, 10.6, INK)
    spaced(c, 12 * mm, Y(193), "PRESERVAÇÃO & CUIDADOS COM SEU ROKO IKIGAI", "CormSB", 11.5, 2.2, NAVY)
    c.setStrokeColor(LINE); c.line(12 * mm, Y(197), W - 12 * mm, Y(197)); c.line(W / 2, Y(199), W / 2, Y(244)); c.line(12 * mm, Y(221), W - 12 * mm, Y(221))
    cuid = [("sparkle", "LIMPEZA DAS LENTES", "Lave suavemente com água corrente fria e sabão neutro. Seque apenas com a flanela de microfibra de alta densidade fornecida no estojo."),
            ("case", "ARMAZENAMENTO ADEQUADO", "Mantenha seus óculos sempre guardados no estojo protetor rígido quando não estiver em uso para evitar riscos e deformações."),
            ("sun", "PROTEÇÃO TÉRMICA", "Evite deixar sua armação de acetato em ambientes de calor extremo, como o porta-luvas ou painel de veículos expostos ao sol."),
            ("gear", "AJUSTES TÉCNICOS", "Não force a estrutura das hastes ou dobradiças. Para eventuais ajustes de anatomia, consulte uma ótica especializada ou o nosso suporte.")]
    for i, (ic, t, d) in enumerate(cuid):
        sx = 12 * mm + (i % 2) * 96 * mm + (2 * mm if i % 2 else 0); sy = 199 + (i // 2) * 22
        _ic(c, ic, sx + 6 * mm, Y(sy + 9), 5.6 * mm); spaced(c, sx + 16 * mm, Y(sy + 4.5), t, "AlegB", 7.2, 1.2, NAVY); para(c, d, sx + 16 * mm, Y(sy + 7.8), 74 * mm, 8.2, 10.4, INK)
    c.drawImage(_img("band2", BAND2_JPG), 9 * mm, Y(282.2), 192 * mm, 32.7 * mm)
    _footer(c, "ROKO IKIGAI STUDIO   ·   INSTAGRAM: @ROOKOIKIGAI", 2); c.showPage()

def build_pdf(unidades: list, frontend_url: str) -> bytes:
    """unidades: dicts com produto, serial, vid, data_compra, valida_ate, modelo. 2 páginas (frente/verso) A4 por unidade."""
    buf = io.BytesIO(); c = canvas.Canvas(buf, pagesize=(W, H))
    c.setTitle("ROKO IKIGAI STUDIO — Certificado de Autenticidade e Garantia"); c.setAuthor("ROKO IKIGAI STUDIO")
    for u in unidades:
        _front(c, u, frontend_url); _back(c, frontend_url, u)
    c.save(); return buf.getvalue()

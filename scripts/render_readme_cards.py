#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Renderiza os cards SVG animados do perfil em cards/ (tema claro, estilo editorial).

Lê data/contributions.json (atualizado pela Action). Fontes Instrument Serif
(nome), Space Grotesk (texto) e JetBrains Mono (eyebrow/ASCII) são subsetadas com
fontTools e embutidas como WOFF base64 — funciona dentro de <img>, que é como o
GitHub mostra o README. O retrato em ASCII é gerado da foto com Pillow.

Animação: keyframes CSS (desligados em prefers-reduced-motion) + <animate> SMIL.
STATIC=1 rende o quadro final (sem animação) pra tirar print antes de commitar.

Knobs no topo: BRAND (cor de marca), EYEBROW, DESC.
"""
import os, io, json, base64, html
from collections import OrderedDict

# ---------------- CONFIG ----------------
BRAND  = "#4f8cff"                       # azul de marca — troque aqui
PAPER  = "none"                          # hero: fundo transparente (adapta ao tema)
CARD   = "#161b22"                       # fundo dos cards (dark, estilo GitHub)
INK    = "#e6edf3"
MUTE   = "#8b949e"
FAINT  = "#8b949e"                       # ASCII
LINE   = "#2a3139"                       # bordas
HEAT   = ["#21262d", "#16335f", "#1f5fd0", "#3b82f6", "#7cb0ff"]  # níveis do gráfico
LOGIN  = "MatheusNunesBoraso"
EYEBROW = "FULLSTACK ENGINEER · NETBIL EDUCACIONAL"
DESC    = ["Construo produtos web e mobile na Netbil,",
           "e tomo muito café enquanto faço."]
STATIC = os.environ.get("STATIC") == "1"

HERE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS  = os.path.join(HERE, "cards")
ASSETS = os.path.join(HERE, "assets")
DATA   = os.path.join(HERE, "data", "contributions.json")

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
RAMP = " .:-=+*#%@"
SUBSET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
          ".,:;!?@#%&*()[]{}/+-_='\"…·—“”↗$áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ")

# ---------------- FONTES ----------------
def _woff_b64(path, text, wght=None):
    from fontTools import subset
    from fontTools.ttLib import TTFont
    font = TTFont(path)
    if wght is not None and "fvar" in font:
        from fontTools.varLib.instancer import instantiateVariableFont
        instantiateVariableFont(font, {"wght": wght}, inplace=True)
    opt = subset.Options()
    opt.flavor = "woff"
    opt.desubroutinize = True
    opt.layout_features = []
    opt.name_IDs = []
    opt.glyph_names = False
    sub = subset.Subsetter(options=opt)
    sub.populate(text=text)
    sub.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO(); font.save(buf)
    return base64.b64encode(buf.getvalue()).decode()

def _f(name):
    return os.path.join(ASSETS, "fonts", name)

print("subset de fontes...")
F_SERIF = _woff_b64(_f("InstrumentSerif-Regular.ttf"), SUBSET)
F_SERIT = _woff_b64(_f("InstrumentSerif-Italic.ttf"), SUBSET)
F_SANS  = _woff_b64(_f("SpaceGrotesk.ttf"), SUBSET, wght=500)
F_MONO  = _woff_b64(_f("JetBrainsMono.ttf"), SUBSET + "".join(set(RAMP)), wght=500)

FONTFACE = "".join([
    '@font-face{font-family:Serif;src:url(data:font/woff;base64,%s) format("woff")}' % F_SERIF,
    '@font-face{font-family:SerIt;src:url(data:font/woff;base64,%s) format("woff")}' % F_SERIT,
    '@font-face{font-family:Sans;src:url(data:font/woff;base64,%s) format("woff")}' % F_SANS,
    '@font-face{font-family:Mono;src:url(data:font/woff;base64,%s) format("woff")}' % F_MONO,
])
KEYFRAMES = (
    '@keyframes rise{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:translateY(0)}}'
    '@keyframes fade{from{opacity:0}to{opacity:1}}'
    '@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}'
    '@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}'
    '@keyframes shine{0%,60%{transform:translateX(-120%)}100%{transform:translateX(420%)}}'
    '@keyframes blink{0%,100%{opacity:.3}50%{opacity:1}}'
)
REDUCED = ('@media (prefers-reduced-motion:reduce){*{animation:none!important;'
           'transform:none!important;opacity:1!important}}')

def style(extra=""):
    body = FONTFACE + (KEYFRAMES if not STATIC else "") + extra + REDUCED
    return "<style>" + body + "</style>"

def reveal(delay, kind="rise", dur="0.6"):
    if STATIC:
        return ""
    return "opacity:0;animation:%s %ss ease forwards;animation-delay:%ss" % (kind, dur, delay)

def esc(t):
    return html.escape(str(t), quote=True)

def card(name, w, h, inner):
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" fill="none" role="img">%s</svg>') % (w, h, w, h, inner)
    open(os.path.join(CARDS, name), "w", encoding="utf-8").write(doc)
    print("  ->", name)

def panel(w, h, bg=CARD):
    return '<rect x=".5" y=".5" width="%d" height="%d" rx="18" fill="%s" stroke="%s"/>' % (w - 1, h - 1, bg, LINE)

# ---------------- ASCII ----------------
def ascii_rows(cols=66, gamma=1.3):
    from PIL import Image, ImageOps, ImageDraw, ImageFilter
    p = os.path.join(ASSETS, "avatar.jpg")
    base = ImageOps.autocontrast(Image.open(p).convert("L"), cutoff=2)
    w, h = base.size
    # vinheta radial: mantém o rosto, apaga o fundo (-> branco -> espaço)
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).ellipse([w * 0.10, -h * 0.04, w * 0.90, h * 0.96], fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(w * 0.05))
    img = Image.composite(base, Image.new("L", (w, h), 255), mask)
    rows = max(1, int(cols * (h / w) * 0.52))
    img = img.resize((cols, rows))
    px = img.load()
    n = len(RAMP)
    out = []
    for y in range(rows):
        line = ""
        for x in range(cols):
            b = px[x, y] / 255.0
            if b > 0.93:
                line += " "; continue
            d = (1.0 - b) ** gamma
            line += RAMP[min(n - 1, int(d * (n - 1) + 0.5))]
        out.append(line.rstrip())
    return out

# ---------------- DADOS ----------------
def load():
    d = json.load(open(DATA, encoding="utf-8"))
    days = [dd for wk in d["calendar"]["weeks"] for dd in wk["contributionDays"]]
    days.sort(key=lambda x: x["date"])
    return d, days

def stats(days):
    active = sum(1 for x in days if x["contributionCount"] > 0)
    busy = max(days, key=lambda x: x["contributionCount"])
    streak = 0
    for x in reversed(days):
        if x["contributionCount"] > 0:
            streak += 1
        else:
            break
    months = OrderedDict()
    for x in days:
        y, m, _ = x["date"].split("-")
        months[(int(y), int(m))] = months.get((int(y), int(m)), 0) + x["contributionCount"]
    return active, busy, streak, list(months.items())[-12:]

def level(c):
    return 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 9 else 4

def _br(iso):
    y, m, d = iso.split("-"); return "%s/%s" % (d, m)

# ---------------- HERO ----------------
def c_hero(prof):
    W, H = 880, 300
    name = (prof.get("name") or LOGIN).split()
    first = name[0]
    rest = " ".join(name[1:]) or ""
    st = style(
        '.eb{font:500 12px Mono;fill:%s;letter-spacing:2.5px}' % MUTE +
        '.n1{font:400 78px Serif;fill:%s}' % INK +
        '.n2{font:400 78px SerIt;fill:%s}' % INK +
        '.ds{font:500 16px Sans;fill:%s}' % MUTE +
        '.lk{font:500 12px Mono;fill:%s;letter-spacing:.5px}' % BRAND +
        '.ax{font:500 7px Mono;fill:%s;letter-spacing:0;white-space:pre}' % FAINT)
    g = [st]  # hero sem caixa: flutua transparente sobre o perfil
    # eyebrow
    g.append('<rect x="46" y="40" width="9" height="9" fill="%s" style="%s"/>' % (BRAND, reveal("0.05", "pop")))
    g.append('<text class="eb" x="64" y="49" style="%s">%s</text>' % (reveal("0.1", "fade"), esc(EYEBROW)))
    # nome (duas linhas; última letra azul)
    g.append('<text class="n1" x="44" y="138" style="%s">%s</text>' % (reveal("0.18"), esc(first)))
    if rest:
        head, last = rest[:-1], rest[-1]
        g.append('<text class="n2" x="44" y="214" style="%s"><tspan>%s</tspan><tspan fill="%s">%s</tspan></text>'
                 % (reveal("0.3"), esc(head), BRAND, esc(last)))
        # brilho azul passando no sobrenome (SMIL, decorativo)
        if not STATIC:
            g.append('<clipPath id="shn"><rect x="44" y="172" width="430" height="56"/></clipPath>')
            g.append('<g clip-path="url(#shn)"><rect x="-140" y="172" width="80" height="56" fill="#fff" opacity="0.5">'
                     '<animate attributeName="x" from="-140" to="560" dur="2.4s" begin="1s" repeatCount="indefinite"/>'
                     '</rect></g>')
    # descrição + link
    g.append('<text class="ds" x="46" y="252" style="%s">%s</text>' % (reveal("0.42", "fade"), esc(DESC[0])))
    if len(DESC) > 1:
        g.append('<text class="ds" x="46" y="274" style="%s">%s</text>' % (reveal("0.48", "fade"), esc(DESC[1])))
    g.append('<text class="lk" x="46" y="294" style="%s">github.com/%s ↗</text>' % (reveal("0.54", "fade"), LOGIN))
    # retrato ASCII (direita)
    rows = ascii_rows(cols=66)
    fs = 7.0; lh = 7.0
    block_h = len(rows) * lh
    x0 = W - 300
    y0 = (H - block_h) / 2 + fs
    for i, line in enumerate(rows):
        d = "" if STATIC else "opacity:0;animation:fade .25s ease forwards;animation-delay:%ss" % round(0.3 + i * 0.018, 3)
        g.append('<text class="ax" x="%d" y="%.1f" style="%s" xml:space="preserve">%s</text>'
                 % (x0, y0 + i * lh, d, esc(line)))
    card("hero.svg", W, H, "".join(g))

# ---------------- TILES ----------------
def c_tile(name, title, sub, delay, icon):
    W, H = 286, 120
    st = style(
        '.t{font:500 14px Mono;fill:%s;letter-spacing:2px}' % INK +
        '.s{font:500 12px Sans;fill:%s}' % MUTE +
        '.sh{animation:shine 3.6s ease-in-out infinite}')
    g = [st, panel(W, H)]
    g.append('<rect x="0" y="0" width="4" height="%d" rx="2" fill="%s"/>' % (H, BRAND))
    g.append(icon)
    g.append('<text class="t" x="24" y="76" style="%s">%s</text>' % (reveal(delay), title))
    g.append('<text class="s" x="24" y="98" style="%s">%s</text>' % (reveal(str(float(delay) + .08)), esc(sub)))
    if not STATIC:
        g.append('<clipPath id="c"><rect width="%d" height="%d" rx="18"/></clipPath>' % (W, H))
        g.append('<g clip-path="url(#c)"><rect class="sh" x="-120" y="0" width="70" height="%d" fill="%s" opacity="0.06"/></g>' % (H, BRAND))
    card(name, W, H, "".join(g))

IC_CODE = '<g transform="translate(236,34)" stroke="%s" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round"><path d="M8 4 L0 12 L8 20 M24 4 L32 12 L24 20"/></g>' % BRAND
IC_NET  = '<g transform="translate(236,30)" stroke="%s" stroke-width="2.5" fill="none"><circle cx="2" cy="14" r="5"/><circle cx="30" cy="4" r="5"/><circle cx="30" cy="26" r="5"/><path d="M7 11 L25 5 M7 17 L25 25"/></g>' % BRAND
IC_CUP  = '<g transform="translate(234,30)" stroke="%s" stroke-width="2.5" fill="none" stroke-linecap="round"><path d="M2 6 h22 v12 a9 9 0 0 1 -9 9 h-4 a9 9 0 0 1 -9 -9 z"/><path d="M24 10 h5 a5 5 0 0 1 0 10 h-5"/></g>' % BRAND

# ---------------- GRÁFICO ----------------
def c_graph(days):
    cell, gap, padx, pady = 12, 3, 24, 52
    total = sum(x["contributionCount"] for x in days)
    ncols = (len(days) // 7) + 2
    W = padx * 2 + ncols * (cell + gap)
    H = pady + 7 * (cell + gap) + 18
    st = style(
        '.t{font:500 13px Mono;fill:%s;letter-spacing:1.5px}' % INK +
        '.n{font:400 26px Serif;fill:%s}' % BRAND +
        '.c{opacity:%s}' % ("1" if STATIC else "0") +
        ('' if STATIC else '.c{animation:pop .4s ease forwards}'))
    g = [st, panel(W, H)]
    g.append('<text class="t" x="%d" y="32">CONTRIBUIÇÕES</text>' % padx)
    g.append('<text class="n" x="%d" y="34" text-anchor="end">%d</text>' % (W - padx, total))
    col = 0
    for i, x in enumerate(days):
        wd = x["weekday"]
        xx = padx + col * (cell + gap); yy = pady + wd * (cell + gap)
        cx, cy = xx + cell / 2, yy + cell / 2
        stt = "" if STATIC else 'transform-origin:%spx %spx;animation-delay:%ss' % (cx, cy, round(i * 0.0015, 4))
        g.append('<rect class="c" x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s" style="%s"/>'
                 % (xx, yy, cell, cell, HEAT[level(x["contributionCount"])], stt))
        if wd == 6:
            col += 1
    card("graph.svg", W, H, "".join(g))

# ---------------- MESES + STATS ----------------
def c_months(days, mitems, active, busy, streak):
    W, H = 880, 250
    padx, top = 32, 58
    chart_h = 104; base = top + chart_h
    mx = max((v for _, v in mitems), default=1) or 1
    bw = (W - padx * 2) / max(len(mitems), 1)
    bestv = max((v for _, v in mitems), default=0)
    st = style(
        '.t{font:500 13px Mono;fill:%s;letter-spacing:1.5px}' % INK +
        '.lab{font:500 11px Mono;fill:%s}' % MUTE +
        '.val{font:500 11px Sans;fill:%s}' % INK +
        '.bar{%s}' % ("" if STATIC else 'transform-origin:center bottom;animation:grow .7s ease forwards') +
        '.sv{font:400 34px Serif;fill:%s}' % BRAND +
        '.sl{font:500 11px Mono;fill:%s}' % MUTE)
    g = [st, panel(W, H)]
    g.append('<text class="t" x="%d" y="34">CONTRIBUIÇÕES POR MÊS</text>' % padx)
    for i, ((yy, mm), v) in enumerate(mitems):
        bh = max(3, round(chart_h * (v / mx)))
        bx = padx + i * bw + bw * 0.2; bwid = bw * 0.6
        color = BRAND if v == bestv and v > 0 else "#30363d"
        stt = "" if STATIC else 'animation-delay:%ss' % round(0.3 + i * 0.05, 3)
        g.append('<rect class="bar" x="%.1f" y="%d" width="%.1f" height="%d" rx="3" fill="%s" style="%s"/>'
                 % (bx, base - bh, bwid, bh, color, stt))
        g.append('<text class="lab" x="%.1f" y="%d" text-anchor="middle">%s</text>' % (bx + bwid / 2, base + 16, MESES[mm - 1]))
        if v == bestv and v > 0:
            g.append('<text class="val" x="%.1f" y="%d" text-anchor="middle">%d</text>' % (bx + bwid / 2, base - bh - 6, v))
    sy = base + 56
    cells = [("%d" % streak, "SEQUÊNCIA (DIAS)"),
             ("%d" % active, "DIAS ATIVOS"),
             ("%d" % busy["contributionCount"], "RECORDE · %s" % _br(busy["date"]))]
    cw = (W - padx * 2) / 3
    for i, (val, lab) in enumerate(cells):
        cx = padx + i * cw + 4
        if i > 0:
            g.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (cx - 10, sy - 26, cx - 10, sy + 12, LINE))
        d = reveal(str(0.9 + i * 0.1))
        g.append('<text class="sv" x="%.1f" y="%d" style="%s">%s</text>' % (cx, sy, d, esc(val)))
        g.append('<text class="sl" x="%.1f" y="%d" style="%s">%s</text>' % (cx, sy + 20, d, esc(lab)))
    card("months.svg", W, H, "".join(g))

# ---------------- REPO CARDS ----------------
def _wrap(text, n):
    out, line = [], ""
    for w in text.split():
        if len(line) + len(w) + 1 > n:
            out.append(line); line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out

def c_repo(i, repo):
    W, H = 430, 132
    accent = repo.get("langColor") or BRAND
    st = style(
        '.n{font:500 17px Mono;fill:%s}' % INK +
        '.d{font:500 12px Sans;fill:%s}' % MUTE +
        '.m{font:500 11px Mono;fill:%s;letter-spacing:.5px}' % MUTE +
        '.dot{animation:blink 2s ease-in-out infinite}')
    g = [st, panel(W, H)]
    g.append('<rect x="0" y="0" width="4" height="%d" rx="2" fill="%s"/>' % (H, accent))
    delay = round(0.9 + i * 0.12, 3)
    g.append('<text class="n" x="24" y="42" style="%s">%s</text>' % (reveal(str(delay)), esc(repo["name"])))
    for li, line in enumerate(_wrap(repo.get("description") or "", 48)[:2]):
        g.append('<text class="d" x="24" y="%d" style="%s">%s</text>' % (68 + li * 18, reveal(str(delay + .08)), esc(line)))
    y = H - 20
    if repo.get("language"):
        g.append('<circle class="dot" cx="30" cy="%d" r="5" fill="%s"/>' % (y - 4, accent))
        g.append('<text class="m" x="42" y="%d">%s</text>' % (y, esc(repo["language"])))
    g.append('<text class="m" x="%d" y="%d" text-anchor="end">%d STARS · %d FORKS</text>'
             % (W - 20, y, repo.get("stars", 0), repo.get("forks", 0)))
    card("repo_%d.svg" % (i + 1), W, H, "".join(g))

def main():
    os.makedirs(CARDS, exist_ok=True)
    d, days = load()
    prof = d["profile"]
    active, busy, streak, mitems = stats(days)
    print("render (STATIC=%s)..." % STATIC)
    c_hero(prof)
    c_tile("tile_code.svg", "PROJETOS", "%d repositórios" % prof.get("publicRepos", 0), "0.3", IC_CODE)
    c_tile("tile_net.svg",  "LINKEDIN", "/in/nunesboraso", "0.38", IC_NET)
    c_tile("tile_cafe.svg", "SOBRE", "%d seguidores · café" % prof.get("followers", 0), "0.46", IC_CUP)
    c_graph(days)
    c_months(days, mitems, active, busy, streak)
    for i, repo in enumerate(d.get("featured", [])):
        c_repo(i, repo)
    print("ok: %d cards" % len(os.listdir(CARDS)))

if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Renderiza os cards SVG animados do perfil em cards/.

Lê data/contributions.json (atualizado pela Action). Fontes Instrument Serif
(nome) e Space Grotesk (texto) são subsetadas com fontTools e embutidas como
WOFF base64 — funciona dentro de <img>, que é como o GitHub mostra o README.

Animação: keyframes CSS (desligados em prefers-reduced-motion) + alguns
<animate> SMIL decorativos. STATIC=1 rende o quadro final (sem animação)
pra tirar print antes de commitar.

Único knob importante: BRAND (cor de marca) logo abaixo.
"""
import os, io, json, base64, html
from collections import OrderedDict

# ---------------- CONFIG ----------------
BRAND   = "#2F81F7"          # cor de marca — troque aqui
BRAND_2 = "#7cc0ff"
BG      = "#0d1117"
PANEL   = "#161b22"
STROKE  = "#21262d"
INK     = "#e6edf3"
MUTE    = "#8b949e"
HEAT    = ["#161b22", "#0b2a5e", "#15489c", BRAND, BRAND_2]  # 5 níveis
LOGIN   = "MatheusNunesBoraso"
STATIC  = os.environ.get("STATIC") == "1"

HERE   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CARDS  = os.path.join(HERE, "cards")
ASSETS = os.path.join(HERE, "assets")
DATA   = os.path.join(HERE, "data", "contributions.json")

MESES = ["jan", "fev", "mar", "abr", "mai", "jun",
         "jul", "ago", "set", "out", "nov", "dez"]
SUBSET = ("ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789 "
          ".,:;!?@#%&*()[]{}/+-_='\"…·—“”áàâãéêíóôõúüçÁÀÂÃÉÊÍÓÔÕÚÜÇ")

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

print("subset de fontes...")
SERIF = _woff_b64(os.path.join(ASSETS, "fonts", "InstrumentSerif-Regular.ttf"), SUBSET)
SANS  = _woff_b64(os.path.join(ASSETS, "fonts", "SpaceGrotesk.ttf"), SUBSET, wght=600)

def _avatar_b64():
    p = os.path.join(ASSETS, "avatar.jpg")
    if not os.path.exists(p):
        return None
    return base64.b64encode(open(p, "rb").read()).decode()
AVATAR = _avatar_b64()

FONTFACE = (
    '@font-face{{font-family:Serif;src:url(data:font/woff;base64,{serif}) format("woff")}}'
    '@font-face{{font-family:Sans;src:url(data:font/woff;base64,{sans}) format("woff")}}'
).format(serif=SERIF, sans=SANS)

KEYFRAMES = (
    '@keyframes rise{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:translateY(0)}}'
    '@keyframes pop{from{opacity:0;transform:scale(.4)}to{opacity:1;transform:scale(1)}}'
    '@keyframes grow{from{transform:scaleY(0)}to{transform:scaleY(1)}}'
    '@keyframes shine{0%,55%{transform:translateX(-140%)}100%{transform:translateX(360%)}}'
    '@keyframes blink{0%,100%{opacity:.3}50%{opacity:1}}'
)
REDUCED = ('@media (prefers-reduced-motion:reduce){*{animation:none!important;'
           'transform:none!important;opacity:1!important}}')

def style(extra=""):
    """Bloco <style> comum a todo card. Em STATIC, sem keyframes."""
    body = FONTFACE
    if not STATIC:
        body += KEYFRAMES
    body += extra
    body += REDUCED
    return "<style>" + body + "</style>"

def reveal(delay, kind="rise"):
    """estilo inline de entrada; em STATIC já nasce no estado final."""
    if STATIC:
        return ""
    return "opacity:0;animation:%s .6s ease forwards;animation-delay:%ss" % (kind, delay)

def esc(t):
    return html.escape(str(t), quote=True)

def card(name, w, h, inner):
    doc = ('<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" '
           'viewBox="0 0 %d %d" fill="none" role="img">%s</svg>') % (w, h, w, h, inner)
    open(os.path.join(CARDS, name), "w", encoding="utf-8").write(doc)
    print("  ->", name)

def panel(w, h):
    return ('<rect x="0" y="0" width="%d" height="%d" rx="16" fill="%s" stroke="%s"/>'
            % (w, h, PANEL, STROKE))

# ---------------- DADOS ----------------
def load():
    d = json.load(open(DATA, encoding="utf-8"))
    days = []
    for wk in d["calendar"]["weeks"]:
        for dd in wk["contributionDays"]:
            days.append(dd)
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
    mitems = list(months.items())[-12:]
    return active, busy, streak, mitems

# ---------------- CARDS ----------------
def level(c):
    return 0 if c == 0 else 1 if c <= 2 else 2 if c <= 5 else 3 if c <= 9 else 4

def c_hero(prof):
    W, H = 840, 230
    name = prof.get("name") or LOGIN
    bio = (prof.get("bio") or "").strip('"').strip()
    sub = 'Dev @ Netbil Educacional · Next.js · React Native · Node.js · ☕'
    sub = sub.replace("☕", "cafe")  # sem emoji nas fontes subsetadas
    st = style(
        '.name{font:400 64px Serif;fill:%s}' % INK +
        '.bio{font:600 18px Sans;fill:%s}' % BRAND +
        '.sub{font:600 14px Sans;fill:%s}' % MUTE)
    g = [st, panel(W, H)]
    g.append('<rect x="0" y="0" width="6" height="%d" rx="3" fill="%s"/>' % (H, BRAND))
    # retrato opcional
    px = 0
    if AVATAR:
        px = 150
        g.append('<clipPath id="av"><circle cx="118" cy="115" r="66"/></clipPath>')
        g.append('<circle cx="118" cy="115" r="70" fill="none" stroke="%s" stroke-width="3"/>' % BRAND)
        g.append('<image href="data:image/jpeg;base64,%s" x="52" y="49" width="132" height="132" '
                 'clip-path="url(#av)" style="%s"/>' % (AVATAR, reveal("0.05", "pop")))
    x0 = 44 + px
    g.append('<text class="name" x="%d" y="110" style="%s">%s</text>' % (x0, reveal("0.1"), esc(name)))
    if bio:
        g.append('<text class="bio" x="%d" y="150" style="%s">%s</text>' % (x0, reveal("0.25"), esc('"' + bio + '"')))
    g.append('<text class="sub" x="%d" y="182" style="%s">%s</text>' % (x0, reveal("0.4"), esc(sub)))
    # acento SMIL (decorativo)
    if not STATIC:
        g.append('<line x1="%d" y1="196" x2="%d" y2="196" stroke="%s" stroke-width="2">'
                 '<animate attributeName="x2" from="%d" to="%d" dur="0.8s" begin="0.5s" fill="freeze"/>'
                 '</line>' % (x0, x0, BRAND, x0, x0 + 300))
    else:
        g.append('<line x1="%d" y1="196" x2="%d" y2="196" stroke="%s" stroke-width="2"/>' % (x0, x0 + 300, BRAND))
    card("hero.svg", W, H, "".join(g))

def c_tile(name, title, sub, accent, delay, icon):
    W, H = 262, 118
    st = style(
        '.t{font:600 15px Sans;fill:%s;letter-spacing:2px}' % accent +
        '.s{font:600 12px Sans;fill:%s}' % MUTE +
        '.sh{animation:shine 3.4s ease-in-out infinite}')
    g = [st, panel(W, H)]
    g.append('<rect x="0" y="0" width="%d" height="4" rx="2" fill="%s"/>' % (W, accent))
    g.append(icon % accent)
    g.append('<text class="t" x="22" y="74" style="%s">%s</text>' % (reveal(delay), title))
    g.append('<text class="s" x="22" y="96" style="%s">%s</text>' % (reveal(str(float(delay) + .1)), esc(sub)))
    if not STATIC:
        g.append('<clipPath id="c"><rect width="%d" height="%d" rx="16"/></clipPath>' % (W, H))
        g.append('<g clip-path="url(#c)"><rect class="sh" x="-120" y="0" width="60" height="%d" '
                 'fill="#fff" opacity="0.05"/></g>' % H)
    card(name, W, H, "".join(g))

def c_graph(days):
    cell, gap, padx, pady = 11, 3, 22, 50
    weeks = (len(days) + 6) // 7
    cols = OrderedDict()
    for x in days:
        y, m, dd = x["date"].split("-")
        cols.setdefault(x["date"], x)
    # reconstrói por semana a partir da ordem
    W = padx * 2 + ((len(days) // 7) + 2) * (cell + gap)
    H = pady + 7 * (cell + gap) + 16
    total = sum(x["contributionCount"] for x in days)
    st = style(
        '.t{font:600 16px Sans;fill:%s}' % INK +
        '.n{font:600 16px Sans;fill:%s}' % BRAND +
        '.c{opacity:%s}' % ("1" if STATIC else "0") +
        ('' if STATIC else '.c{animation:pop .4s ease forwards}'))
    g = [st, panel(W, H)]
    g.append('<text class="t" x="%d" y="30">Contribuições</text>' % padx)
    g.append('<text class="n" x="%d" y="30" text-anchor="end">%d no último ano</text>' % (W - padx, total))
    col = 0; wd = days[0]["weekday"]
    # começa alinhado ao primeiro weekday
    idx = 0
    for x in days:
        wd = x["weekday"]
        xx = padx + col * (cell + gap)
        yy = pady + wd * (cell + gap)
        d = round(idx * 0.0016, 4)
        lv = level(x["contributionCount"])
        cx, cy = xx + cell / 2, yy + cell / 2
        stt = "" if STATIC else 'transform-origin:%spx %spx;animation-delay:%ss' % (cx, cy, d)
        g.append('<rect class="c" x="%d" y="%d" width="%d" height="%d" rx="2.5" fill="%s" style="%s"/>'
                 % (xx, yy, cell, cell, HEAT[lv], stt))
        idx += 1
        if wd == 6:
            col += 1
    card("graph.svg", W, H, "".join(g))

def c_months(days, mitems, active, busy, streak):
    W, H = 840, 240
    padx, top = 30, 54
    chart_w, chart_h = W - padx * 2, 110
    base = top + chart_h
    mx = max((v for _, v in mitems), default=1) or 1
    bw = chart_w / max(len(mitems), 1)
    st = style(
        '.t{font:600 16px Sans;fill:%s}' % INK +
        '.lab{font:600 11px Sans;fill:%s}' % MUTE +
        '.val{font:600 11px Sans;fill:%s}' % INK +
        '.bar{%s}' % ("" if STATIC else 'transform-origin:center bottom;animation:grow .7s ease forwards') +
        '.sv{font:600 30px Sans;fill:%s}' % BRAND +
        '.sl{font:600 11px Sans;fill:%s}' % MUTE)
    g = [st, panel(W, H)]
    g.append('<text class="t" x="%d" y="32">Contribuições por mês</text>' % padx)
    bestv = max((v for _, v in mitems), default=0)
    for i, ((yy, mm), v) in enumerate(mitems):
        bh = max(3, round(chart_h * (v / mx)))
        bx = padx + i * bw + bw * 0.18
        bwid = bw * 0.64
        color = BRAND if v == bestv and v > 0 else "#30363d"
        delay = round(0.3 + i * 0.05, 3)
        stt = "" if STATIC else 'animation-delay:%ss' % delay
        g.append('<rect class="bar" x="%.1f" y="%d" width="%.1f" height="%d" rx="3" fill="%s" style="%s"/>'
                 % (bx, base - bh, bwid, bh, color, stt))
        g.append('<text class="lab" x="%.1f" y="%d" text-anchor="middle">%s</text>'
                 % (bx + bwid / 2, base + 16, MESES[mm - 1]))
        if v == bestv and v > 0:
            g.append('<text class="val" x="%.1f" y="%d" text-anchor="middle">%d</text>'
                     % (bx + bwid / 2, base - bh - 6, v))
    # linha de stats
    sy = base + 54
    cells = [("%d dias" % streak, "sequência atual"),
             ("%d dias" % active, "dias ativos no ano"),
             ("%d" % busy["contributionCount"], "recorde em %s" % _br(busy["date"]))]
    cw = chart_w / 3
    for i, (val, lab) in enumerate(cells):
        cx = padx + i * cw + 6
        if i > 0:
            g.append('<line x1="%.1f" y1="%d" x2="%.1f" y2="%d" stroke="%s"/>' % (cx - 6, sy - 24, cx - 6, sy + 10, STROKE))
        d = reveal(str(0.9 + i * 0.1))
        g.append('<text class="sv" x="%.1f" y="%d" style="%s">%s</text>' % (cx, sy, d, esc(val)))
        g.append('<text class="sl" x="%.1f" y="%d" style="%s">%s</text>' % (cx, sy + 20, d, esc(lab)))
    card("months.svg", W, H, "".join(g))

def _br(iso):
    y, m, d = iso.split("-")
    return "%s/%s" % (d, m)

def c_repo(i, repo):
    W, H = 410, 130
    accent = repo.get("langColor") or BRAND
    st = style(
        '.n{font:600 17px Sans;fill:%s}' % INK +
        '.d{font:600 12px Sans;fill:%s}' % MUTE +
        '.m{font:600 12px Sans;fill:%s}' % MUTE +
        '.dot{animation:blink 2s ease-in-out infinite}')
    g = [st, panel(W, H)]
    g.append('<rect x="0" y="0" width="5" height="%d" rx="2.5" fill="%s"/>' % (H, accent))
    delay = round(0.9 + i * 0.12, 3)
    g.append('<text class="n" x="24" y="40" style="%s">%s</text>' % (reveal(str(delay)), esc(repo["name"])))
    desc = repo.get("description") or ""
    for li, line in enumerate(_wrap(desc, 46)[:2]):
        g.append('<text class="d" x="24" y="%d" style="%s">%s</text>'
                 % (66 + li * 18, reveal(str(delay + .08)), esc(line)))
    # rodapé: linguagem + estrelas/forks
    y = H - 20
    lang = repo.get("language")
    if lang:
        g.append('<circle class="dot" cx="30" cy="%d" r="5" fill="%s"/>' % (y - 4, accent))
        g.append('<text class="m" x="42" y="%d">%s</text>' % (y, esc(lang)))
    g.append('<text class="m" x="%d" y="%d" text-anchor="end">%d estrelas · %d forks</text>'
             % (W - 20, y, repo.get("stars", 0), repo.get("forks", 0)))
    card("repo_%d.svg" % (i + 1), W, H, "".join(g))

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

# ícones simples por tile (path desenhado, sem fonte de emoji)
IC_CODE = '<path d="M30 40 l-12 12 l12 12 M54 40 l12 12 l-12 12" stroke="%s" stroke-width="3" fill="none" stroke-linecap="round" stroke-linejoin="round"/>'
IC_NET  = '<g stroke="%s" stroke-width="3" fill="none"><circle cx="24" cy="46" r="6"/><circle cx="56" cy="34" r="6"/><circle cx="56" cy="60" r="6"/><path d="M30 43 L50 36 M30 49 L50 58"/></g>'
IC_CUP  = '<g stroke="%s" stroke-width="3" fill="none" stroke-linecap="round"><path d="M22 38 h26 v14 a10 10 0 0 1 -10 10 h-6 a10 10 0 0 1 -10 -10 z"/><path d="M48 42 h6 a6 6 0 0 1 0 12 h-6"/></g>'

def main():
    os.makedirs(CARDS, exist_ok=True)
    d, days = load()
    prof = d["profile"]
    active, busy, streak, mitems = stats(days)
    print("render (STATIC=%s)..." % STATIC)
    c_hero(prof)
    c_tile("tile_code.svg", "PROJETOS", "%d repositórios" % prof.get("publicRepos", 0), BRAND, "0.3", IC_CODE)
    c_tile("tile_net.svg",  "LINKEDIN", "/in/nunesboraso", "#58a6ff", "0.38", IC_NET)
    c_tile("tile_cafe.svg", "SOBRE", "%d seguidores · café" % prof.get("followers", 0), "#e3b341", "0.46", IC_CUP)
    c_graph(days)
    c_months(days, mitems, active, busy, streak)
    for i, repo in enumerate(d.get("featured", [])):
        c_repo(i, repo)
    print("ok: %d cards em cards/" % len(os.listdir(CARDS)))

if __name__ == "__main__":
    main()

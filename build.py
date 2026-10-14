# -*- coding: utf-8 -*-
"""把 data/{date}.json 渲染成 site/{date}.html 并重建 site/index.html。
若环境变量 SITE_PASS 存在，则给所有页面加一道口令门（防君子不防小人，个人用途足够）。
"""
import json, glob, os, re, html as H, hashlib, datetime

SITE = os.path.join("site"); os.makedirs(SITE, exist_ok=True)

LOCK_TMPL = """
<div id="lock" style="position:fixed;inset:0;background:#f6f5f1;z-index:99;display:flex;flex-direction:column;align-items:center;justify-content:center;font-family:sans-serif">
  <div style="background:#fff;border:1px solid #ddd;border-radius:12px;padding:28px 32px;width:280px;text-align:center">
    <div style="font-size:18px;font-weight:700;margin-bottom:4px">官媒日报</div>
    <div style="font-size:12px;color:#999;margin-bottom:16px">私人阅读，请输入访问口令</div>
    <input id="pw" type="password" placeholder="口令" style="width:100%;padding:9px 10px;border:1px solid #ccc;border-radius:8px;font-size:15px">
    <button onclick="go()" style="margin-top:12px;width:100%;padding:9px;background:#c7000b;color:#fff;border:0;border-radius:8px;font-size:15px">进入</button>
    <div id="err" style="color:#c7000b;font-size:12px;margin-top:8px"></div>
  </div>
</div>
<script>
const HASH = "__HASH__";
document.getElementById("app").style.display = "none";
async function go() {
  const v = document.getElementById("pw").value;
  const h = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(v));
  const hex = [...new Uint8Array(h)].map(b => b.toString(16).padStart(2, "0")).join("");
  if (hex === HASH) { document.getElementById("lock").remove(); document.getElementById("app").style.display = ""; }
  else { document.getElementById("err").textContent = "口令错误"; }
}
document.getElementById("pw").addEventListener("keydown", e => { if (e.key === "Enter") go(); });
</script>
"""

PAGE_TMPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>官媒日报 · __DATE__</title>
<style>
:root{--bg:#f6f5f1;--card:#fff;--ink:#1a1a1a;--sub:#666;--line:#e5e2da;--red:#c7000b;--tag:#f2e8e6}
*{margin:0;padding:0;box-sizing:border-box;-webkit-tap-highlight-color:transparent}
body{font-family:-apple-system,"PingFang SC","Noto Sans CJK SC",sans-serif;background:var(--bg);color:var(--ink);line-height:1.75}
.wrap{max-width:640px;margin:0 auto;padding:0 14px 60px}
header{padding:26px 0 14px;border-bottom:3px double var(--red);margin-bottom:6px}
header .kicker{font-size:12px;letter-spacing:4px;color:var(--red);font-weight:700}
header h1{font-size:26px;font-weight:800;margin-top:4px}
header .meta{font-size:12px;color:var(--sub);margin-top:6px}
nav{position:sticky;top:0;z-index:9;background:rgba(246,245,241,.96);backdrop-filter:blur(6px);display:flex;gap:8px;overflow-x:auto;padding:10px 0;border-bottom:1px solid var(--line)}
nav a{flex:0 0 auto;font-size:13px;text-decoration:none;color:var(--ink);background:var(--card);border:1px solid var(--line);border-radius:999px;padding:5px 13px}
section{margin-top:26px}
.paper-head{display:flex;align-items:baseline;gap:10px;border-left:5px solid var(--red);padding-left:10px;margin-bottom:12px;flex-wrap:wrap}
.paper-head h2{font-size:19px}
.paper-head .date{font-size:12px;color:var(--sub)}
.paper-head .badge{font-size:11px;color:var(--red);background:var(--tag);border-radius:4px;padding:1px 7px}
article{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:13px 15px;margin-bottom:10px}
article h3{font-size:16.5px;line-height:1.5;margin-bottom:5px}
article p{font-size:14.5px;color:#333}
article .src{display:block;margin-top:7px;font-size:12px;color:var(--sub)}
article .src a{color:#8a8a8a;text-decoration:none;border-bottom:1px dotted #bbb}
.note{font-size:12px;color:var(--sub);background:#fffbe8;border:1px dashed #e0cf8f;border-radius:8px;padding:9px 12px;margin:12px 0}
footer{margin-top:36px;padding-top:14px;border-top:1px solid var(--line);font-size:11.5px;color:#999;line-height:1.8}
</style>
</head>
<body>
<div class="wrap" id="app">
<header>
  <div class="kicker">每 日 官 媒 精 要</div>
  <h1>官媒日报</h1>
  <div class="meta">__DATE__ · 每天 07:00 自动更新 · <a href="index.html" style="color:var(--sub)">往期回顾</a></div>
</header>
<nav>__NAV__</nav>
__SECTIONS__
<footer>本页面为个人学习使用的阅读聚合，内容版权归原报社所有，每篇均附原文出处。</footer>
</div>
__LOCK__
</body>
</html>
"""

def esc(s): return H.escape(str(s or ""))

def build_day(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    date = data["date"]
    nav, sections = [], []
    order = ["人民日报", "湖北日报", "十堰日报", "竹山报"]
    for name in order:
        p = data["papers"].get(name, {"items": [], "date": None})
        items = p["items"]
        if not items: continue
        pid = {"人民日报": "rmrb", "湖北日报": "hbrb", "十堰日报": "syrb", "竹山报": "zsb"}[name]
        pdate = p.get("date") or date
        badge = "要闻" if name in ("人民日报", "湖北日报") else "全文"
        if name == "竹山报" and pdate != date:
            badge = "周刊 · 最新一期"
        nav.append(f'<a href="#{pid}">{name}</a>')
        arts = []
        for it in items:
            summ = f"<p>{esc(it.get('summary'))}</p>" if it.get("summary") else ""
            arts.append(f'<article><h3>{esc(it["title"])}</h3>{summ}'
                        f'<span class="src">{esc(it.get("src",""))} · <a href="{esc(it.get("url",""))}">原文</a></span></article>')
        sections.append(f'<section id="{pid}"><div class="paper-head"><h2>{name}</h2>'
                        f'<span class="date">{pdate}</span><span class="badge">{badge}</span></div>'
                        + "".join(arts) + "</section>")
    lock = ""
    pw = os.environ.get("SITE_PASS")
    if pw:
        lock = LOCK_TMPL.replace("__HASH__", hashlib.sha256(pw.encode()).hexdigest())
    page = (PAGE_TMPL.replace("__DATE__", date).replace("__NAV__", "".join(nav))
                     .replace("__SECTIONS__", "\n".join(sections)).replace("__LOCK__", lock))
    out = os.path.join(SITE, f"{date}.html")
    with open(out, "w", encoding="utf-8") as f:
        f.write(page)
    print("built:", out)

def build_index():
    days = sorted((os.path.basename(p)[:-5] for p in glob.glob(os.path.join(SITE, "20*.html"))), reverse=True)
    lis = "\n".join(f'<li><a href="{d}.html">{d}</a></li>' for d in days)
    page = f"""<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0"><title>官媒日报 · 往期</title>
<style>body{{font-family:-apple-system,"PingFang SC",sans-serif;max-width:640px;margin:0 auto;padding:24px 16px;background:#f6f5f1}}
h1{{font-size:22px;border-bottom:3px double #c7000b;padding-bottom:10px}}ul{{list-style:none;padding:0}}li{{background:#fff;border:1px solid #e5e2da;border-radius:10px;margin:10px 0}}a{{display:block;padding:14px 16px;text-decoration:none;color:#1a1a1a;font-size:16px}}</style>
</head><body><h1>官媒日报 · 往期</h1><ul>{lis}</ul></body></html>"""
    with open(os.path.join(SITE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print("built: site/index.html", len(days), "days")

if __name__ == "__main__":
    for p in sorted(glob.glob("data/*.json")):
        build_day(p)
    build_index()

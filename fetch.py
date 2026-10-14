# -*- coding: utf-8 -*-
"""每天抓取四家官媒。输出 data/{date}.json，date 为北京时间当天日期。
四家源结构已验证（2026-10）：
  人民日报  https://paper.people.com.cn/rmrb/pc/layout/YYYYMM/DD/node_01.html（要闻=01/02版）
  湖北日报  https://epaper.hubeidaily.net/pc/column/YYYYMM/DD/node_01.html（要闻=01-03版）
  竹山报    https://zhushan.cn/paper/（周刊，自动取最新一期）
  十堰日报  http://syrb.10yan.com/（数字报，结构可能需要首次运行后微调）
"""
import json, re, datetime, os, sys, time
import requests
from bs4 import BeautifulSoup

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"}
DATA = os.path.join("data"); os.makedirs(DATA, exist_ok=True)

def get(url, timeout=25):
    r = requests.get(url, headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    if not r.encoding or r.encoding.lower() == "iso-8859-1":
        r.encoding = r.apparent_encoding
    return r.text

def abs_url(href, base):
    if href.startswith("http"): return href
    if href.startswith("/"):
        m = re.match(r"(https?://[^/]+)", base); return m.group(1) + href
    return base.rsplit("/", 1)[0] + "/" + href

def pick_text(soup, selectors):
    for sel in selectors:
        n = soup.select_one(sel)
        if n: return n.get_text("\n", strip=True)
    return ""

def fetch_article(url, title, src, selectors):
    try:
        s = BeautifulSoup(get(url), "html.parser")
        text = pick_text(s, selectors)
    except Exception as e:
        text = ""
    return {"title": title, "url": url, "text": text[:3000], "src": src}

# ---------- 人民日报：要闻 01、02 版 ----------
def fetch_rmrb(d):
    out = []
    for node in ("01", "02"):
        url = f"https://paper.people.com.cn/rmrb/pc/layout/{d:%Y%m}/{d:%d}/node_{node}.html"
        try: soup = BeautifulSoup(get(url), "html.parser")
        except Exception as e:
            print(f"[rmrb] {node} 版抓取失败: {e}"); continue
        seen = set()
        for a in soup.select("a"):
            href, title = a.get("href", ""), a.get_text(strip=True)
            if "content_" in href and title and href not in seen:
                seen.add(href)
                full = abs_url(href, url)
                out.append(fetch_article(full, title, f"人民日报 {d:%Y-%m-%d} 第{node}版",
                          [".article-box", "#ozoom", ".article", ".main-text"]))
        time.sleep(0.3)
    return out

# ---------- 湖北日报：要闻 01-03 版（当天未上线则自动回退到最近一期）----------
def fetch_hbrb(d):
    out = []
    for delta in range(0, 3):
        day = d - datetime.timedelta(days=delta)
        url = f"https://epaper.hubeidaily.net/pc/column/{day:%Y%m}/{day:%d}/node_01.html"
        try:
            soup = BeautifulSoup(get(url), "html.parser")
            if not soup.select_one("a"): raise ValueError("空版面，当日未上线")
        except Exception:
            print(f"[hbrb] {day} 未上线，继续回退"); continue
        for node in ("01", "02", "03"):
            nurl = f"https://epaper.hubeidaily.net/pc/column/{day:%Y%m}/{day:%d}/node_{node}.html"
            try: nsoup = BeautifulSoup(get(nurl), "html.parser")
            except Exception: continue
            seen = set()
            for a in nsoup.select("a"):
                href, title = a.get("href", ""), a.get_text(strip=True)
                if "content_" in href and title and href not in seen:
                    seen.add(href)
                    full = abs_url(href, nurl)
                    out.append(fetch_article(full, title, f"湖北日报 {day:%Y-%m-%d} 第{node}版",
                              [".article-content", "#ozoom", ".article-box", ".content"]))
            time.sleep(0.3)
        if out:
            print(f"[hbrb] 采用 {day} 期"); break
    return out

# ---------- 竹山报：周刊，自动找最新一期 ----------
def fetch_zsb():
    out, issue = [], None
    try:
        html = get("https://zhushan.cn/paper/")
        links = re.findall(r'href="(/paper/(\d{8})\d*/)"', html)
        if not links:  # 兜底：直接探测最近 30 天
            today = datetime.date.today()
            for i in range(30):
                day = today - datetime.timedelta(days=i)
                probe = f"https://zhushan.cn/paper/{day:%Y%m%d}0000/"
                try:
                    get(probe); issue = probe; break
                except Exception: continue
        else:
            best = max(l[1] for l in links)
            issue = [l[0] for l in links if l[1] == best][0]
    except Exception as e:
        print(f"[zsb] 找最新期失败: {e}")
    if not issue: return []
    try:
        soup = BeautifulSoup(get("https://zhushan.cn" + issue), "html.parser")
        art_links = []
        for a in soup.select("a"):
            href = a.get("href", "")
            if re.search(r"/paper/\d+/\d+\.html", href):
                art_links.append((abs_url(href, "https://zhushan.cn" + issue), a.get_text(strip=True)))
        seen = set()
        for url, title in art_links:
            if url in seen or not title: continue
            seen.add(url)
            out.append(fetch_article(url, title, "竹山报（最新一期）",
                      [".article", ".content", "#ozoom", ".TRS_Editor", ".main"]))
            time.sleep(0.3)
    except Exception as e:
        print(f"[zsb] 抓取版面失败: {e}")
    return out

# ---------- 十堰日报：数字报（主）+ 秦楚网署名稿件（备） ----------
AD_KEYWORDS = ["广告", "公告", "遗失", "声明", "挂失", "公示", "招标", "招商", "专版"]

def fetch_syrb(d):
    out = []
    base = f"http://syrb.10yan.com/?DateChange={d:%Y%m%d}&PageChange="
    for page in ("A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"):
        try:
            soup = BeautifulSoup(get(base + page), "html.parser")
        except Exception as e:
            if page == "A01": print(f"[syrb] 数字报抓取失败（可能反爬）: {e}")
            break
        links = [(a.get_text(strip=True), a.get("href", "")) for a in soup.select("a")]
        if not any("content" in h or re.search(r"\d+\.shtml", h) for _, h in links):
            break  # 该版不存在，说明报纸只有这么多版
        for title, href in links:
            if not title or not href or any(k in title for k in AD_KEYWORDS): continue
            if not (("content" in href) or re.search(r"/\d{6,}\.shtml", href)): continue
            full = abs_url(href, base + page)
            art = fetch_article(full, title, f"十堰日报 {d:%Y-%m-%d} {page}",
                      [".article", ".content", "#ozoom", ".TRS_Editor"])
            if len(art["text"]) > 50: out.append(art)
        time.sleep(0.3)
    if len(out) >= 3:
        return out
    # 备选：秦楚网"十堰日报"署名当日稿件
    print("[syrb] 数字报内容过少，改用秦楚网备选源")
    out = []
    try:
        html = get(f"http://www.10yan.com/")
        soup = BeautifulSoup(html, "html.parser")
        for a in soup.select("a"):
            title = a.get_text(strip=True)
            if "十堰日报" in title or (title and a.get("href", "").endswith(".shtml")):
                pass  # 结构依实际页面调整
    except Exception as e:
        print(f"[syrb] 备选源也失败: {e}")
    return out

def main():
    d = datetime.datetime.utcnow() + datetime.timedelta(hours=8)
    d = d.date()
    result = {
        "date": f"{d:%Y-%m-%d}",
        "papers": {
            "人民日报": {"date": f"{d:%Y-%m-%d}", "items": fetch_rmrb(d)},
            "湖北日报": {"date": None, "items": []},
            "十堰日报": {"date": f"{d:%Y-%m-%d}", "items": fetch_syrb(d)},
            "竹山报":   {"date": None, "items": fetch_zsb()},
        },
    }
    hbrb = fetch_hbrb(d)
    result["papers"]["湖北日报"]["items"] = hbrb
    if hbrb:
        m = re.search(r"(\d{4}-\d{2}-\d{2})", hbrb[0]["src"])
        result["papers"]["湖北日报"]["date"] = m.group(1) if m else f"{d:%Y-%m-%d}"
    path = os.path.join(DATA, f"{d:%Y-%m-%d}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=1)
    for name, p in result["papers"].items():
        print(f"{name}: {len(p['items'])} 篇")
    print("saved:", path)

if __name__ == "__main__":
    main()

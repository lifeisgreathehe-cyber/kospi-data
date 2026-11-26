"""Collect FOMC statements and Federal Reserve Board speeches (verbatim text).

Writes:
  data/fed/statements/YYYYMMDD.txt   FOMC statement text, one paragraph per line
  data/fed/statements/index.json     [{date, url, title}]
  data/fed/speeches/<slug>.txt       speech text
  data/fed/speeches/index.json       [{date, speaker, title, url, file}] newest first
The container that writes the Korean commentary cannot reach federalreserve.gov,
so this job (run by GitHub Actions) copies the public-domain text into the repo.
"""
import json, os, re, sys, time
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
import requests
from bs4 import BeautifulSoup

BASE = "https://www.federalreserve.gov"
UA = {"User-Agent": "Mozilla/5.0 (compatible; kospi-data fed collector; +https://github.com)"}
OUT = "data/fed"
SPEECH_DAYS = 60

def get(url):
    for i in range(3):
        try:
            r = requests.get(url, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.text
            print("HTTP", r.status_code, url)
        except Exception as e:
            print("ERR", e, url)
        time.sleep(3 * (i + 1))
    return None

def article_paras(html):
    soup = BeautifulSoup(html, "html.parser")
    art = soup.find(id="article") or soup
    for bad in art.select(".heading, .lastUpdate, script, style, .shareDL, .article__time"):
        bad.decompose()
    paras = []
    for p in art.find_all("p"):
        t = re.sub(r"\s+", " ", p.get_text(" ", strip=True)).strip()
        if not t:
            continue
        if t.startswith(("For media inquiries", "Implementation Note issued", "For release at")):
            continue
        paras.append(t)
    title = soup.find("h3", class_="title")
    return (title.get_text(strip=True) if title else ""), paras

def load(path, default):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return default

def save(path, obj):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def statements():
    d = f"{OUT}/statements"
    idx = load(f"{d}/index.json", [])
    have = {x["date"] for x in idx}
    links = set()
    feed = get(f"{BASE}/feeds/press_monetary.xml") or ""
    links |= set(re.findall(r"/newsevents/pressreleases/monetary(\d{8})a\.htm", feed))
    yr = datetime.now(timezone.utc).year
    for y in (yr - 1, yr):
        page = get(f"{BASE}/newsevents/pressreleases/{y}-press-fomc.htm") or ""
        links |= set(re.findall(r"monetary(\d{8})a\.htm", page))
    for date in sorted(links):
        if date in have or date < f"{yr-1}0101":
            continue
        url = f"{BASE}/newsevents/pressreleases/monetary{date}a.htm"
        html = get(url)
        if not html:
            continue
        title, paras = article_paras(html)
        if "FOMC statement" not in title:
            continue
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/{date}.txt", "w") as f:
            f.write("\n\n".join(paras) + "\n")
        idx.append({"date": date, "url": url, "title": title})
        print("statement", date, len(paras), "paras")
    idx.sort(key=lambda x: x["date"])
    save(f"{d}/index.json", idx)

def speeches():
    d = f"{OUT}/speeches"
    idx = load(f"{d}/index.json", [])
    have = {x["url"] for x in idx}
    feed = get(f"{BASE}/feeds/speeches.xml")
    if not feed:
        return
    soup = BeautifulSoup(feed, "xml")
    cutoff = datetime.now(timezone.utc) - timedelta(days=SPEECH_DAYS)
    for it in soup.find_all("item"):
        url = it.link.get_text(strip=True)
        if url.startswith("/"):
            url = BASE + url
        try:
            dt = parsedate_to_datetime(it.pubDate.get_text(strip=True))
        except Exception:
            continue
        if dt < cutoff or url in have:
            continue
        title = it.title.get_text(strip=True)
        speaker = (it.description.get_text(strip=True) if it.description else "")
        html = get(url)
        if not html:
            continue
        soup2 = BeautifulSoup(html, "html.parser")
        sp = soup2.find(class_="speaker")
        if sp:
            speaker = sp.get_text(" ", strip=True)
        _, paras = article_paras(html)
        slug = re.sub(r"\.htm$", "", url.rsplit("/", 1)[-1])
        os.makedirs(d, exist_ok=True)
        with open(f"{d}/{slug}.txt", "w") as f:
            f.write("\n\n".join(paras) + "\n")
        idx.append({"date": dt.strftime("%Y-%m-%d"), "speaker": speaker, "title": title,
                    "url": url, "file": f"{slug}.txt"})
        print("speech", dt.date(), slug)
    idx.sort(key=lambda x: x["date"], reverse=True)
    save(f"{d}/index.json", idx)

if __name__ == "__main__":
    statements()
    speeches()

"""주식 리포트 생성기

사용:  python -I build.py data/2026-11-09.json
결과:
  reports/2026-11-09.html   그날 리포트
  index.html                최신 리포트 + 지난 리포트 목록
  kakao.txt                 카카오톡용 요약 (200자 이내)
"""
import html
import json
import os
import sys

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://kkhgold.github.io/stock-report/"

CSS = """
:root{--bg:#f6f8fb;--card:#fff;--text:#1d2330;--muted:#5d6676;--line:#e3e7ee;--accent:#2b6cb0;--up:#d63c3c;--down:#2a6fdb;--chip:#eef2f7}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#11151c;--card:#1a2029;--text:#e7ebf2;--muted:#9aa4b5;--line:#2a3240;--accent:#7fb3ec;--up:#ff6b6b;--down:#6aa7ff;--chip:#232b37}}
:root[data-theme="dark"]{--bg:#11151c;--card:#1a2029;--text:#e7ebf2;--muted:#9aa4b5;--line:#2a3240;--accent:#7fb3ec;--up:#ff6b6b;--down:#6aa7ff;--chip:#232b37}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Malgun Gothic","Noto Sans KR",sans-serif;line-height:1.55}
.wrap{max-width:760px;margin:0 auto;padding:20px 16px 48px}h1{font-size:1.5rem;margin:16px 0 2px}.sub{color:var(--muted);margin:0 0 16px}
h2{font-size:1.1rem;margin:24px 0 10px}.card{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px;margin-bottom:12px}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}.tile{background:var(--card);border:1px solid var(--line);border-radius:12px;padding:12px}
.tile .n{color:var(--muted);font-size:.85rem}.tile .v{font-size:1.3rem;font-weight:700;font-variant-numeric:tabular-nums}.tile .r{font-weight:600;font-variant-numeric:tabular-nums}
.up{color:var(--up)}.down{color:var(--down)}.flat{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:.95rem}th,td{padding:7px 4px;border-bottom:1px solid var(--line);text-align:left}td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}th{color:var(--muted);font-weight:600}
ul{margin:4px 0 0;padding-left:20px}li{margin:4px 0}.news li{font-size:.95rem}.t{color:var(--muted);font-size:.85rem;margin-right:6px}
.arch a{display:inline-block;background:var(--chip);color:var(--text);text-decoration:none;border-radius:999px;padding:4px 10px;margin:3px 4px 3px 0;font-size:.85rem}
footer{color:var(--muted);font-size:.8rem;margin-top:28px}
"""


def esc(x):
    return html.escape(str(x))


def cls(rate):
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return "flat"
    return "up" if r > 0 else "down" if r < 0 else "flat"


def pct(rate):
    try:
        r = float(rate)
    except (TypeError, ValueError):
        return "-"
    return f"{'▲' if r > 0 else '▼' if r < 0 else ''}{abs(r):.2f}%"


def num(v, digits=2):
    try:
        f = float(v)
    except (TypeError, ValueError):
        return esc(v)
    return f"{f:,.{digits}f}" if digits else f"{f:,.0f}"


def tiles(items, digits=2):
    out = []
    for it in items:
        out.append(
            f"<div class='tile'><div class='n'>{esc(it['name'])}</div>"
            f"<div class='v'>{num(it.get('price'), digits)}</div>"
            f"<div class='r {cls(it.get('rate'))}'>{pct(it.get('rate'))}"
            + (f" ({num(it['change'], digits)})" if it.get("change") not in (None, "") else "")
            + "</div></div>"
        )
    return "<div class='tiles'>" + "".join(out) + "</div>"


def table(rows):
    if not rows:
        return "<p class='t'>데이터 없음</p>"
    body = "".join(
        f"<tr><td>{esc(r['name'])}</td><td class='num'>{num(r.get('price'), 0)}</td>"
        f"<td class='num {cls(r.get('rate'))}'>{pct(r.get('rate'))}</td></tr>"
        for r in rows
    )
    return f"<table><tr><th>종목</th><th class='num'>현재가</th><th class='num'>등락률</th></tr>{body}</table>"


def render(d, archive):
    title = f"주식 리포트 {d['date']}"
    parts = [
        f"<h1>📈 {esc(title)}</h1>",
        f"<p class='sub'>{esc(d.get('weekday', ''))} {esc(d.get('generated_at', ''))} 기준 · 국내 장중 / 미국 전일 마감</p>",
    ]
    if d.get("summary"):
        parts.append("<h2>📝 오늘의 요약</h2><div class='card'><ul>" +
                     "".join(f"<li>{esc(s)}</li>" for s in d["summary"]) + "</ul></div>")
    parts.append("<h2>🇰🇷 국내 지수</h2>" + tiles(d.get("indices", [])))
    if d.get("us"):
        parts.append("<h2>🇺🇸 미국 · 환율 (전일 마감)</h2>" + tiles(d["us"]))
    parts.append("<h2>💰 거래대금 상위</h2><div class='card'>" + table(d.get("top_value", [])) + "</div>")
    if d.get("gainers") or d.get("losers"):
        parts.append("<h2>🔺 상승률 상위 (코스피)</h2><div class='card'>" + table(d.get("gainers", [])) + "</div>")
        parts.append("<h2>🔻 하락률 상위 (코스피)</h2><div class='card'>" + table(d.get("losers", [])) + "</div>")
    if d.get("news"):
        parts.append("<h2>📰 주요 뉴스</h2><div class='card news'><ul>" +
                     "".join(f"<li><span class='t'>{esc(n.get('time', ''))}</span>{esc(n['title'])}</li>" for n in d["news"]) +
                     "</ul></div>")
    if archive:
        parts.append("<h2>🗂 지난 리포트</h2><div class='arch'>" +
                     "".join(f"<a href='{SITE}reports/{a}.html'>{a}</a>" for a in archive) + "</div>")
    parts.append("<footer>데이터: 한국투자증권(KIS)·Yahoo Finance via PlayMCP. 투자 판단의 참고용이며 투자 권유가 아닙니다.</footer>")
    return (
        "<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
        "<meta name='viewport' content='width=device-width, initial-scale=1'>"
        f"<title>주식 리포트</title><meta name='description' content='{esc(title)}'>"
        f"<meta property='og:title' content='📈 {esc(title)}'>"
        f"<style>{CSS}</style></head><body><div class='wrap'>" + "".join(parts) + "</div></body></html>"
    )


def kakao_text(d):
    idx = " ".join(f"{i['name']} {num(i.get('price'))}({pct(i.get('rate'))})" for i in d.get("indices", [])[:2])
    top = ", ".join(f"{r['name']} {pct(r.get('rate'))}" for r in d.get("top_value", [])[:2])
    head = f"📈 {d['date'][5:].replace('-', '/')} 11시 주식 리포트\n{idx}\n💰 {top}\n"
    tail = f"🔗 {SITE}"
    room = 195 - len(head) - len(tail)
    summ = (d.get("summary") or [""])[0]
    if room > 10 and summ:
        head += "📝 " + (summ if len(summ) <= room - 4 else summ[: room - 5] + "…") + "\n"
    return head + tail


def main():
    src = sys.argv[1]
    with open(src, encoding="utf-8") as f:
        d = json.load(f)
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    archive = sorted(
        (n[:-5] for n in os.listdir(os.path.join(ROOT, "reports")) if n.endswith(".html")),
        reverse=True,
    )
    if d["date"] not in archive:
        archive = sorted(archive + [d["date"]], reverse=True)
    page = render(d, archive)
    for path in (os.path.join(ROOT, "reports", d["date"] + ".html"), os.path.join(ROOT, "index.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
    text = kakao_text(d)
    with open(os.path.join(ROOT, "kakao.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"\n({len(text)}자)")


if __name__ == "__main__":
    main()

"""오늘의 코스피 요약 페이지 (네이버 금융, 로그인 불필요)

사용:  python3 -I kospi.py   → kospi.html (최신) + kospi/YYYY-MM-DD.html, kospi.txt (카톡용)
"""
import html
import json
import os
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
SITE = "https://kkhgold.github.io/stock-report/"
UA = {"User-Agent": "Mozilla/5.0"}
WEEK = "월화수목금토일"


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.loads(r.read())


def n(x):
    try:
        return float(str(x).replace(",", "").replace("+", ""))
    except (TypeError, ValueError):
        return 0.0


esc = html.escape


def cls(v):
    return "up" if v > 0 else "down" if v < 0 else "flat"


def pct(v):
    return f"{'▲' if v > 0 else '▼' if v < 0 else ''}{abs(v):.2f}%"


def won(eok):
    """억원 → '1조 2,345억' 형태"""
    a = abs(eok)
    s = f"{int(a // 10000)}조 {int(a % 10000):,}억" if a >= 10000 else f"{int(a):,}억"
    return ("+" if eok > 0 else "−" if eok < 0 else "") + s


def line_svg(xs, ys, base=None, w=640, h=260, pad=12, labels=None, pr=84):
    lo, hi = min(ys + ([base] if base else [])), max(ys + ([base] if base else []))
    rng = (hi - lo) or 1
    lo, hi = lo - rng * 0.08, hi + rng * 0.08
    X = lambda i: pad + (w - pad - pr) * i / max(1, len(ys) - 1)
    Y = lambda v: 12 + (h - 44) * (hi - v) / (hi - lo)
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(ys))
    col = "var(--up)" if ys[-1] >= (base if base else ys[0]) else "var(--down)"
    area = f"{X(0):.1f},{h - 32} {pts} {X(len(ys) - 1):.1f},{h - 32}"
    s = f"<svg viewBox='0 0 {w} {h}' class='chart' role='img'>"
    for k in range(4):
        v = lo + (hi - lo) * (k + 0.5) / 4
        s += f"<line x1='{pad}' x2='{w - pr}' y1='{Y(v):.1f}' y2='{Y(v):.1f}' class='grid'/><text x='{w - pr + 6}' y='{Y(v) + 4:.1f}' class='ax'>{v:,.0f}</text>"
    if base:
        s += f"<line x1='{pad}' x2='{w - pr}' y1='{Y(base):.1f}' y2='{Y(base):.1f}' class='base'/><text x='{pad}' y='{Y(base) - 4:.1f}' class='ax'>전일 {base:,.2f}</text>"
    s += f"<polygon points='{area}' style='fill:{col};opacity:.10'/><polyline points='{pts}' style='fill:none;stroke:{col};stroke-width:3'/>"
    s += f"<circle cx='{X(len(ys) - 1):.1f}' cy='{Y(ys[-1]):.1f}' r='6' style='fill:{col}'/>"
    for i, t in (labels or []):
        s += f"<text x='{X(i):.1f}' y='{h - 8}' class='ax' text-anchor='middle'>{esc(t)}</text>"
    return s + "</svg>"


def main():
    now = datetime.now(KST)
    today = now.strftime("%Y%m%d")
    rt = get("https://polling.finance.naver.com/api/realtime/domestic/index/KOSPI")["datas"][0]
    integ = {i["code"]: i["value"] for i in get("https://m.stock.naver.com/api/index/KOSPI/integration")["totalInfos"]}
    price, chg, rate = n(rt["closePriceRaw"]), n(rt["compareToPreviousClosePriceRaw"]), n(rt["fluctuationsRatioRaw"])
    prev = n(integ.get("lastClosePrice"))
    op, hi, lo = n(rt["openPriceRaw"]), n(rt["highPriceRaw"]), n(rt["lowPriceRaw"])
    value_eok = n(rt["accumulatedTradingValue"].replace("백만", "")) / 100
    hi52, lo52 = n(integ.get("highPriceOf52Weeks")), n(integ.get("lowPriceOf52Weeks"))
    is_open = rt.get("marketStatus") == "OPEN"
    t = rt["localTradedAt"][11:16]
    status = f"{t} 장중" if is_open else "장 마감"

    tr = get("https://m.stock.naver.com/api/index/KOSPI/trend")
    inv = [("개인", n(tr["personalValue"])), ("외국인", n(tr["foreignValue"])), ("기관", n(tr["institutionalValue"]))]

    mins = get(f"https://api.stock.naver.com/chart/domestic/index/KOSPI/minute?startDateTime={today}0900&endDateTime={today}1600")
    mins = [m for m in mins if m.get("currentPrice")]
    days = get("https://api.stock.naver.com/chart/domestic/index/KOSPI?periodType=dayCandle")["priceInfos"][-60:]
    caps = get("https://m.stock.naver.com/api/stocks/marketValue/KOSPI?page=1&pageSize=10")["stocks"]
    groups = [g for g in get("https://m.stock.naver.com/api/stocks/industry?page=1&pageSize=100")["groups"] if g["totalCount"] >= 3]
    groups.sort(key=lambda g: -n(g["changeRate"]))
    rise, fall = sum(g["riseCount"] for g in groups), sum(g["fallCount"] for g in groups)

    # 요약 문장
    d5 = days[-6]["closePrice"] if len(days) >= 6 else None
    big = max(inv, key=lambda x: abs(x[1]))
    buy = [nm for nm, v in inv if v > 0]
    sell = [nm for nm, v in inv if v < 0]
    up_caps = [c for c in caps if n(c["fluctuationsRatio"]) > 0]
    summary = [
        f"코스피 {price:,.2f}, 전일보다 {chg:+,.2f}p ({pct(rate)}) · {status}",
        f"시가 {op:,.2f}로 {'갭상승' if op > prev else '갭하락' if op < prev else '보합'} 출발, 장중 고가 {hi:,.2f} · 저가 {lo:,.2f} (변동폭 {hi - lo:,.0f}p)",
        f"투자자: {'·'.join(buy) or '-'} 순매수, {'·'.join(sell) or '-'} 순매도 — {big[0]} {won(big[1])}원이 가장 큼",
        f"시가총액 상위 10종목 중 {len(up_caps)}개 상승 · 거래대금 {won(value_eok).lstrip('+')}원",
        f"업종: 강세 {groups[0]['name']} {pct(n(groups[0]['changeRate']))}, 약세 {groups[-1]['name']} {pct(n(groups[-1]['changeRate']))}",
    ]
    if d5:
        summary.append(f"최근 5거래일 {pct((price / d5 - 1) * 100)} · 52주 최고 {hi52:,.2f} 대비 {pct((price / hi52 - 1) * 100)}")

    # 차트
    intraday = ""
    if mins:
        ys = [m["currentPrice"] for m in mins]
        labs = [(i, m["localDateTime"][8:10] + ":" + m["localDateTime"][10:12]) for i, m in enumerate(mins) if m["localDateTime"][10:12] == "00" and m["localDateTime"][8:10] in ("09", "11", "13", "15")]
        intraday = line_svg(list(range(len(ys))), ys, base=prev, labels=labs)
    dys = [d["closePrice"] for d in days]
    step = max(1, len(days) // 4)
    dlabs = [(i, f"{int(days[i]['localDate'][4:6])}/{int(days[i]['localDate'][6:])}") for i in range(0, len(days), step)]
    daily = line_svg(list(range(len(dys))), dys, labels=dlabs)

    mx = max(abs(v) for _, v in inv) or 1
    inv_html = "".join(
        f"<div class='inv'><span class='nm'>{nm}</span><div class='track'><i class='{cls(v)}' style='width:{abs(v) / mx * 100:.0f}%'></i></div><b class='{cls(v)}'>{won(v)}</b></div>"
        for nm, v in inv)
    cap_rows = "".join(
        f"<tr><td>{i}</td><td>{esc(c['stockName'])}</td><td class='num'>{esc(c['closePrice'])}</td><td class='num {cls(n(c['fluctuationsRatio']))}'>{pct(n(c['fluctuationsRatio']))}</td><td class='num sub'>{esc(c['marketValueHangeul'].split(' ')[0])}</td></tr>"
        for i, c in enumerate(caps, 1))

    def sec_list(gs):
        return "".join(f"<li><span>{esc(g['name'])}</span><b class='{cls(n(g['changeRate']))}'>{pct(n(g['changeRate']))}</b></li>" for g in gs)

    rng_pos = (price - lo) / ((hi - lo) or 1) * 100
    date_kr = f"{now.month}/{now.day}({WEEK[now.weekday()]})"
    page = f"""<!doctype html><html lang="ko"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>오늘의 코스피</title><meta name="description" content="{date_kr} 코스피 요약">
<meta property="og:title" content="📊 {date_kr} 코스피 {price:,.2f} ({pct(rate)})"><meta property="og:description" content="{esc(summary[2])}">
<style>
:root{{--bg:#f5f6f8;--card:#fff;--ink:#16181d;--sub:#6b7280;--line:#e5e7eb;--up:#e5383b;--down:#1c7ed6;--flat:#868e96;--hero:#0f2a4a}}
@media (prefers-color-scheme:dark){{:root:not([data-theme="light"]){{--bg:#0f1115;--card:#181b21;--ink:#eef0f3;--sub:#9aa1ad;--line:#2a2e36;--up:#ff6b6b;--down:#4dabf7;--hero:#0b1a2e}}}}
:root[data-theme="dark"]{{--bg:#0f1115;--card:#181b21;--ink:#eef0f3;--sub:#9aa1ad;--line:#2a2e36;--up:#ff6b6b;--down:#4dabf7;--hero:#0b1a2e}}
*{{box-sizing:border-box}}body{{margin:0;background:var(--bg);color:var(--ink);font:15px/1.55 -apple-system,"Apple SD Gothic Neo","Noto Sans KR",sans-serif}}
.hero{{background:var(--hero);color:#fff;padding:22px 16px 26px}}.hero .in,main{{max-width:760px;margin:0 auto}}
.k{{font-size:12px;letter-spacing:.12em;opacity:.7}}.big{{font-size:40px;font-weight:800;margin:4px 0 0;font-variant-numeric:tabular-nums}}
.chg{{font-size:18px;font-weight:700}}.hero .up{{color:#ff8787}}.hero .down{{color:#74c0fc}}.st{{font-size:13px;opacity:.75;margin-top:4px}}
main{{padding:14px 16px 40px}}.card{{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px;margin-bottom:12px}}
h2{{font-size:16px;margin:0 0 10px}}.up{{color:var(--up)}}.down{{color:var(--down)}}.flat{{color:var(--flat)}}.sub{{color:var(--sub)}}
ul.sum{{margin:0;padding-left:18px}}ul.sum li{{margin:3px 0}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:8px}}.kv{{background:var(--bg);border-radius:10px;padding:8px 10px}}.kv span{{display:block;color:var(--sub);font-size:12px}}.kv b{{font-variant-numeric:tabular-nums}}
.range{{position:relative;height:8px;background:linear-gradient(90deg,var(--down),var(--line),var(--up));border-radius:4px;margin:16px 0 4px}}.range i{{position:absolute;top:-5px;width:4px;height:18px;background:var(--ink);border-radius:2px;transform:translateX(-50%)}}
.rl{{display:flex;justify-content:space-between;font-size:12px;color:var(--sub)}}
svg.chart{{width:100%;height:auto;display:block}}svg .grid{{stroke:var(--line)}}svg .base{{stroke:var(--sub);stroke-dasharray:4 4}}svg .ax{{fill:var(--sub);font-size:20px}}
.inv{{display:grid;grid-template-columns:52px 1fr 104px;align-items:center;gap:8px;margin:8px 0}}.track{{height:12px;background:var(--bg);border-radius:6px;overflow:hidden}}.track i{{display:block;height:100%;border-radius:6px}}
.track i.up{{background:var(--up)}}.track i.down{{background:var(--down)}}.inv b{{text-align:right;font-variant-numeric:tabular-nums;font-size:14px}}
table{{width:100%;border-collapse:collapse;font-size:14px}}td{{padding:7px 4px;border-top:1px solid var(--line)}}td.num{{text-align:right;font-variant-numeric:tabular-nums}}td:first-child{{color:var(--sub);width:22px}}
.two{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}.secl{{list-style:none;margin:0;padding:0}}.secl li{{display:flex;justify-content:space-between;padding:6px 0;border-top:1px solid var(--line);font-size:14px}}
.br{{display:flex;height:10px;border-radius:5px;overflow:hidden;margin-top:8px}}.br .u{{background:var(--up)}}.br .d{{background:var(--down)}}
footer{{color:var(--sub);font-size:12px;text-align:center;margin-top:18px}}a{{color:inherit}}
@media (max-width:520px){{.grid{{grid-template-columns:repeat(2,1fr)}}.two{{grid-template-columns:1fr}}.big{{font-size:34px}}}}
</style></head><body>
<header class="hero"><div class="in"><div class="k">KOSPI DAILY · {date_kr}</div>
<div class="big">{price:,.2f}</div><div class="chg {cls(chg)}">{chg:+,.2f}p · {pct(rate)}</div><div class="st">{status} 기준 · 전일 종가 {prev:,.2f}</div></div></header>
<main>
<div class="card"><h2>📝 한 줄씩 요약</h2><ul class="sum">{''.join(f'<li>{esc(s)}</li>' for s in summary)}</ul></div>
<div class="card"><h2>⏱ 오늘 흐름</h2>{intraday or "<p class='sub'>분봉 데이터 없음</p>"}
<div class="range"><i style="left:{rng_pos:.0f}%"></i></div><div class="rl"><span>저가 {lo:,.2f}</span><span>현재 {price:,.2f}</span><span>고가 {hi:,.2f}</span></div></div>
<div class="card"><h2>📌 주요 수치</h2><div class="grid">
<div class="kv"><span>시가</span><b>{op:,.2f}</b></div><div class="kv"><span>고가</span><b class="up">{hi:,.2f}</b></div><div class="kv"><span>저가</span><b class="down">{lo:,.2f}</b></div>
<div class="kv"><span>거래대금</span><b>{won(value_eok).lstrip('+')}</b></div><div class="kv"><span>52주 최고</span><b>{hi52:,.2f}</b></div><div class="kv"><span>52주 최저</span><b>{lo52:,.2f}</b></div></div></div>
<div class="card"><h2>👥 투자자별 순매수 <span class="sub" style="font-size:12px;font-weight:400">(억원)</span></h2>{inv_html}</div>
<div class="card"><h2>🏢 시가총액 상위 10</h2><table><tbody>{cap_rows}</tbody></table></div>
<div class="card"><h2>🏭 업종</h2><div class="two"><div><b class="up">🔺 강세</b><ul class="secl">{sec_list(groups[:5])}</ul></div><div><b class="down">🔻 약세</b><ul class="secl">{sec_list(groups[::-1][:5])}</ul></div></div>
<p class="sub" style="font-size:12px;margin:10px 0 0">전체 시장(코스피+코스닥) 상승 {rise:,} · 하락 {fall:,}</p><div class="br"><div class="u" style="flex:{rise}"></div><div class="d" style="flex:{fall}"></div></div></div>
<div class="card"><h2>📈 최근 3개월 (일별 종가)</h2>{daily}</div>
<footer>데이터: 네이버 금융 · {now.strftime('%Y-%m-%d %H:%M')} 생성<br><a href="{SITE}">📊 전체 주식 리포트</a> · 투자 참고용이며 투자 권유가 아닙니다.</footer>
</main></body></html>"""
    os.makedirs(os.path.join(ROOT, "kospi"), exist_ok=True)
    for p in (os.path.join(ROOT, "kospi.html"), os.path.join(ROOT, "kospi", now.strftime("%Y-%m-%d") + ".html")):
        open(p, "w", encoding="utf-8").write(page)
    url = f"{SITE}kospi/{now.strftime('%Y-%m-%d')}.html"
    biz = [f"{nm} {won(v)}" for nm, v in inv]
    txt = (f"📊 {date_kr} 코스피 요약 ({status})\n{price:,.2f} {chg:+,.2f}p ({pct(rate)})\n"
           f"👥 {' / '.join(biz)}\n🏭 강세 {groups[0]['name']} · 약세 {groups[-1]['name']}\n{url}")
    open(os.path.join(ROOT, "kospi.txt"), "w", encoding="utf-8").write(txt[:200])
    print(txt, f"\n({len(txt)}자)")


if __name__ == "__main__":
    main()

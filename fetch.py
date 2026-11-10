"""주식 리포트 데이터 수집 (로그인 필요 없음: 네이버 금융 + Yahoo Finance)

사용:  python3 -I fetch.py            → data/YYYY-MM-DD.json 을 만들고 그 경로를 출력
관심종목은 watchlist.txt 에 한 줄에 하나씩 (이름 / 6자리 코드 / 미국 티커).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
KST = timezone(timedelta(hours=9))
UA = {"User-Agent": "Mozilla/5.0"}
NAVER = "https://m.stock.naver.com/api"
WEEK = ["월요일", "화요일", "수요일", "목요일", "금요일", "토요일", "일요일"]


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as r:
        return json.loads(r.read())


def f(x):
    try:
        return float(str(x).replace(",", ""))
    except (TypeError, ValueError):
        return None


def mkt(sosok_or_type):
    return "KOSDAQ" if str(sosok_or_type) in ("1", "KOSDAQ", "KQ") else "KOSPI"


def row(s):
    return {"name": s["stockName"], "code": s["itemCode"], "market": mkt(s.get("sosok")),
            "price": f(s["closePrice"]), "rate": f(s["fluctuationsRatio"])}


def plain_stock(s):
    """보통주만 (ETF·ETN·우선주 제외)"""
    return s.get("stockEndType") == "stock" and s["itemCode"].endswith("0") and not s["stockName"].endswith(("우", "우B", "우C"))


def movers(kind, n, sign):
    out = []
    for m in ("KOSPI", "KOSDAQ"):
        for s in get(f"{NAVER}/stocks/{kind}/{m}?page=1&pageSize=40")["stocks"]:
            r = row(s)
            r["market"] = m
            if plain_stock(s) and r["rate"] is not None and 0 < r["rate"] * sign <= 30.5:  # 신규상장 등 가격제한폭(30%) 밖은 제외
                out.append(r)
    out.sort(key=lambda r: -r["rate"] * sign)
    return out[:n]


def index(code):
    d = get(f"{NAVER}/index/{code}/basic")
    return {"name": code, "price": f(d["closePrice"]), "change": f(d["compareToPreviousClosePrice"]),
            "rate": f(d["fluctuationsRatio"])}


def yahoo(sym):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(sym) + "?range=5d&interval=1d"
    res = get(url)["chart"]["result"][0]
    # 마지막 봉 = 오늘(진행 중일 수 있음) → 전일 종가는 그 앞 봉들 중 마지막 값
    closes = [c for c in res["indicators"]["quote"][0]["close"][:-1] if c is not None]
    p, prev = res["meta"]["regularMarketPrice"], closes[-1]
    return {"price": round(p, 2), "change": round(p - prev, 2), "rate": round((p - prev) / prev * 100, 2)}


def resolve(q):
    """관심종목 한 줄 → {'kr': code, market} 또는 {'us': ticker}"""
    if q.isdigit() and len(q) == 6:
        return {"code": q}
    try:
        items = [i for i in get("https://ac.stock.naver.com/ac?target=stock&q=" + urllib.parse.quote(q))["items"]
                 if i.get("nationCode") == "KOR" and i.get("category") == "stock"]
    except Exception:
        items = []
    exact = [i for i in items if i["name"].replace(" ", "").upper() == q.replace(" ", "").upper()]
    if exact:
        return {"code": exact[0]["code"]}
    if q.isascii():
        return {"us": q.upper()}
    if items:
        return {"code": items[0]["code"]}
    return None


def watchlist():
    path = os.path.join(ROOT, "watchlist.txt")
    if not os.path.exists(path):
        return [], []
    kr, us = [], []
    for line in open(path, encoding="utf-8"):
        q = line.split("#")[0].strip()
        if not q:
            continue
        r = resolve(q)
        try:
            if r and "code" in r:
                s = get(f"{NAVER}/stock/{r['code']}/basic")
                kr.append({"name": s["stockName"], "code": s["itemCode"], "market": mkt(s.get("sosok")),
                           "price": f(s["closePrice"]), "rate": f(s["fluctuationsRatio"])})
            elif r:
                y = yahoo(r["us"])
                us.append({"name": r["us"], "ticker": r["us"], "price": y["price"], "rate": y["rate"]})
            else:
                print(f"[WARN] 관심종목 '{q}' 을(를) 못 찾음", file=sys.stderr)
        except Exception as e:
            print(f"[WARN] 관심종목 '{q}' 실패: {e}", file=sys.stderr)
    return kr, us


def news(n=6):
    out = []
    for a in get(f"{NAVER}/news/list?category=mainnews&page=1&pageSize=20"):
        dt = a.get("dt", "")
        out.append({"time": f"{dt[8:10]}:{dt[10:12]}" if len(dt) >= 12 else "", "title": a["tit"].replace("&quot;", '"')})
        if len(out) >= n:
            break
    return out


def sign(v):
    return f"{'+' if v > 0 else ''}{v:.1f}%"


def main():
    now = datetime.now(KST)
    idx = [index("KOSPI"), index("KOSDAQ")]
    us = []
    for nm, sym in (("S&P 500", "^GSPC"), ("NASDAQ", "^IXIC"), ("Dow", "^DJI"), ("원/달러", "KRW=X")):
        try:
            us.append({"name": nm, **yahoo(sym)})
        except Exception as e:
            print(f"[WARN] {nm} 실패: {e}", file=sys.stderr)
    top = [row(s) for s in get(f"{NAVER}/stocks/priceTop/KOSPI?page=1&pageSize=6")["stocks"]]
    gainers, losers = movers("up", 5, 1), movers("down", 5, -1)
    wkr, wus = watchlist()
    try:
        nw = news()
    except Exception as e:
        print(f"[WARN] 뉴스 실패: {e}", file=sys.stderr)
        nw = []

    k, q = idx
    summary = [f"코스피 {sign(k['rate'])}({k['price']:,.2f}), 코스닥 {sign(q['rate'])}({q['price']:,.2f})"]
    if top:
        summary.append("거래대금 상위: " + ", ".join(f"{r['name']} {sign(r['rate'])}" for r in top[:3]))
    if gainers and losers:
        summary.append(f"급등 {gainers[0]['name']} {sign(gainers[0]['rate'])} · 급락 {losers[0]['name']} {sign(losers[0]['rate'])}")
    u = {x["name"]: x for x in us}
    if "NASDAQ" in u and "S&P 500" in u:
        line = f"美 전일 나스닥 {sign(u['NASDAQ']['rate'])}, S&P500 {sign(u['S&P 500']['rate'])}"
        if "원/달러" in u:
            line += f" · 원/달러 {u['원/달러']['price']:,.0f}원"
        summary.append(line)
    if wkr or wus:
        summary.append("⭐ 관심: " + ", ".join(f"{r['name']} {sign(r['rate'])}" for r in (wkr + wus)[:5] if r["rate"] is not None))

    d = {"date": now.strftime("%Y-%m-%d"), "weekday": WEEK[now.weekday()], "generated_at": now.strftime("%H:%M"),
         "summary": summary, "indices": idx, "us": us, "top_value": top, "gainers": gainers, "losers": losers,
         "watch_kr": wkr, "watch_us": wus, "news": nw}
    os.makedirs(os.path.join(ROOT, "data"), exist_ok=True)
    path = os.path.join(ROOT, "data", d["date"] + ".json")
    with open(path, "w", encoding="utf-8") as fp:
        json.dump(d, fp, ensure_ascii=False, indent=2)
    print(path)


if __name__ == "__main__":
    main()

"""주식 리포트 생성기 (차트 포함)

사용:  python -I build.py data/2026-11-09.json
  - 지수 1년 이력은 Yahoo Finance 에서 직접 받아 차트로 그림 (^KS11 ^KQ11 ^IXIC ^GSPC)
결과:
  reports/YYYY-MM-DD.html   그날 리포트
  index.html                최신 리포트 (+ 지난 리포트 목록)
  kakao.txt                 카카오톡용 요약 (200자 이내)
"""
import html
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone, timedelta

ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = "https://kkhgold.github.io/stock-report/"
KST = timezone(timedelta(hours=9))

CHARTS = [
    ("kospi", "^KS11", "KOSPI", "kr"),
    ("kosdaq", "^KQ11", "KOSDAQ", "kr"),
    ("nasdaq", "^IXIC", "NASDAQ", "us"),
    ("sp500", "^GSPC", "S&P 500", "us"),
]


def fetch_history(symbol):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=1y&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())["chart"]["result"][0]
    tz = timezone(timedelta(seconds=res["meta"].get("gmtoffset", 0)))
    out = []
    for t, c in zip(res["timestamp"], res["indicators"]["quote"][0]["close"]):
        if c is None:
            continue
        out.append([datetime.fromtimestamp(t, tz).strftime("%Y-%m-%d"), round(c, 2)])
    return out


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
    return f"{f:,.{digits}f}"


CSS = r"""
:root{color-scheme:light;--bg:#f3f5f9;--surface:#ffffff;--surface-2:#f7f9fc;--text:#0f1520;--text-2:#4f5a6b;--muted:#7a8494;
--line:#e4e8ef;--grid:#edf0f5;--series-1:#2a78d6;--series-2:#eb6834;--up:#d63c3c;--down:#2a6fdb;--chip:#eef2f7;
--hero-a:#0f2a52;--hero-b:#1f5fa8;--shadow:0 1px 2px rgba(16,24,40,.04),0 4px 16px rgba(16,24,40,.06)}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){color-scheme:dark;--bg:#0d1117;--surface:#161b22;--surface-2:#1c222b;
--text:#eef1f6;--text-2:#b4bccb;--muted:#8a93a3;--line:#29313d;--grid:#222a35;--series-1:#3987e5;--series-2:#d95926;--up:#ff6b6b;--down:#6aa7ff;
--chip:#222a35;--hero-a:#0b1a33;--hero-b:#163e70;--shadow:none}}
:root[data-theme="dark"]{color-scheme:dark;--bg:#0d1117;--surface:#161b22;--surface-2:#1c222b;--text:#eef1f6;--text-2:#b4bccb;--muted:#8a93a3;
--line:#29313d;--grid:#222a35;--series-1:#3987e5;--series-2:#d95926;--up:#ff6b6b;--down:#6aa7ff;--chip:#222a35;--hero-a:#0b1a33;--hero-b:#163e70;--shadow:none}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Apple SD Gothic Neo","Pretendard","Malgun Gothic","Noto Sans KR",sans-serif;line-height:1.55;-webkit-font-smoothing:antialiased}
.hero{background:linear-gradient(135deg,var(--hero-a),var(--hero-b));color:#fff;padding:28px 16px 64px}
.hero .in{max-width:880px;margin:0 auto}
.hero .kicker{opacity:.75;font-size:.85rem;letter-spacing:.04em}
.hero h1{margin:4px 0 6px;font-size:1.7rem;letter-spacing:-.01em}
.hero p{margin:0;opacity:.85;font-size:.95rem}
.wrap{max-width:880px;margin:-44px auto 0;padding:0 16px 56px}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:var(--shadow);margin-bottom:14px}
.summary ul{margin:0;padding-left:18px}.summary li{margin:6px 0}
.sec{display:flex;align-items:center;gap:10px;margin:30px 0 12px}
.sec h2{margin:0;font-size:1.2rem}.sec .tag{font-size:.78rem;color:var(--muted);background:var(--chip);border-radius:999px;padding:2px 10px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:14px}.grid2>*{min-width:0}
html,body{overflow-x:hidden}td{word-break:keep-all}
.chart-card{padding:16px 16px 10px}
.ch-head{display:flex;justify-content:space-between;align-items:flex-start;gap:8px;flex-wrap:wrap}
.ch-name{font-size:.9rem;color:var(--text-2);font-weight:600}
.ch-price{font-size:1.7rem;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em;line-height:1.15}
.ch-chg{font-weight:700;font-variant-numeric:tabular-nums;font-size:.95rem}
.tabs{display:flex;background:var(--chip);border-radius:10px;padding:3px;gap:2px}
.tabs button{border:0;background:transparent;color:var(--text-2);font:inherit;font-size:.8rem;font-weight:600;padding:5px 10px;border-radius:8px;cursor:pointer;min-width:40px}
.tabs button.on{background:var(--surface);color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.plot{position:relative;margin-top:8px;touch-action:pan-y}
.plot svg{display:block;width:100%;height:220px;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px 10px;font-size:.8rem;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;opacity:0;transition:opacity .12s;color:var(--text)}
.tip b{font-variant-numeric:tabular-nums}.tip .d{color:var(--muted)}
.legend{display:flex;gap:14px;font-size:.78rem;color:var(--text-2);margin:6px 0 2px}
.legend i{display:inline-block;width:16px;height:2px;vertical-align:middle;margin-right:5px;border-radius:2px}
.legend i.ma{background:none;border-top:2px dashed var(--series-2);height:0}
.stats{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:8px;border-top:1px solid var(--line);padding-top:10px}
.stats div{font-size:.75rem;color:var(--muted)}.stats b{display:block;font-size:.9rem;color:var(--text);font-variant-numeric:tabular-nums}
.tiles{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.tile{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px;box-shadow:var(--shadow)}
.tile .n{color:var(--muted);font-size:.8rem}.tile .v{font-size:1.2rem;font-weight:800;font-variant-numeric:tabular-nums}.tile .r{font-weight:700;font-size:.85rem;font-variant-numeric:tabular-nums}
.up,.stats b.up{color:var(--up)}.down,.stats b.down{color:var(--down)}.flat{color:var(--muted)}
table{width:100%;border-collapse:collapse;font-size:.92rem}
th,td{padding:9px 4px;border-bottom:1px solid var(--line);text-align:left}
tr:last-child td{border-bottom:0}
td.num,th.num{text-align:right;font-variant-numeric:tabular-nums}th{color:var(--muted);font-weight:600;font-size:.8rem}
td.rk{color:var(--muted);width:24px;font-variant-numeric:tabular-nums}
.bar{position:relative;display:inline-block;height:6px;border-radius:3px;vertical-align:middle;margin-left:6px;opacity:.85}
.news li{margin:8px 0}.news .t{color:var(--muted);font-size:.8rem;margin-right:8px;font-variant-numeric:tabular-nums}
.news ul{margin:0;padding-left:0;list-style:none}
.arch a{display:inline-block;background:var(--chip);color:var(--text);text-decoration:none;border-radius:999px;padding:4px 12px;margin:3px 4px 3px 0;font-size:.85rem}
details.tbl summary{cursor:pointer;color:var(--muted);font-size:.8rem;margin-top:6px}
footer{color:var(--muted);font-size:.78rem;margin-top:30px;text-align:center}
@media (max-width:480px){.ch-price{font-size:1.45rem}.stats{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:1.45rem}}
"""

JS = r"""
(function(){
const DATA = JSON.parse(document.getElementById('chart-data').textContent);
const RANGES = {'1M':22,'3M':66,'6M':130,'1Y':9999};
const fmt = (v,d=2)=>v.toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
function ma(arr,n){return arr.map((_,i)=>i<n-1?null:arr.slice(i-n+1,i+1).reduce((a,b)=>a+b,0)/n);}
function niceTicks(lo,hi,count){const span=hi-lo;const step0=span/count;const mag=Math.pow(10,Math.floor(Math.log10(step0)));
 const step=[1,2,2.5,5,10].map(m=>m*mag).find(s=>s>=step0);const out=[];for(let v=Math.ceil(lo/step)*step;v<=hi;v+=step)out.push(v);return out;}
function draw(card,key,range){
 const full=DATA[key]; if(!full||!full.length){card.querySelector('.plot').innerHTML='<p style="color:var(--muted)">차트 데이터 없음</p>';return;}
 const closes=full.map(p=>p[1]); const ma20full=ma(closes,20);
 const n=Math.min(RANGES[range],full.length); const s=full.length-n;
 const pts=full.slice(s), m20=ma20full.slice(s);
 const plot=card.querySelector('.plot'); const W=Math.max(260,Math.round(plot.clientWidth||600)),H=220,L=4,R=56,T=10,B=24;
 const vals=pts.map(p=>p[1]).concat(m20.filter(v=>v!=null));
 let lo=Math.min(...vals),hi=Math.max(...vals);const pad=(hi-lo)*0.08||1;lo-=pad;hi+=pad;
 const x=i=>L+(W-L-R)*(n===1?0.5:i/(n-1)); const y=v=>T+(H-T-B)*(1-(v-lo)/(hi-lo));
 const line=pts.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(p[1]).toFixed(1)).join('');
 const area=line+'L'+x(n-1).toFixed(1)+','+(H-B)+'L'+x(0).toFixed(1)+','+(H-B)+'Z';
 let maPath='';m20.forEach((v,i)=>{if(v==null)return;maPath+=(maPath?'L':'M')+x(i).toFixed(1)+','+y(v).toFixed(1);});
 const ticks=niceTicks(lo,hi,4);
 const grid=ticks.map(t=>`<line x1="${L}" x2="${W-R}" y1="${y(t)}" y2="${y(t)}" stroke="var(--grid)" stroke-width="1"/>`+
   `<text x="${W-R+8}" y="${y(t)+4}" font-size="11" fill="var(--muted)">${t>=100?fmt(t,0):fmt(t,1)}</text>`).join('');
 const xl=[0,Math.floor((n-1)/2),n-1].map((i,k)=>`<text x="${x(i)}" y="${H-6}" font-size="11" fill="var(--muted)" text-anchor="${['start','middle','end'][k]}">${pts[i][0].slice(5).replace('-','/')}</text>`).join('');
 const last=pts[n-1][1], first=pts[0][1];
 const gid='g'+key;
 const svg=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${card.dataset.name} ${range} 추이">
  <defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--series-1)" stop-opacity=".28"/><stop offset="1" stop-color="var(--series-1)" stop-opacity="0"/></linearGradient></defs>
  ${grid}${xl}
  <path d="${area}" fill="url(#${gid})"/>
  ${maPath?`<path d="${maPath}" fill="none" stroke="var(--series-2)" stroke-width="1.6" stroke-dasharray="5 4" vector-effect="non-scaling-stroke"/>`:''}
  <path d="${line}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/>
  <circle cx="${x(n-1)}" cy="${y(last)}" r="4" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2"/>
  <line class="xh" x1="0" x2="0" y1="${T}" y2="${H-B}" stroke="var(--muted)" stroke-width="1" stroke-dasharray="3 3" opacity="0" vector-effect="non-scaling-stroke"/>
  <circle class="dot" r="5" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2" opacity="0"/>
  <rect class="hit" x="0" y="0" width="${W}" height="${H}" fill="transparent"/></svg><div class="tip"></div>`;
 plot.innerHTML=svg;
 const sv=plot.querySelector('svg'),xh=sv.querySelector('.xh'),dot=sv.querySelector('.dot'),tip=plot.querySelector('.tip');
 function move(ev){const r=sv.getBoundingClientRect();const cx=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)/r.width*W;
  let i=Math.round((cx-L)/(W-L-R)*(n-1));i=Math.max(0,Math.min(n-1,i));const px=x(i),py=y(pts[i][1]);
  xh.setAttribute('x1',px);xh.setAttribute('x2',px);xh.setAttribute('opacity',1);dot.setAttribute('cx',px);dot.setAttribute('cy',py);dot.setAttribute('opacity',1);
  const prev=i?pts[i-1][1]:null;const ch=prev?((pts[i][1]/prev-1)*100):null;
  tip.innerHTML=`<div class="d">${pts[i][0]}</div><b>${fmt(pts[i][1])}</b>`+(ch!=null?` <span class="${ch>0?'up':ch<0?'down':'flat'}">${ch>0?'▲':ch<0?'▼':''}${Math.abs(ch).toFixed(2)}%</span>`:'')+(m20[i]!=null?`<div class="d">20일선 ${fmt(m20[i])}</div>`:'');
  tip.style.opacity=1;const tw=tip.offsetWidth;let left=px/W*r.width+12;if(left+tw>r.width)left=px/W*r.width-tw-12;tip.style.left=left+'px';tip.style.top='4px';}
 function leave(){xh.setAttribute('opacity',0);dot.setAttribute('opacity',0);tip.style.opacity=0;}
 const hit=sv.querySelector('.hit');hit.addEventListener('mousemove',move);hit.addEventListener('mouseleave',leave);
 hit.addEventListener('touchstart',move,{passive:true});hit.addEventListener('touchmove',move,{passive:true});hit.addEventListener('touchend',leave);
 const ret=(last/first-1)*100;const hiAll=Math.max(...pts.map(p=>p[1])),loAll=Math.min(...pts.map(p=>p[1]));
 const st=card.querySelector('.stats');
 st.innerHTML=`<div>${range} 수익률<b class="${ret>0?'up':ret<0?'down':'flat'}">${ret>0?'+':''}${ret.toFixed(2)}%</b></div>`+
  `<div>${range} 최고<b>${fmt(hiAll)}</b></div><div>${range} 최저<b>${fmt(loAll)}</b></div>`+
  `<div>20일선 대비<b class="${last>ma20full[ma20full.length-1]?'up':'down'}">${last>ma20full[ma20full.length-1]?'위':'아래'} ${Math.abs((last/ma20full[ma20full.length-1]-1)*100).toFixed(1)}%</b></div>`;
 card.querySelectorAll('.tabs button').forEach(b=>b.classList.toggle('on',b.dataset.r===range));
 const tb=card.querySelector('tbody');if(tb){tb.innerHTML=pts.slice(-10).reverse().map(p=>`<tr><td>${p[0]}</td><td class="num">${fmt(p[1])}</td></tr>`).join('');}
}
document.querySelectorAll('.chart-card').forEach(card=>{const key=card.dataset.key;
 card.querySelectorAll('.tabs button').forEach(b=>b.addEventListener('click',()=>draw(card,key,b.dataset.r)));draw(card,key,'3M');});
let t;window.addEventListener('resize',()=>{clearTimeout(t);t=setTimeout(()=>document.querySelectorAll('.chart-card').forEach(c=>draw(c,c.dataset.key,c.querySelector('.tabs .on').dataset.r)),150);});
})();
"""


def chart_card(key, label, quote):
    price = quote.get("price") if quote else None
    rate = quote.get("rate") if quote else None
    change = quote.get("change") if quote else None
    chg = pct(rate) + (f" ({'+' if float(change) > 0 else ''}{num(change)})" if change not in (None, "") else "")
    return f"""
<div class="card chart-card" data-key="{key}" data-name="{esc(label)}">
  <div class="ch-head">
    <div><div class="ch-name">{esc(label)}</div>
      <div class="ch-price">{num(price)}</div>
      <div class="ch-chg {cls(rate)}">{chg}</div></div>
    <div class="tabs" role="tablist" aria-label="{esc(label)} 기간">
      <button data-r="1M">1M</button><button data-r="3M" class="on">3M</button><button data-r="6M">6M</button><button data-r="1Y">1Y</button></div>
  </div>
  <div class="legend"><span><i style="background:var(--series-1)"></i>종가</span><span><i class="ma"></i>20일 이동평균</span></div>
  <div class="plot"></div>
  <div class="stats"></div>
  <details class="tbl"><summary>최근 10일 표로 보기</summary><table><thead><tr><th>날짜</th><th class="num">종가</th></tr></thead><tbody></tbody></table></details>
</div>"""


def tiles(items, digits=2):
    return "<div class='tiles'>" + "".join(
        f"<div class='tile'><div class='n'>{esc(it['name'])}</div><div class='v'>{num(it.get('price'), digits)}</div>"
        f"<div class='r {cls(it.get('rate'))}'>{pct(it.get('rate'))}</div></div>" for it in items) + "</div>"


def rank_table(rows, show_bar=False):
    if not rows:
        return "<p class='flat'>데이터 없음</p>"
    mx = max((abs(float(r.get("rate") or 0)) for r in rows), default=1) or 1
    body = ""
    for i, r in enumerate(rows, 1):
        rate = float(r.get("rate") or 0)
        bar = (f"<span class='bar' style='width:{max(4, abs(rate) / mx * 48):.0f}px;background:var(--{'up' if rate > 0 else 'down'})'></span>"
               if show_bar else "")
        body += (f"<tr><td class='rk'>{i}</td><td>{esc(r['name'])}</td><td class='num'>{num(r.get('price'), 0)}</td>"
                 f"<td class='num {cls(rate)}'>{pct(rate)}{bar}</td></tr>")
    return f"<table><thead><tr><th></th><th>종목</th><th class='num'>현재가</th><th class='num'>등락률</th></tr></thead><tbody>{body}</tbody></table>"


def find(items, name):
    return next((i for i in items if i["name"].upper().replace(" ", "") == name.upper().replace(" ", "")), {})


def render(d, archive, hist):
    title = f"주식 리포트 {d['date']}"
    idx, us = d.get("indices", []), d.get("us", [])
    p = []
    p.append(f"""<header class="hero"><div class="in"><div class="kicker">DAILY MARKET REPORT</div>
<h1>📈 {esc(d['date'])} ({esc(d.get('weekday', ''))})</h1>
<p>{esc(d.get('generated_at', ''))} 기준 · 국내 장중 / 미국 전일 마감</p></div></header><main class="wrap">""")
    if d.get("summary"):
        p.append("<div class='card summary'><ul>" + "".join(f"<li>{esc(s)}</li>" for s in d["summary"]) + "</ul></div>")

    p.append("<div class='sec'><h2>🇰🇷 국내 시장</h2><span class='tag'>KOSPI · KOSDAQ</span></div><div class='grid2'>")
    p.append(chart_card("kospi", "KOSPI", find(idx, "KOSPI")))
    p.append(chart_card("kosdaq", "KOSDAQ", find(idx, "KOSDAQ")))
    p.append("</div>")
    p.append("<div class='grid2'><div class='card'><h3 style='margin:0 0 6px;font-size:1rem'>💰 거래대금 상위</h3>"
             + rank_table(d.get("top_value", [])) + "</div>")
    if d.get("gainers") or d.get("losers"):
        p.append("<div class='card'><h3 style='margin:0 0 6px;font-size:1rem'>🔺 상승률 상위</h3>" + rank_table(d.get("gainers", []), True)
                 + "<h3 style='margin:14px 0 6px;font-size:1rem'>🔻 하락률 상위</h3>" + rank_table(d.get("losers", []), True) + "</div>")
    p.append("</div>")

    p.append("<div class='sec'><h2>🇺🇸 미국 시장</h2><span class='tag'>전일 마감</span></div><div class='grid2'>")
    p.append(chart_card("nasdaq", "NASDAQ", find(us, "NASDAQ")))
    p.append(chart_card("sp500", "S&P 500", find(us, "S&P 500")))
    p.append("</div>")
    rest = [u for u in us if u["name"].upper().replace(" ", "") not in ("NASDAQ", "S&P500")]
    if rest:
        p.append(tiles(rest))

    if d.get("news"):
        p.append("<div class='sec'><h2>📰 주요 뉴스</h2></div><div class='card news'><ul>" +
                 "".join(f"<li><span class='t'>{esc(n.get('time', ''))}</span>{esc(n['title'])}</li>" for n in d["news"]) + "</ul></div>")
    if archive:
        p.append("<div class='sec'><h2>🗂 지난 리포트</h2></div><div class='arch'>" +
                 "".join(f"<a href='{SITE}reports/{a}.html'>{a}</a>" for a in archive) + "</div>")
    p.append("<footer>지수 차트: Yahoo Finance · 시세·순위·뉴스: 한국투자증권(KIS)·PlayMCP<br>투자 판단의 참고용이며 투자 권유가 아닙니다.</footer></main>")
    data_json = json.dumps(hist, separators=(",", ":")).replace("</", "<\\/")
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>주식 리포트</title><meta name='description' content='{esc(title)}'>"
            f"<meta property='og:title' content='📈 {esc(title)}'><meta property='og:description' content='KOSPI·KOSDAQ·NASDAQ·S&amp;P500 차트와 시장 요약'>"
            f"<style>{CSS}</style></head><body>" + "".join(p) +
            f"<script type='application/json' id='chart-data'>{data_json}</script><script>{JS}</script></body></html>")


def kakao_text(d):
    idx = " ".join(f"{i['name']} {num(i.get('price'))}({pct(i.get('rate'))})" for i in d.get("indices", [])[:2])
    nas = find(d.get("us", []), "NASDAQ")
    us = f"🇺🇸 나스닥 {pct(nas.get('rate'))}" if nas else ""
    top = ", ".join(f"{r['name']} {pct(r.get('rate'))}" for r in d.get("top_value", [])[:2])
    head = f"📈 {d['date'][5:].replace('-', '/')} 주식 리포트\n🇰🇷 {idx}\n{us}\n💰 {top}\n"
    tail = f"📊 차트 보기 {SITE}"
    room = 195 - len(head) - len(tail)
    summ = (d.get("summary") or [""])[0]
    if room > 12 and summ:
        head += "📝 " + (summ if len(summ) <= room - 4 else summ[: room - 5] + "…") + "\n"
    return head + tail


def main():
    import urllib.parse  # noqa: F401  (fetch_history 에서 사용)
    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)
    hist = {}
    for key, sym, _, _ in CHARTS:
        try:
            hist[key] = fetch_history(sym)
        except Exception as e:  # 차트 실패해도 리포트는 생성
            print(f"[WARN] {sym} 이력 실패: {e}", file=sys.stderr)
            hist[key] = []
    os.makedirs(os.path.join(ROOT, "reports"), exist_ok=True)
    archive = sorted({n[:-5] for n in os.listdir(os.path.join(ROOT, "reports")) if n.endswith(".html")} | {d["date"]}, reverse=True)
    page = render(d, archive, hist)
    for path in (os.path.join(ROOT, "reports", d["date"] + ".html"), os.path.join(ROOT, "index.html")):
        with open(path, "w", encoding="utf-8") as f:
            f.write(page)
    text = kakao_text(d)
    with open(os.path.join(ROOT, "kakao.txt"), "w", encoding="utf-8") as f:
        f.write(text)
    sys.stdout.reconfigure(encoding="utf-8")
    print(text)
    print(f"\n({len(text)}자) · 차트 데이터: " + ", ".join(f"{k} {len(v)}일" for k, v in hist.items()))


if __name__ == "__main__":
    import urllib.parse
    main()

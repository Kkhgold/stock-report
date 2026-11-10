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


US_STOCKS = [
    ("NVDA", "엔비디아"), ("AAPL", "애플"), ("MSFT", "마이크로소프트"), ("AMZN", "아마존"),
    ("GOOGL", "알파벳"), ("META", "메타"), ("TSLA", "테슬라"), ("AVGO", "브로드컴"),
]


FX = [
    ("USD", "미국 달러", "🇺🇸", 1, None),
    ("JPY", "일본 엔", "🇯🇵", 100, "JPY=X"),
    ("CNY", "중국 위안", "🇨🇳", 1, "CNY=X"),
    ("INR", "인도 루피", "🇮🇳", 1, "INR=X"),
    ("VND", "베트남 동", "🇻🇳", 100, "VND=X"),
    ("THB", "태국 바트", "🇹🇭", 1, "THB=X"),
]


COINS = [  # 시가총액 상위 (스테이블코인 제외), 원화 기준
    ("BTC-KRW", "비트코인", "BTC"), ("ETH-KRW", "이더리움", "ETH"), ("XRP-KRW", "리플", "XRP"),
    ("BNB-KRW", "바이낸스코인", "BNB"), ("SOL-KRW", "솔라나", "SOL"), ("DOGE-KRW", "도지코인", "DOGE"),
    ("ADA-KRW", "에이다", "ADA"), ("TRX-KRW", "트론", "TRX"),
]

COMMODITIES = [
    ("GC=F", "🥇 금", "달러/온스"),
    ("SI=F", "🥈 은", "달러/온스"),
    ("HG=F", "🟠 구리", "달러/파운드"),
    ("CL=F", "🛢 WTI 원유", "달러/배럴"),
    ("BZ=F", "🛢 브렌트유", "달러/배럴"),
]


def fetch_fx():
    """원화 환율 = (원/달러) ÷ (통화/달러) × 단위 — 모든 통화를 같은 기준으로 계산"""
    usdkrw = dict(fetch_history("KRW=X"))
    out = {}
    for code, _, _, unit, sym in FX:
        if sym is None:
            series = sorted(usdkrw.items())
        else:
            other = dict(fetch_history(sym))
            series = sorted((d, usdkrw[d] / v) for d, v in other.items() if d in usdkrw and v)
        out["fx:" + code] = [[d, round(v * unit, 4)] for d, v in series]
    return out


def kr_symbol(r):
    code = str(r.get("code", "")).strip()
    if not code:
        return None
    return code + (".KQ" if str(r.get("market", "")).upper() in ("KQ", "KOSDAQ") else ".KS")


def fetch_history(symbol, ohlc=False):
    url = ("https://query1.finance.yahoo.com/v8/finance/chart/"
           + urllib.parse.quote(symbol) + "?range=1y&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=20) as r:
        res = json.loads(r.read())["chart"]["result"][0]
    tz = timezone(timedelta(seconds=res["meta"].get("gmtoffset", 0)))
    q = res["indicators"]["quote"][0]
    out = []
    for i, t in enumerate(res["timestamp"]):
        c = q["close"][i]
        if c is None:
            continue
        day = datetime.fromtimestamp(t, tz).strftime("%Y-%m-%d")
        if ohlc:
            o = q["open"][i] if q["open"][i] is not None else c
            h = q["high"][i] if q["high"][i] is not None else max(o, c)
            l = q["low"][i] if q["low"][i] is not None else min(o, c)
            out.append([day, round(o, 2), round(max(h, o, c), 2), round(min(l, o, c), 2), round(c, 2)])
        else:
            out.append([day, round(c, 2)])
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
.hero{background:linear-gradient(135deg,var(--hero-a),var(--hero-b));color:#fff;padding:24px 16px 22px}
.hero .in{max-width:880px;margin:0 auto}
.hero .kicker{opacity:.75;font-size:.85rem;letter-spacing:.04em}
.hero h1{margin:4px 0 6px;font-size:1.7rem;letter-spacing:-.01em}
.hero p{margin:0;opacity:.85;font-size:.95rem}
.wrap{max-width:880px;margin:0 auto;padding:14px 16px 56px}
.hero{padding-bottom:22px!important}
.tabbar{position:sticky;top:0;z-index:20;background:color-mix(in srgb,var(--bg) 88%,transparent);backdrop-filter:blur(10px);-webkit-backdrop-filter:blur(10px);border-bottom:1px solid var(--line)}
.tb-in{max-width:880px;margin:0 auto;padding:8px 12px;display:flex;gap:6px;overflow-x:auto;scrollbar-width:none}
.tb-in::-webkit-scrollbar{display:none}
.tabbar button{flex:0 0 auto;border:1px solid var(--line);background:var(--surface);color:var(--text-2);font:inherit;font-size:.9rem;font-weight:700;
 padding:8px 14px;border-radius:999px;cursor:pointer;transition:background .2s,color .2s,transform .15s}
.tabbar button:hover{transform:translateY(-1px)}
.tabbar button[aria-selected="true"]{background:var(--series-1);border-color:var(--series-1);color:#fff}
.pane{animation:fadeUp .35s cubic-bezier(.2,.8,.2,1)}
.pane > .sec:first-child{margin-top:6px}
.hint{color:var(--muted);font-size:.85rem;margin:2px 0 12px}
.h3{margin:0 0 6px;font-size:1rem}
.qt{text-align:left;font:inherit;color:inherit;cursor:pointer;transition:transform .15s,border-color .15s}
.qt:hover{transform:translateY(-2px);border-color:var(--series-1)}
.card{background:var(--surface);border:1px solid var(--line);border-radius:16px;padding:16px;box-shadow:var(--shadow);margin-bottom:14px}
.summary ul{margin:0;padding-left:18px}.summary li{margin:6px 0}
.sec{display:flex;align-items:center;gap:10px;margin:30px 0 12px}
.sec h2{margin:0;font-size:1.2rem}.sec .tag{font-size:.78rem;color:var(--muted);background:var(--chip);border-radius:999px;padding:2px 10px}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,400px),1fr));gap:14px}.grid2>*{min-width:0}
html,body{overflow-x:hidden}td{word-break:keep-all}
.chart-card{padding:16px 16px 10px}
.ch-head{display:block}.ch-head .tabgrp{justify-content:flex-start;margin-top:10px}
.ch-name{font-size:.9rem;color:var(--text-2);font-weight:600}
.ch-price{font-size:1.7rem;font-weight:800;font-variant-numeric:tabular-nums;letter-spacing:-.02em;line-height:1.15}
.ch-chg{font-weight:700;font-variant-numeric:tabular-nums;font-size:.95rem}
.tabgrp{display:flex;gap:6px;flex-wrap:wrap;justify-content:flex-end}.tabs.iv button{min-width:34px}
.tabs{display:flex;background:var(--chip);border-radius:10px;padding:3px;gap:2px}
.tabs button{border:0;background:transparent;color:var(--text-2);font:inherit;font-size:.8rem;font-weight:600;padding:5px 10px;border-radius:8px;cursor:pointer;min-width:40px}
.tabs button.on{background:var(--surface);color:var(--text);box-shadow:0 1px 3px rgba(0,0,0,.12)}
.plot{position:relative;margin-top:8px;touch-action:pan-y}
.plot svg{display:block;width:100%;height:220px;overflow:visible}
.tip{position:absolute;pointer-events:none;background:var(--surface);border:1px solid var(--line);border-radius:10px;padding:6px 10px;font-size:.8rem;box-shadow:0 4px 14px rgba(0,0,0,.15);white-space:nowrap;opacity:0;transition:opacity .12s;color:var(--text)}
.tip b{font-variant-numeric:tabular-nums}.tip .d{color:var(--muted)}
.legend{display:flex;gap:14px;font-size:.78rem;color:var(--text-2);margin:6px 0 2px}
.legend i{display:inline-block;width:16px;height:2px;vertical-align:middle;margin-right:5px;border-radius:2px}
.ln-key{background:var(--series-1)}.ln-key.cdl{width:12px!important;height:10px!important;border-radius:2px!important;background:linear-gradient(90deg,var(--up) 50%,var(--down) 50%)}
.tip .ohlc{display:grid;grid-template-columns:auto auto auto auto;gap:0 6px;font-variant-numeric:tabular-nums;margin:2px 0}.tip .ohlc span{color:var(--muted)}
@keyframes grow{from{transform:scaleY(0);opacity:0}to{transform:scaleY(1);opacity:1}}
g.candles>g.grow{animation:grow .45s cubic-bezier(.2,.8,.2,1) both}
@media (prefers-reduced-motion:reduce){g.candles>g{animation:none!important}}
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
.stocks{display:grid;grid-template-columns:repeat(auto-fill,minmax(min(100%,190px),1fr));gap:10px}
.stock{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 14px 8px;box-shadow:var(--shadow);cursor:pointer;
 text-align:left;font:inherit;color:inherit;transition:transform .18s ease,box-shadow .18s ease,border-color .18s}
.stock:hover,.stock:focus-visible{transform:translateY(-3px);border-color:var(--series-1);box-shadow:0 8px 24px rgba(42,120,214,.18);outline:none}
.stock .nm{font-weight:700;font-size:.92rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.stock .sb{color:var(--muted);font-size:.72rem}
.stock .row{display:flex;justify-content:space-between;align-items:baseline;margin-top:4px}
.stock .pr{font-weight:800;font-variant-numeric:tabular-nums}.stock .rt{font-weight:700;font-size:.85rem;font-variant-numeric:tabular-nums}
.stock svg{display:block;width:100%;height:44px;margin-top:6px}
tr.clk{cursor:pointer;transition:background .15s}tr.clk:hover{background:var(--surface-2)}
.modal{position:fixed;inset:0;z-index:50;display:flex;align-items:flex-end;justify-content:center;background:rgba(5,10,20,.55);opacity:0;pointer-events:none;transition:opacity .2s}
.modal.open{opacity:1;pointer-events:auto}
.sheet{background:var(--surface);color:var(--text);width:min(720px,100%);max-height:92vh;overflow:auto;border-radius:20px 20px 0 0;padding:18px 16px 24px;
 transform:translateY(40px);transition:transform .28s cubic-bezier(.2,.8,.2,1)}
.modal.open .sheet{transform:none}
@media (min-width:760px){.modal{align-items:center}.sheet{border-radius:20px}}
.sheet .x{float:right;border:0;background:var(--chip);color:var(--text);width:34px;height:34px;border-radius:50%;font-size:18px;cursor:pointer}
.sheet .plot svg{height:260px}
@keyframes fadeUp{from{opacity:0;transform:translateY(14px)}to{opacity:1;transform:none}}
.pre{opacity:0}
.anim{animation:fadeUp .55s cubic-bezier(.2,.8,.2,1) both}
@keyframes drawLine{to{stroke-dashoffset:0}}
@keyframes fadeIn{from{opacity:0}to{opacity:1}}
.draw{animation:drawLine 1.1s cubic-bezier(.4,0,.2,1) forwards}
.fade{animation:fadeIn .9s ease .25s both}
@media (prefers-reduced-motion:reduce){.pre{opacity:1}.anim,.draw,.fade{animation:none!important;opacity:1!important;stroke-dashoffset:0!important}.stock,.sheet,.modal{transition:none}}
@media (max-width:480px){.ch-price{font-size:1.45rem}.stats{grid-template-columns:repeat(2,1fr)}.hero h1{font-size:1.45rem}}
"""

JS = r"""
(function(){
/* 데이터: [d,c] 또는 [d,o,h,l,c] → {d,o,h,l,c} 로 통일 */
const RAW = JSON.parse(document.getElementById('chart-data').textContent);
const DATA = {};
for (const k in RAW) DATA[k] = RAW[k].map(p => p.length >= 5 ? {d:p[0],o:p[1],h:p[2],l:p[3],c:p[4]} : {d:p[0],o:p[1],h:p[1],l:p[1],c:p[1],line:1});
const RM = matchMedia('(prefers-reduced-motion: reduce)').matches;
const RANGES = {D:{'1M':22,'3M':66,'6M':130,'1Y':9999}, W:{'1M':5,'3M':14,'6M':27,'1Y':9999}};
const RANGES_CAL = {D:{'1M':30,'3M':91,'6M':182,'1Y':9999}, W:{'1M':5,'3M':14,'6M':27,'1Y':9999}};
const MA_N = {D:20, W:13}, MA_L = {D:'20일', W:'13주'};
const fmt=(v,d=2)=>v.toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
let CUR='';const dg=v=>(CUR.startsWith('fx:')||CUR.startsWith('cm:'))?2:(v>=1000?0:2);
const sgn=c=>c>0?'up':c<0?'down':'flat', arrow=c=>c>0?'▲':c<0?'▼':'';
const hasOHLC=k=>DATA[k]&&DATA[k].length&&!DATA[k][0].line;
function ma(a,n){return a.map((_,i)=>i<n-1?null:a.slice(i-n+1,i+1).reduce((x,y)=>x+y,0)/n);}
function weekly(arr){const out=[];let cur=null;arr.forEach(p=>{const t=new Date(p.d+'T00:00:00');t.setDate(t.getDate()-((t.getDay()+6)%7));const w=t.toISOString().slice(0,10);
 if(cur&&cur.w===w){cur.h=Math.max(cur.h,p.h);cur.l=Math.min(cur.l,p.l);cur.c=p.c;cur.d=p.d;}else{cur={d:p.d,o:p.o,h:p.h,l:p.l,c:p.c,w,line:p.line};out.push(cur);}});return out;}
function niceTicks(lo,hi,c){const st0=(hi-lo)/c,m=Math.pow(10,Math.floor(Math.log10(st0)));const st=[1,2,2.5,5,10].map(k=>k*m).find(v=>v>=st0);const o=[];for(let v=Math.ceil(lo/st)*st;v<=hi;v+=st)o.push(v);return o;}
function animatePaths(svg){if(RM||!svg)return;svg.querySelectorAll('path.ln').forEach(p=>{const L=p.getTotalLength();if(!L)return;
 p.style.strokeDasharray=L;p.style.strokeDashoffset=L;p.getBoundingClientRect();p.classList.add('draw');
 p.addEventListener('animationend',()=>{p.style.strokeDasharray=p.dataset.dash||'';p.style.strokeDashoffset='';p.classList.remove('draw');},{once:true});});
 const cg=svg.querySelector('g.candles');if(cg){[...cg.children].forEach((el,i,a)=>{el.style.animationDelay=(i/a.length*700)+'ms';el.classList.add('grow');});}}
function countUp(el,to,d){if(!el||isNaN(to))return;if(RM){el.textContent=fmt(to,d);return;}const t0=performance.now(),from=to*0.92;
 (function f(t){const k=Math.min(1,(t-t0)/700),e=1-Math.pow(1-k,3);el.textContent=fmt(from+(to-from)*e,d);if(k<1)requestAnimationFrame(f);})(t0);}

/* 큰 차트 */
function draw(host,key,range,animate){
 CUR=key;const full=DATA[key];const plot=host.querySelector('.plot');host.dataset.key=key;
 if(!full||full.length<2){plot.innerHTML='<p class="flat">차트 데이터 없음</p>';return;}
 const iv=host.dataset.iv||'D',ser=iv==='W'?weekly(full):full,maN=MA_N[iv];
 const ohlc=hasOHLC(key);let type=host.dataset.type||(ohlc?'C':'L');if(!ohlc)type='L';
 host.querySelectorAll('.tabs.ty').forEach(t=>t.hidden=!ohlc);
 const closes=ser.map(p=>p.c),m20f=ma(closes,maN);
 const n=Math.max(2,Math.min((key.startsWith('co:')?RANGES_CAL:RANGES)[iv][range],ser.length)),s=ser.length-n,pts=ser.slice(s),m20=m20f.slice(s);
 host.querySelectorAll('.ma-lbl').forEach(e=>e.textContent=MA_L[iv]+' 이동평균');
 host.querySelectorAll('.ln-lbl').forEach(e=>e.textContent=type==='C'?(iv==='W'?'주봉 캔들':'일봉 캔들'):'종가');
 host.querySelectorAll('.ln-key').forEach(e=>e.className='ln-key'+(type==='C'?' cdl':''));
 const W=Math.max(260,Math.round(plot.clientWidth||600)),H=parseInt(getComputedStyle(plot).getPropertyValue('--h'))||220,L=4,R=60,T=10,B=24;
 const vals=(type==='C'?pts.flatMap(p=>[p.h,p.l]):pts.map(p=>p.c)).concat(m20.filter(v=>v!=null));
 let lo=Math.min(...vals),hi=Math.max(...vals);const pd=(hi-lo)*.08||1;lo-=pd;hi+=pd;
 const step=(W-L-R)/n, x=i=>type==='C'?L+step*(i+.5):L+(W-L-R)*(i/(n-1)), y=v=>T+(H-T-B)*(1-(v-lo)/(hi-lo));
 const ticks=niceTicks(lo,hi,4),grid=ticks.map(t=>`<line x1="${L}" x2="${W-R}" y1="${y(t)}" y2="${y(t)}" stroke="var(--grid)"/><text x="${W-R+8}" y="${y(t)+4}" font-size="11" fill="var(--muted)">${fmt(t,t>=100?0:1)}</text>`).join('');
 const nt=W<420?3:5,idx=[...new Set(Array.from({length:nt},(_,k)=>Math.round(k*(n-1)/(nt-1))))];
 const lab=i=>{const d=pts[i].d;return (n>60||range==='1Y')?d.slice(2,7).replace('-','/')+(iv==='W'?'':'/'+d.slice(8)):d.slice(5).replace('-','/');};
 const xl=idx.map((i,k)=>`<line x1="${x(i)}" x2="${x(i)}" y1="${H-B}" y2="${H-B+4}" stroke="var(--line)"/><text x="${x(i)}" y="${H-6}" font-size="11" fill="var(--muted)" text-anchor="${k===0?'start':k===idx.length-1?'end':'middle'}">${lab(i)}</text>`).join('')
  +`<text x="${W-R+8}" y="${H-6}" font-size="10" fill="var(--muted)">${iv==='W'?'주봉':'일봉'}</text>`;
 let mp='';m20.forEach((v,i)=>{if(v!=null)mp+=(mp?'L':'M')+x(i).toFixed(1)+','+y(v).toFixed(1);});
 const last=pts[n-1].c,first=pts[0].c,fa=animate&&!RM?'fade':'';
 let main='';
 if(type==='C'){
  const bw=Math.max(1.5,Math.min(12,step*.62));
  main='<g class="candles">'+pts.map((p,i)=>{const up=p.c>=p.o,col=up?'var(--up)':'var(--down)',cx=x(i).toFixed(1);
   const yt=y(Math.max(p.o,p.c)),yb=y(Math.min(p.o,p.c)),bh=Math.max(1,yb-yt);
   return `<g style="transform-origin:${cx}px ${H-B}px"><line x1="${cx}" x2="${cx}" y1="${y(p.h).toFixed(1)}" y2="${y(p.l).toFixed(1)}" stroke="${col}" stroke-width="1"/>`+
    `<rect x="${(x(i)-bw/2).toFixed(1)}" y="${yt.toFixed(1)}" width="${bw.toFixed(1)}" height="${bh.toFixed(1)}" rx="${bw>4?1:0}" fill="${up?'var(--surface)':col}" stroke="${col}" stroke-width="1.2"/></g>`;}).join('')+'</g>';
  main=main.replace(/fill="var\(--surface\)" stroke="var\(--up\)"/g,'fill="var(--up)" stroke="var(--up)"');
 }else{
  const gid='g'+key.replace(/[^a-z0-9]/gi,'')+Math.random().toString(36).slice(2,6);
  const line=pts.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(p.c).toFixed(1)).join('');
  const area=line+`L${x(n-1).toFixed(1)},${H-B}L${x(0).toFixed(1)},${H-B}Z`;
  main=`<defs><linearGradient id="${gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="var(--series-1)" stop-opacity=".3"/><stop offset="1" stop-color="var(--series-1)" stop-opacity="0"/></linearGradient></defs>`+
   `<path class="${fa}" d="${area}" fill="url(#${gid})"/><path class="ln" d="${line}" fill="none" stroke="var(--series-1)" stroke-width="2" stroke-linejoin="round"/>`+
   `<circle class="${fa}" cx="${x(n-1)}" cy="${y(last)}" r="4" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2"/>`;
 }
 plot.innerHTML=`<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${host.dataset.name||''} ${range} ${type==='C'?'캔들':'라인'} 차트">${grid}${xl}${main}
  ${mp?`<path class="ln" data-dash="5 4" d="${mp}" fill="none" stroke="var(--series-2)" stroke-width="1.6" stroke-dasharray="5 4"/>`:''}
  <line class="xh" y1="${T}" y2="${H-B}" stroke="var(--muted)" stroke-dasharray="3 3" opacity="0"/>
  <circle class="dot" r="4.5" fill="var(--series-1)" stroke="var(--surface)" stroke-width="2" opacity="0"/>
  <rect class="hit" width="${W}" height="${H}" fill="transparent"/></svg><div class="tip"></div>`;
 const sv=plot.querySelector('svg');if(animate)animatePaths(sv);
 const xh=sv.querySelector('.xh'),dot=sv.querySelector('.dot'),tip=plot.querySelector('.tip'),hit=sv.querySelector('.hit');
 function mv(ev){CUR=key;const r=sv.getBoundingClientRect(),cx=((ev.touches?ev.touches[0].clientX:ev.clientX)-r.left)/r.width*W;
  let i=type==='C'?Math.floor((cx-L)/step):Math.round((cx-L)/(W-L-R)*(n-1));i=Math.max(0,Math.min(n-1,i));const p=pts[i],px=x(i),py=y(p.c);
  xh.setAttribute('x1',px);xh.setAttribute('x2',px);xh.setAttribute('opacity',1);
  if(type==='L'){dot.setAttribute('cx',px);dot.setAttribute('cy',py);dot.setAttribute('opacity',1);}
  const prev=i?pts[i-1].c:(s?ser[s-1].c:null),ch=prev?(p.c/prev-1)*100:null,D=v=>fmt(v,dg(v));
  const when=iv==='W'?p.w.slice(5).replace('-','/')+' 주 (마감 '+p.d.slice(5).replace('-','/')+')':p.d;
  tip.innerHTML=`<div class="d">${when}</div>`+(type==='C'?`<div class="ohlc"><span>시</span>${D(p.o)}<span>고</span>${D(p.h)}<span>저</span>${D(p.l)}<span>종</span><b>${D(p.c)}</b></div>`:`<b>${D(p.c)}</b>`)+
   (ch!=null?` <span class="${sgn(ch)}">${arrow(ch)}${Math.abs(ch).toFixed(2)}%</span> <span class="d">${iv==='W'?'전주':'전일'} 대비</span>`:'')+(m20[i]!=null?`<div class="d">${MA_L[iv]}선 ${D(m20[i])}</div>`:'');
  tip.style.opacity=1;const tw=tip.offsetWidth;let lf=px/W*r.width+12;if(lf+tw>r.width)lf=px/W*r.width-tw-12;tip.style.left=Math.max(0,lf)+'px';tip.style.top='4px';}
 function lv(){xh.setAttribute('opacity',0);dot.setAttribute('opacity',0);tip.style.opacity=0;}
 hit.addEventListener('mousemove',mv);hit.addEventListener('mouseleave',lv);hit.addEventListener('touchstart',mv,{passive:true});hit.addEventListener('touchmove',mv,{passive:true});hit.addEventListener('touchend',lv);
 const ret=(last/first-1)*100,hA=Math.max(...pts.map(p=>type==='C'?p.h:p.c)),lA=Math.min(...pts.map(p=>type==='C'?p.l:p.c)),m=m20f[m20f.length-1];
 host.querySelector('.stats').innerHTML=`<div>${range} 수익률<b class="${sgn(ret)}">${ret>0?'+':''}${ret.toFixed(2)}%</b></div><div>${range} 최고<b>${fmt(hA,dg(hA))}</b></div><div>${range} 최저<b>${fmt(lA,dg(lA))}</b></div>`+
  (m?`<div>${MA_L[iv]}선 대비<b class="${last>m?'up':'down'}">${last>m?'위':'아래'} ${Math.abs((last/m-1)*100).toFixed(1)}%</b></div>`:'<div></div>');
 host.querySelectorAll('.tabs [data-r]').forEach(b=>b.classList.toggle('on',b.dataset.r===range));
 host.querySelectorAll('.tabs [data-iv]').forEach(b=>b.classList.toggle('on',b.dataset.iv===iv));
 host.querySelectorAll('.tabs [data-t]').forEach(b=>b.classList.toggle('on',b.dataset.t===type));
 host.dataset.range=range;
 const tb=host.querySelector('tbody');if(tb){const D=v=>fmt(v,dg(v));
  tb.parentElement.querySelector('thead').innerHTML=ohlc?'<tr><th>날짜</th><th class="num">시가</th><th class="num">고가</th><th class="num">저가</th><th class="num">종가</th></tr>':'<tr><th>날짜</th><th class="num">종가</th></tr>';
  tb.innerHTML=pts.slice(-10).reverse().map(p=>`<tr><td>${iv==='W'?p.w+' 주':p.d}</td>`+(ohlc?`<td class="num">${D(p.o)}</td><td class="num">${D(p.h)}</td><td class="num">${D(p.l)}</td>`:'')+`<td class="num">${D(p.c)}</td></tr>`).join('');}
}
function bindTabs(host){
 host.querySelectorAll('.tabs [data-r]').forEach(b=>b.onclick=()=>draw(host,host.dataset.key,b.dataset.r,true));
 host.querySelectorAll('.tabs [data-iv]').forEach(b=>b.onclick=()=>{host.dataset.iv=b.dataset.iv;draw(host,host.dataset.key,host.dataset.range||'3M',true);});
 host.querySelectorAll('.tabs [data-t]').forEach(b=>b.onclick=()=>{host.dataset.type=b.dataset.t;draw(host,host.dataset.key,host.dataset.range||'3M',true);});}

/* 지수 카드 */
const cards=[...document.querySelectorAll('.chart-card')];
cards.forEach(c=>{draw(c,c.dataset.key,'3M',false);bindTabs(c);});

/* 종목·원자재·환율 카드: 가격·등락·스파크라인 */
document.querySelectorAll('.stock').forEach(el=>{CUR=el.dataset.key;const d=DATA[el.dataset.key];if(!d||d.length<2)return;
 const pts=d.slice(-66),W=180,H=44,lo=Math.min(...pts.map(p=>p.c)),hi=Math.max(...pts.map(p=>p.c));
 const x=i=>i/(pts.length-1)*W,y=v=>H-3-(H-6)*((v-lo)/((hi-lo)||1));
 const ln=pts.map((p,i)=>(i?'L':'M')+x(i).toFixed(1)+','+y(p.c).toFixed(1)).join('');
 const last=d[d.length-1].c,ch=(last/d[d.length-2].c-1)*100,col=ch>=0?'var(--up)':'var(--down)';
 el.querySelector('.pr').textContent=fmt(last,dg(last));const rt=el.querySelector('.rt');rt.textContent=arrow(ch)+Math.abs(ch).toFixed(2)+'%';rt.className='rt '+sgn(ch);
 el.querySelector('.spark').innerHTML=`<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="none" aria-hidden="true"><path class="ln" d="${ln}" fill="none" stroke="${col}" stroke-width="1.8" vector-effect="non-scaling-stroke"/></svg>`;});

/* 차트 팝업 */
const modal=document.getElementById('modal'),sheet=modal.querySelector('.sheet');let lastFocus=null;bindTabs(sheet);
function openStock(key,name,sub){CUR=key;const d=DATA[key];if(!d||d.length<2)return;lastFocus=document.activeElement;
 const last=d[d.length-1].c,ch=(last/d[d.length-2].c-1)*100;
 sheet.dataset.name=name;sheet.querySelector('.ch-name').textContent=name+(sub?' · '+sub:'');
 sheet.querySelector('.src').textContent=key.startsWith('fx:')?'환율: Yahoo Finance 달러 기준 환율로 원화 환산 (원/달러 ÷ 통화/달러)':key.startsWith('cm:')?'원자재: Yahoo Finance 근월물 선물 (달러 기준)':key.startsWith('co:')?'코인: Yahoo Finance 원화 시세 (일봉은 UTC 0시 기준)':'차트·가격: Yahoo Finance 기준';
 const ce=sheet.querySelector('.ch-chg');ce.className='ch-chg '+sgn(ch);ce.textContent=`${arrow(ch)}${Math.abs(ch).toFixed(2)}% (전일 대비)`;
 modal.classList.add('open');modal.setAttribute('aria-hidden','false');document.body.style.overflow='hidden';
 sheet.dataset.iv='D';delete sheet.dataset.type;
 requestAnimationFrame(()=>{draw(sheet,key,'3M',true);CUR=key;countUp(sheet.querySelector('.ch-price'),last,dg(last));sheet.querySelector('.x').focus();});}
function closeModal(){modal.classList.remove('open');modal.setAttribute('aria-hidden','true');document.body.style.overflow='';if(lastFocus)lastFocus.focus();}
modal.addEventListener('click',e=>{if(e.target===modal)closeModal();});sheet.querySelector('.x').onclick=closeModal;
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&modal.classList.contains('open'))closeModal();});
document.querySelectorAll('[data-open]').forEach(el=>{const go=()=>openStock(el.dataset.key,el.dataset.name,el.dataset.sub||'');
 el.addEventListener('click',go);if(el.tagName==='TR'){el.tabIndex=0;el.addEventListener('keydown',e=>{if(e.key==='Enter')go();});}});

/* 첫 화면 등장 애니메이션 */
if('IntersectionObserver' in window && !RM){
 const io=new IntersectionObserver(es=>es.forEach(en=>{if(!en.isIntersecting)return;const el=en.target;io.unobserve(el);
  el.classList.remove('pre');el.classList.add('anim');
  if(el.classList.contains('chart-card')){draw(el,el.dataset.key,el.dataset.range||'3M',true);const pe=el.querySelector('.ch-price');countUp(pe,parseFloat(pe.dataset.v),2);}
  el.querySelectorAll('.spark svg').forEach(animatePaths);}),{threshold:.12});
 document.querySelectorAll('.pane:not([hidden]) .card, .pane:not([hidden]) .tile, .pane:not([hidden]) .stock').forEach((el,i)=>{el.classList.add('pre');el.style.animationDelay=((i%4)*70)+'ms';io.observe(el);});
}

/* 탭 */
const tabs=[...document.querySelectorAll('.tabbar [data-tab]')];
function showTab(id,push){const pane=document.getElementById('pane-'+id);if(!pane)return;
 tabs.forEach(t=>t.setAttribute('aria-selected',t.dataset.tab===id?'true':'false'));
 document.querySelectorAll('.pane').forEach(p=>p.hidden=p!==pane);
 pane.style.animation='none';pane.offsetHeight;pane.style.animation='';
 pane.querySelectorAll('.pre').forEach(e=>{e.classList.remove('pre');e.classList.add('anim');});
 pane.querySelectorAll('.chart-card').forEach(c=>{draw(c,c.dataset.key,c.dataset.range||'3M',true);const pe=c.querySelector('.ch-price');countUp(pe,parseFloat(pe.dataset.v),2);});
 pane.querySelectorAll('.spark svg').forEach(animatePaths);
 const sel=tabs.find(t=>t.dataset.tab===id);if(sel)sel.scrollIntoView({inline:'center',block:'nearest',behavior:RM?'auto':'smooth'});
 if(push)history.replaceState(null,'','#'+id);
 const bar=document.querySelector('.tabbar');if(bar&&window.scrollY>bar.offsetTop)window.scrollTo({top:bar.offsetTop,behavior:'auto'});}
tabs.forEach(t=>t.addEventListener('click',()=>showTab(t.dataset.tab,true)));
document.querySelectorAll('[data-goto]').forEach(b=>b.addEventListener('click',()=>showTab(b.dataset.goto,true)));
if(location.hash&&document.getElementById('pane-'+location.hash.slice(1)))showTab(location.hash.slice(1),false);
let rt;addEventListener('resize',()=>{clearTimeout(rt);rt=setTimeout(()=>{cards.filter(c=>c.offsetParent).forEach(c=>draw(c,c.dataset.key,c.dataset.range||'3M',false));
 if(modal.classList.contains('open'))draw(sheet,sheet.dataset.key,sheet.dataset.range||'3M',false);},150);});
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
      <div class="ch-price" data-v="{price if price is not None else ''}">{num(price)}</div>
      <div class="ch-chg {cls(rate)}">{chg}</div></div>
    <div class="tabgrp"><div class="tabs" role="tablist" aria-label="{esc(label)} 기간">
      <button data-r="1M">1M</button><button data-r="3M" class="on">3M</button><button data-r="6M">6M</button><button data-r="1Y">1Y</button></div><div class="tabs iv" role="tablist" aria-label="봉 단위"><button data-iv="D" class="on">일</button><button data-iv="W">주</button></div><div class="tabs ty" role="tablist" aria-label="차트 종류"><button data-t="C" class="on">캔들</button><button data-t="L">라인</button></div></div>
  </div>
  <div class="legend"><span><i class="ln-key cdl"></i><span class="ln-lbl">일봉 캔들</span></span><span><i class="ma"></i><span class="ma-lbl">20일 이동평균</span></span></div>
  <div class="plot"></div>
  <div class="stats"></div>
  <details class="tbl"><summary>최근 10개 표로 보기</summary><table><thead><tr><th>날짜</th><th class="num">종가</th></tr></thead><tbody></tbody></table></details>
</div>"""


def stock_cards(items):
    """items: [(key, name, sub)]"""
    return "<div class='stocks'>" + "".join(
        f"<button class='stock' data-open data-key='{esc(k)}' data-name='{esc(nm)}' data-sub='{esc(sub)}' aria-label='{esc(nm)} 차트 열기'>"
        f"<div class='nm'>{esc(nm)}</div><div class='sb'>{esc(sub)}</div>"
        f"<div class='row'><span class='pr'>-</span><span class='rt flat'>-</span></div><div class='spark'></div></button>"
        for k, nm, sub in items) + "</div>"


MODAL = """<div class="modal" id="modal" aria-hidden="true"><div class="sheet" role="dialog" aria-modal="true" aria-label="종목 차트">
<button class="x" aria-label="닫기">✕</button>
<div class="ch-name"></div><div class="ch-price">-</div><div class="ch-chg"></div>
<div class="tabgrp" style="margin-top:10px"><div class="tabs"><button data-r="1M">1M</button><button data-r="3M" class="on">3M</button><button data-r="6M">6M</button><button data-r="1Y">1Y</button></div><div class="tabs iv" role="tablist" aria-label="봉 단위"><button data-iv="D" class="on">일</button><button data-iv="W">주</button></div><div class="tabs ty" role="tablist" aria-label="차트 종류"><button data-t="C" class="on">캔들</button><button data-t="L">라인</button></div></div>
<div class="legend"><span><i class="ln-key cdl"></i><span class="ln-lbl">일봉 캔들</span></span><span><i class="ma"></i><span class="ma-lbl">20일 이동평균</span></span></div>
<div class="plot" style="--h:260"></div><div class="stats"></div>
<details class="tbl"><summary>최근 10개 표로 보기</summary><table><thead><tr><th>날짜</th><th class="num">종가</th></tr></thead><tbody></tbody></table></details>
<p class="flat src" style="font-size:.75rem;margin:10px 0 0">차트·가격: Yahoo Finance 종가 기준</p></div></div>"""


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
        sym = kr_symbol(r)
        attrs = f" class='clk' data-open data-key='s:{esc(sym)}' data-name='{esc(r['name'])}' data-sub='{esc(sym)}'" if sym else ""
        body += (f"<tr{attrs}><td class='rk'>{i}</td><td>{esc(r['name'])}</td><td class='num'>{num(r.get('price'), 0)}</td>"
                 f"<td class='num {cls(rate)}'>{pct(rate)}{bar}</td></tr>")
    return f"<table><thead><tr><th></th><th>종목</th><th class='num'>현재가</th><th class='num'>등락률</th></tr></thead><tbody>{body}</tbody></table>"


def find(items, name):
    return next((i for i in items if i["name"].upper().replace(" ", "") == name.upper().replace(" ", "")), {})


def quick_tile(hist, key, label, tab, digits=2):
    d = hist.get(key) or []
    if len(d) < 2:
        return ""
    last, prev = d[-1][-1], d[-2][-1]
    rate = (last / prev - 1) * 100
    return (f"<button class='tile qt' data-goto='{tab}'><div class='n'>{esc(label)}</div>"
            f"<div class='v'>{num(last, digits)}</div><div class='r {cls(rate)}'>{pct(rate)}</div></button>")


def render(d, archive, hist):
    title = f"주식 리포트 {d['date']}"
    idx, us = d.get("indices", []), d.get("us", [])
    head = f"""<header class="hero"><div class="in"><div class="kicker">DAILY MARKET REPORT</div>
<h1>📈 {esc(d['date'])} ({esc(d.get('weekday', ''))})</h1>
<p>{esc(d.get('generated_at', ''))} 기준 · 국내 장중 / 미국 전일 마감</p></div></header>"""

    panes = []  # (id, 탭 이름, html)

    # 요약
    sm = ""
    if d.get("summary"):
        sm += "<div class='card summary'><ul>" + "".join(f"<li>{esc(x)}</li>" for x in d["summary"]) + "</ul></div>"
    sm += "<div class='sec'><h2>한눈에 보기</h2><span class='tag'>누르면 해당 탭으로</span></div><div class='tiles'>"
    sm += quick_tile(hist, "kospi", "KOSPI", "kr") + quick_tile(hist, "kosdaq", "KOSDAQ", "kr")
    sm += quick_tile(hist, "nasdaq", "NASDAQ", "us") + quick_tile(hist, "sp500", "S&P 500", "us")
    sm += quick_tile(hist, "fx:USD", "🇺🇸 원/달러", "fx") + quick_tile(hist, "fx:JPY", "🇯🇵 원/100엔", "fx")
    sm += quick_tile(hist, "cm:GC=F", "🥇 금 ($/oz)", "cm") + quick_tile(hist, "cm:CL=F", "🛢 WTI ($/bbl)", "cm")
    sm += quick_tile(hist, "co:BTC-KRW", "₿ 비트코인 (원)", "coin", 0) + quick_tile(hist, "co:ETH-KRW", "Ξ 이더리움 (원)", "coin", 0)
    sm += "</div>"
    w_items = [("s:" + kr_symbol(r), r["name"], r["code"]) for r in d.get("watch_kr", []) if hist.get("s:" + kr_symbol(r))]
    w_items += [("s:" + r["ticker"], r["name"], r["ticker"] + " · 미국") for r in d.get("watch_us", []) if hist.get("s:" + r["ticker"])]
    if w_items:
        sm += ("<div class='sec'><h2>⭐ 관심종목</h2><span class='tag'>watchlist.txt 에서 추가·삭제</span></div>"
               + stock_cards(w_items))
    panes.append(("home", "📋 요약", sm))

    # 국내
    kr = "<div class='grid2'>" + chart_card("kospi", "KOSPI", find(idx, "KOSPI")) + chart_card("kosdaq", "KOSDAQ", find(idx, "KOSDAQ")) + "</div>"
    kr_items, seen = [], set()
    for r in d.get("top_value", []) + d.get("gainers", []) + d.get("losers", []):
        sym = kr_symbol(r)
        if sym and sym not in seen and hist.get("s:" + sym):
            seen.add(sym)
            kr_items.append(("s:" + sym, r["name"], sym.split(".")[0]))
    if kr_items:
        kr += "<div class='sec'><h2>🔎 주요 종목</h2><span class='tag'>눌러서 차트 보기</span></div>" + stock_cards(kr_items)
    kr += ("<div class='sec'><h2>📊 순위</h2></div><div class='grid2'><div class='card'><h3 class='h3'>💰 거래대금 상위</h3>"
           + rank_table(d.get("top_value", [])) + "</div>")
    if d.get("gainers") or d.get("losers"):
        kr += ("<div class='card'><h3 class='h3'>🔺 상승률 상위</h3>" + rank_table(d.get("gainers", []), True)
               + "<h3 class='h3' style='margin-top:14px'>🔻 하락률 상위</h3>" + rank_table(d.get("losers", []), True) + "</div>")
    kr += "</div>"
    panes.append(("kr", "🇰🇷 국내", kr))

    # 미국
    usp = "<div class='grid2'>" + chart_card("nasdaq", "NASDAQ", find(us, "NASDAQ")) + chart_card("sp500", "S&P 500", find(us, "S&P 500")) + "</div>"
    rest = [u for u in us if u["name"].upper().replace(" ", "") not in ("NASDAQ", "S&P500", "원/달러")]
    if rest:
        usp += "<div style='margin-top:14px'>" + tiles(rest) + "</div>"
    us_items = [("s:" + t, nm, t) for t, nm in US_STOCKS if hist.get("s:" + t)]
    if us_items:
        usp += "<div class='sec'><h2>🔎 빅테크</h2><span class='tag'>눌러서 차트 보기</span></div>" + stock_cards(us_items)
    panes.append(("us", "🇺🇸 미국", usp))

    # 코인
    co_items = [("co:" + sym, nm, f"{tk} · 원화") for sym, nm, tk in COINS if hist.get("co:" + sym)]
    if co_items:
        panes.append(("coin", "₿ 코인", "<p class='hint'>원화 기준 · 24시간 거래 · 카드를 누르면 캔들 차트</p>" + stock_cards(co_items)))

    # 원자재
    cm_items = [("cm:" + sym, nm, unit) for sym, nm, unit in COMMODITIES if hist.get("cm:" + sym)]
    if cm_items:
        panes.append(("cm", "🛢 원자재", "<p class='hint'>국제 선물 근월물 종가 · 카드를 누르면 차트</p>" + stock_cards(cm_items)))

    # 환율
    fx_items = [("fx:" + c, f"{flag} {nm}", f"{unit}{c} 기준") for c, nm, flag, unit, _ in FX if hist.get("fx:" + c)]
    if fx_items:
        panes.append(("fx", "💱 환율", "<p class='hint'>원화 기준 · 카드를 누르면 차트</p>" + stock_cards(fx_items)))

    # 뉴스 + 지난 리포트
    nw = ""
    if d.get("news"):
        nw += "<div class='card news'><ul>" + "".join(f"<li><span class='t'>{esc(n.get('time', ''))}</span>{esc(n['title'])}</li>" for n in d["news"]) + "</ul></div>"
    if archive:
        nw += "<div class='sec'><h2>🗂 지난 리포트</h2></div><div class='arch'>" + "".join(f"<a href='{SITE}reports/{a}.html'>{a}</a>" for a in archive) + "</div>"
    if nw:
        panes.append(("news", "📰 뉴스", nw))

    tabbar = ("<nav class='tabbar' role='tablist' aria-label='리포트 섹션'><div class='tb-in'>" +
              "".join(f"<button role='tab' data-tab='{pid}' aria-selected='{'true' if i == 0 else 'false'}'>{nm}</button>" for i, (pid, nm, _) in enumerate(panes)) +
              "</div></nav>")
    body = "".join(f"<section class='pane' id='pane-{pid}' role='tabpanel' data-pane='{pid}'{'' if i == 0 else ' hidden'}>{h}</section>"
                   for i, (pid, _, h) in enumerate(panes))
    foot = "<footer>지수·종목·코인·환율·원자재 차트: Yahoo Finance · 시세·순위·뉴스: 네이버 금융<br>투자 판단의 참고용이며 투자 권유가 아닙니다.</footer>"
    data_json = json.dumps(hist, separators=(",", ":")).replace("</", "<\\/")
    return ("<!doctype html><html lang='ko'><head><meta charset='utf-8'>"
            "<meta name='viewport' content='width=device-width, initial-scale=1'>"
            f"<title>주식 리포트</title><meta name='description' content='{esc(title)}'>"
            f"<meta property='og:title' content='📈 {esc(title)}'><meta property='og:description' content='국내·미국 지수, 종목, 원자재, 환율 차트'>"
            f"<style>{CSS}</style></head><body>" + head + tabbar + "<main class='wrap'>" + body + foot + "</main>" +
            MODAL + f"<script type='application/json' id='chart-data'>{data_json}</script><script>{JS}</script></body></html>")


def kakao_text(d):
    idx = " ".join(f"{i['name']} {num(i.get('price'))}({pct(i.get('rate'))})" for i in d.get("indices", [])[:2])
    nas = find(d.get("us", []), "NASDAQ")
    us = f"🇺🇸 나스닥 {pct(nas.get('rate'))}" if nas else ""
    top = ", ".join(f"{r['name']} {pct(r.get('rate'))}" for r in d.get("top_value", [])[:2])
    head = f"📈 {d['date'][5:].replace('-', '/')} 주식 리포트\n🇰🇷 {idx}\n{us}\n💰 {top}\n"
    w = d.get("watch_kr", []) + d.get("watch_us", [])
    if w:
        head += "⭐ " + ", ".join(f"{r['name']} {pct(r.get('rate'))}" for r in w[:3]) + "\n"
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
            hist[key] = fetch_history(sym, ohlc=True)
        except Exception as e:  # 차트 실패해도 리포트는 생성
            print(f"[WARN] {sym} 이력 실패: {e}", file=sys.stderr)
            hist[key] = []
    syms = []
    for r in d.get("top_value", []) + d.get("gainers", []) + d.get("losers", []):
        sym = kr_symbol(r)
        if sym and sym not in syms:
            syms.append(sym)
    for r in d.get("watch_kr", []):
        sym = kr_symbol(r)
        if sym and sym not in syms:
            syms.append(sym)
    syms += [r["ticker"] for r in d.get("watch_us", []) if r["ticker"] not in syms]
    syms += [t for t, _ in US_STOCKS if t not in syms]
    for sym in syms:
        try:
            hist["s:" + sym] = fetch_history(sym, ohlc=True)
        except Exception as e:
            print(f"[WARN] {sym} 이력 실패: {e}", file=sys.stderr)
    for sym, _, _ in COINS:
        try:
            hist["co:" + sym] = fetch_history(sym, ohlc=True)
        except Exception as e:
            print(f"[WARN] {sym} 실패: {e}", file=sys.stderr)
    for sym, _, _ in COMMODITIES:
        try:
            hist["cm:" + sym] = fetch_history(sym, ohlc=True)
        except Exception as e:
            print(f"[WARN] {sym} 실패: {e}", file=sys.stderr)
    try:
        hist.update(fetch_fx())
    except Exception as e:
        print(f"[WARN] 환율 실패: {e}", file=sys.stderr)
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
    print(f"\n({len(text)}자) · 차트 데이터: " + f"지수 {sum(1 for k in hist if ':' not in k)}개, 종목 {sum(1 for k in hist if k.startswith('s:'))}개, 환율 {sum(1 for k in hist if k.startswith('fx:'))}개, 원자재 {sum(1 for k in hist if k.startswith('cm:'))}개, 코인 {sum(1 for k in hist if k.startswith('co:'))}개")


if __name__ == "__main__":
    import urllib.parse
    main()

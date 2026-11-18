import os, math, requests
from statistics import mean

API_KEY = os.environ["OTCHARTS_API_KEY"]
API_URL = "https://otcharts.com/v1/candles"
PAIR, TIMEFRAME, CANDLE_LIMIT = "EURUSD_otc", 60, 1000
MIN_CANDLES, MIN_SCORE, MIN_VOTE_MARGIN = 220, 7, 2

def validate_candles(raw):
    out, seen = [], set()
    for c in raw:
        try:
            x = {k: (c[k] if k == "time" else float(c[k])) for k in ("time","open","high","low","close")}
            vals = [x[k] for k in ("open","high","low","close")]
            if not all(math.isfinite(v) for v in vals): continue
            if x["high"] < max(vals) or x["low"] > min(vals) or x["high"] < x["low"]: continue
            if x["time"] in seen: continue
            seen.add(x["time"]); out.append(x)
        except (KeyError, TypeError, ValueError): continue
    return sorted(out, key=lambda x: x["time"])

def get_candles():
    r = requests.get(API_URL, headers={"Authorization": f"Bearer {API_KEY}", "Accept":"application/json"},
        params={"venue":"quotex","symbol":PAIR,"tf":TIMEFRAME,"limit":CANDLE_LIMIT}, timeout=30)
    r.raise_for_status(); data = r.json()
    if data.get("symbol") != PAIR: raise RuntimeError("Market symbol mismatch")
    cs = validate_candles(data.get("candles", []))
    print("Requested:", CANDLE_LIMIT, "Received:", len(cs))
    if len(cs) < MIN_CANDLES: raise RuntimeError("Not enough valid candles")
    return cs

def ema(v,p):
    if len(v)<p: raise ValueError(f"Not enough EMA{p} data")
    k=2/(p+1); out=[mean(v[:p])]
    for x in v[p:]: out.append(x*k+out[-1]*(1-k))
    return out

def sma(v,p):
    if len(v)<p: raise ValueError(f"Not enough SMA{p} data")
    return [mean(v[max(0,i-p+1):i+1]) for i in range(len(v))]

def rsi_series(v,p=14):
    d=[v[i]-v[i-1] for i in range(1,len(v))]
    g=[max(x,0) for x in d]; l=[max(-x,0) for x in d]
    ag,al=mean(g[:p]),mean(l[:p]); out=[50.0]*p
    def val(a,b): return 100 if b==0 and a else (50 if b==0 else 100-100/(1+a/b))
    out.append(val(ag,al))
    for i in range(p,len(g)):
        ag=(ag*(p-1)+g[i])/p; al=(al*(p-1)+l[i])/p; out.append(val(ag,al))
    return out

def rsi(v,p=14): return rsi_series(v,p)[-1]

def macd_series(v):
    f,s=ema(v,12),ema(v,26); line=[a-b for a,b in zip(f[-len(s):],s)]
    return line,ema(line,9)

def macd(v):
    a,b=macd_series(v); return a[-1],b[-1]

def true_ranges(cs):
    return [max(cs[i]["high"]-cs[i]["low"],abs(cs[i]["high"]-cs[i-1]["close"]),abs(cs[i]["low"]-cs[i-1]["close"])) for i in range(1,len(cs))]

def atr(cs,p=14):
    t=true_ranges(cs); x=mean(t[:p])
    for z in t[p:]: x=(x*(p-1)+z)/p
    return x

def adx(cs,p=14):
    tr=[]; plus=[]; minus=[]
    for i in range(1,len(cs)):
        c,q=cs[i],cs[i-1]; up=c["high"]-q["high"]; dn=q["low"]-c["low"]
        tr.append(max(c["high"]-c["low"],abs(c["high"]-q["close"]),abs(c["low"]-q["close"])))
        plus.append(up if up>dn and up>0 else 0); minus.append(dn if dn>up and dn>0 else 0)
    t,a,b=sum(tr[:p]),sum(plus[:p]),sum(minus[:p]); dx=[]
    for i in range(p,len(tr)):
        t+=(tr[i]-t)/p; a+=(plus[i]-a)/p; b+=(minus[i]-b)/p
        x,y=(100*a/t,100*b/t) if t else (0,0); dx.append(100*abs(x-y)/(x+y) if x+y else 0)
    z=mean(dx[:p])
    for q in dx[p:]: z=(z*(p-1)+q)/p
    return z

def bollinger(v,p=20,m=2):
    w=v[-p:]; mid=mean(w); sd=math.sqrt(mean((x-mid)**2 for x in w))
    return mid+m*sd,mid-m*sd

def cci(cs,p=14):
    t=[(x["high"]+x["low"]+x["close"])/3 for x in cs[-p:]]; a=mean(t); d=mean(abs(x-a) for x in t)
    return (t[-1]-a)/(.015*d) if d else 0

def williams(cs,p=14):
    w=cs[-p:]; h=max(x["high"] for x in w); l=min(x["low"] for x in w)
    return -100*(h-w[-1]["close"])/(h-l) if h!=l else 0

def demarker(cs,p=14):
    u=[]; d=[]
    for i in range(-p,0):
        u.append(max(cs[i]["high"]-cs[i-1]["high"],0)); d.append(max(cs[i-1]["low"]-cs[i]["low"],0))
    a,b=mean(u),mean(d); return a/(a+b) if a+b else .5

def levels(cs,n=100):
    s=[]; r=[]; w=cs[-n:]
    for i in range(2,len(w)-2):
        q=w[i]; near=w[i-2:i]+w[i+1:i+3]
        if all(q["low"]<x["low"] for x in near): s.append(q["low"])
        if all(q["high"]>x["high"] for x in near): r.append(q["high"])
    return s,r

def patterns(cs):
    c,p=cs[-1],cs[-2]; body=abs(c["close"]-c["open"]); rng=max(c["high"]-c["low"],1e-12)
    up=c["high"]-max(c["open"],c["close"]); dn=min(c["open"],c["close"])-c["low"]; out=set()
    if p["close"]<p["open"] and c["close"]>c["open"] and c["open"]<=p["close"] and c["close"]>=p["open"]: out.add("BULL_ENGULF")
    if p["close"]>p["open"] and c["close"]<c["open"] and c["open"]>=p["close"] and c["close"]<=p["open"]: out.add("BEAR_ENGULF")
    if dn>=2*body and up<.25*rng and c["close"]>c["open"]: out.add("HAMMER")
    if up>=2*body and dn<.25*rng and c["close"]<c["open"]: out.add("STAR")
    if body<.1*rng: out.add("DOJI")
    if len(cs)>=3:
        a,b,d=cs[-3:]
        if a["close"]<a["open"] and abs(a["close"]-a["open"])>.5*(a["high"]-a["low"]) and abs(b["close"]-b["open"])<.3*(b["high"]-b["low"]) and d["close"]>d["open"] and d["close"]>(a["open"]+a["close"])/2: out.add("MORNING_STAR")
        if a["close"]>a["open"] and abs(a["close"]-a["open"])>.5*(a["high"]-a["low"]) and abs(b["close"]-b["open"])<.3*(b["high"]-b["low"]) and d["close"]<d["open"] and d["close"]<(a["open"]+a["close"])/2: out.add("EVENING_STAR")
    if len(cs)>=4 and all(x["close"]>x["open"] for x in cs[-4:-1]): out.add("THREE_GREEN")
    if len(cs)>=4 and all(x["close"]<x["open"] for x in cs[-4:-1]): out.add("THREE_RED")
    return out

def analyze_market(candles):
    cs=validate_candles(candles)
    if len(cs)<MIN_CANDLES: raise ValueError(f"Need at least {MIN_CANDLES} candles")
    cl=[x["close"] for x in cs]; hi=[x["high"] for x in cs]; lo=[x["low"] for x in cs]; c,p=cs[-1],cs[-2]
    a=atr(cs); rv=rsi_series(cl); ml,ms=macd_series(cl); pat=patterns(cs); sup,res=levels(cs)
    near_s=bool(sup and abs(c["close"]-min(sup,key=lambda x:abs(x-c["close"])))<.35*a)
    near_r=bool(res and abs(c["close"]-min(res,key=lambda x:abs(x-c["close"])))<.35*a)
    e5,e6,e9,e14,e20,e21,e26,e50,e200=[ema(cl,x) for x in (5,6,9,14,20,21,26,50,200)]
    s5,s50,s100=[sma(cl,x) for x in (5,50,100)]
    bu,bl=bollinger(cl); oldbu,oldbl=bollinger(cl[:-10])
    votes=[]; reasons=[]
    def add(name,d,w=1):
        if d in ("CALL","PUT"): votes.append((d,w)); reasons.append(name+"="+d)
    # 1-15 Price action
    add("01 support pin","CALL" if near_s and "HAMMER" in pat else None)
    add("02 resistance star","PUT" if near_r and "STAR" in pat else None)
    add("03 SBR retest","PUT" if p["close"]<c["close"] and near_r and c["close"]<c["open"] else None)
    add("04 RBS retest","CALL" if near_s and c["close"]>c["open"] else None)
    add("05 bullish engulf support","CALL" if near_s and "BULL_ENGULF" in pat else None)
    add("06 bearish engulf resistance","PUT" if near_r and "BEAR_ENGULF" in pat else None)
    add("07 morning star","CALL" if "MORNING_STAR" in pat else None)
    add("08 evening star","PUT" if "EVENING_STAR" in pat else None)
    add("09 three candle continuation","CALL" if "THREE_GREEN" in pat else ("PUT" if "THREE_RED" in pat else None))
    add("10 exhaustion reversal","PUT" if sum(x["close"]>x["open"] for x in cs[-7:-1])>=5 and c["high"]-c["low"]>1.7*a and c["close"]<c["open"] else ("CALL" if sum(x["close"]<x["open"] for x in cs[-7:-1])>=5 and c["high"]-c["low"]>1.7*a and c["close"]>c["open"] else None))
    add("11 inside bar break","CALL" if c["high"]<p["high"] and c["low"]>p["low"] and c["close"]>cs[-3]["high"] else ("PUT" if c["high"]<p["high"] and c["low"]>p["low"] and c["close"]<cs[-3]["low"] else None))
    hh=sorted(hi[-30:],reverse=True)[:2]; ll=sorted(lo[-30:])[:2]
    add("12 double top proxy","PUT" if abs(hh[0]-hh[1])<.3*a and c["close"]<min(lo[-15:]) else None)
    add("13 double bottom proxy","CALL" if abs(ll[0]-ll[1])<.3*a and c["close"]>max(hi[-15:]) else None)
    rn=round(c["close"]*2000)/2000
    add("14 round number rejection","PUT" if abs(c["high"]-rn)<.12*a and c["close"]<c["open"] else ("CALL" if abs(c["low"]-rn)<.12*a and c["close"]>c["open"] else None))
    gap=c["open"]-p["close"]
    add("15 gap fill","PUT" if gap>.25*a and c["close"]<c["open"] else ("CALL" if gap<-.25*a and c["close"]>c["open"] else None))
    # 16-22 trendline/channel approximations
    add("16 ascending line bounce","CALL" if min(lo[-20:])==c["low"] and c["close"]>c["open"] else None)
    add("17 descending line reject","PUT" if max(hi[-20:])==c["high"] and c["close"]<c["open"] else None)
    add("18 trendline breakout proxy","CALL" if c["close"]>max(hi[-6:-1]) else ("PUT" if c["close"]<min(lo[-6:-1]) else None))
    add("19 channel bounce","PUT" if c["high"]>=max(hi[-30:])-.15*a and c["close"]<c["open"] else ("CALL" if c["low"]<=min(lo[-30:])+.15*a and c["close"]>c["open"] else None))
    add("20 triangle breakout proxy","CALL" if max(hi[-10:])-min(lo[-10:])<max(hi[-30:-20])-min(lo[-30:-20]) and c["close"]>max(hi[-10:-1]) else ("PUT" if max(hi[-10:])-min(lo[-10:])<max(hi[-30:-20])-min(lo[-30:-20]) and c["close"]<min(lo[-10:-1]) else None))
    add("21 rising wedge breakdown proxy","PUT" if c["close"]<min(lo[-5:-1]) and mean(hi[-5:])>mean(hi[-10:-5]) else None)
    add("22 falling wedge breakout proxy","CALL" if c["close"]>max(hi[-5:-1]) and mean(lo[-5:])<mean(lo[-10:-5]) else None)
    # 23-30 averages
    add("23 EMA cross","CALL" if e9[-2]<=e21[-2] and e9[-1]>e21[-1] else ("PUT" if e9[-2]>=e21[-2] and e9[-1]<e21[-1] else None))
    add("24 EMA20 pullback","CALL" if c["close"]>e20[-1] and abs(c["low"]-e20[-1])<.2*a and c["close"]>c["open"] else ("PUT" if c["close"]<e20[-1] and abs(c["high"]-e20[-1])<.2*a and c["close"]<c["open"] else None))
    add("25 SMA50 bounce","CALL" if c["close"]>s50[-1] and abs(c["low"]-s50[-1])<.2*a and c["close"]>c["open"] else ("PUT" if c["close"]<s50[-1] and abs(c["high"]-s50[-1])<.2*a and c["close"]<c["open"] else None))
    add("26 EMA200 filter","CALL" if c["close"]>e200[-1] and e9[-1]>e21[-1] else ("PUT" if c["close"]<e200[-1] and e9[-1]<e21[-1] else None))
    add("27 rainbow EMA","CALL" if e6[-1]>e14[-1]>e26[-1] and abs(c["close"]-e14[-1])<.2*a else ("PUT" if e6[-1]<e14[-1]<e26[-1] and abs(c["close"]-e14[-1])<.2*a else None))
    add("28 SMA5 cross proxy","CALL" if p["close"]<=s5[-2]<c["close"] else ("PUT" if p["close"]>=s5[-2]>c["close"] else None))
    add("29 EMA squeeze breakout","CALL" if abs(e9[-1]-e21[-1])<.08*a and c["close"]>max(hi[-5:-1]) else ("PUT" if abs(e9[-1]-e21[-1])<.08*a and c["close"]<min(lo[-5:-1]) else None))
    add("30 SMA100 rejection","CALL" if abs(c["low"]-s100[-1])<.15*a and c["close"]>c["open"] else ("PUT" if abs(c["high"]-s100[-1])<.15*a and c["close"]<c["open"] else None))
    # 31-40 oscillators
    add("31 RSI reversal","PUT" if rv[-2]>70 and rv[-1]<70 else ("CALL" if rv[-2]<30 and rv[-1]>30 else None))
    add("32 RSI divergence proxy","PUT" if max(hi[-8:])>max(hi[-16:-8]) and max(rv[-8:])<max(rv[-16:-8]) else ("CALL" if min(lo[-8:])<min(lo[-16:-8]) and min(rv[-8:])>min(rv[-16:-8]) else None))
    add("33 RSI50 bounce","CALL" if e9[-1]>e21[-1] and rv[-2]<50<=rv[-1] else ("PUT" if e9[-1]<e21[-1] and rv[-2]>50>=rv[-1] else None))
    # stochastic approximation from rolling high/low
    stlo=min(lo[-14:]); sthi=max(hi[-14:]); sk=50 if sthi==stlo else 100*(c["close"]-stlo)/(sthi-stlo)
    add("34 stochastic extreme","CALL" if sk<20 and c["close"]>c["open"] else ("PUT" if sk>80 and c["close"]<c["open"] else None))
    add("35 MACD zero cross","CALL" if ml[-2]<=0<ml[-1] else ("PUT" if ml[-2]>=0>ml[-1] else None))
    hist=[x-y for x,y in zip(ml[-len(ms):],ms)]
    add("36 MACD histogram flip","CALL" if hist[-2]<=0<hist[-1] else ("PUT" if hist[-2]>=0>hist[-1] else None))
    cv=cci(cs)
    add("37 CCI extreme","PUT" if cv<100 and cci(cs[:-1])>200 else ("CALL" if cv>-100 and cci(cs[:-1])<-200 else None))
    wr=williams(cs)
    add("38 Williams bounce","PUT" if wr<-20 and williams(cs[:-1])>-20 else ("CALL" if wr>-80 and williams(cs[:-1])<-80 else None))
    dm=demarker(cs)
    add("39 DeMarker reversal","PUT" if dm<.7 and demarker(cs[:-1])>.7 else ("CALL" if dm>.3 and demarker(cs[:-1])<.3 else None))
    # AO proxy: SMA5(mid)-SMA34(mid)
    mids=[(x["high"]+x["low"])/2 for x in cs]; ao=sma(mids,5)[-1]-sma(mids,34)[-1]
    add("40 AO momentum","CALL" if ao>0 and c["close"]>c["open"] else ("PUT" if ao<0 and c["close"]<c["open"] else None))
    # 41-50 volatility/hybrid
    add("41 Bollinger reversal","PUT" if p["close"]>bollinger(cl[:-1])[0] and c["close"]<bu and c["close"]<c["open"] else ("CALL" if p["close"]<bollinger(cl[:-1])[1] and c["close"]>bl and c["close"]>c["open"] else None))
    add("42 Bollinger squeeze breakout","CALL" if bu-bl<oldbu-oldbl and c["close"]>bu else ("PUT" if bu-bl<oldbu-oldbl and c["close"]<bl else None))
    add("43 BB plus RSI","PUT" if c["close"]>=bu and rv[-1]>70 else ("CALL" if c["close"]<=bl and rv[-1]<30 else None))
    kc_u,kc_l=ema(cl,20)[-1]+1.5*a,ema(cl,20)[-1]-1.5*a
    add("44 Keltner squeeze proxy","CALL" if bu<kc_u and c["close"]>kc_u else ("PUT" if bl>kc_l and c["close"]<kc_l else None))
    psar=1 if c["close"]>p["high"] else (-1 if c["close"]<p["low"] else 0)
    add("45 SAR direction proxy","CALL" if psar==1 else ("PUT" if psar==-1 else None))
    add("46 SAR plus MACD","CALL" if psar==1 and ml[-1]>ms[-1] else ("PUT" if psar==-1 and ml[-1]<ms[-1] else None))
    ten=(max(hi[-9:])+min(lo[-9:]))/2; kij=(max(hi[-26:])+min(lo[-26:]))/2; span=(max(hi[-52:])+min(lo[-52:]))/2
    top=max((ten+kij)/2,span); bot=min((ten+kij)/2,span)
    add("47 Ichimoku cloud proxy","CALL" if p["close"]<=top<c["close"] else ("PUT" if p["close"]>=bot>c["close"] else None))
    add("48 Alligator EMA proxy","CALL" if e5[-1]>e9[-1]>e14[-1] and e5[-2]<=e9[-2] else ("PUT" if e5[-1]<e9[-1]<e14[-1] and e5[-2]>=e9[-2] else None))
    add("49 fractal breakout","CALL" if sup and c["close"]>max(sup) else ("PUT" if res and c["close"]<min(res) else None))
    fib_hi,fib_lo=max(hi[-30:]),min(lo[-30:]); fib=fib_hi-.618*(fib_hi-fib_lo)
    add("50 Fibonacci pullback","CALL" if abs(c["close"]-fib)<.15*a and e9[-1]>e21[-1] and c["close"]>c["open"] else ("PUT" if abs(c["close"]-(fib_lo+.618*(fib_hi-fib_lo)))<.15*a and e9[-1]<e21[-1] and c["close"]<c["open"] else None))
    # Prior support/resistance and candle context add weight, not extra independent strategies.
    if near_s: add("Support confluence","CALL",2)
    if near_r: add("Resistance confluence","PUT",2)
    bull=sum(w for d,w in votes if d=="CALL"); bear=sum(w for d,w in votes if d=="PUT")
    bc=sum(d=="CALL" for d,w in votes); rc=sum(d=="PUT" for d,w in votes)
    vol_ok=a>0 and c["high"]-c["low"]<=2*a
    direction="NO SIGNAL"
    if vol_ok and bull>=MIN_SCORE and bull-bear>=MIN_VOTE_MARGIN and bc>=3: direction="CALL"
    elif vol_ok and bear>=MIN_SCORE and bear-bull>=MIN_VOTE_MARGIN and rc>=3: direction="PUT"
    return {"pair":PAIR,"timeframe":"1 Minute","direction":direction,
        "bullish_score":bull,"bearish_score":bear,"bullish_setups":bc,"bearish_setups":rc,
        "minimum_score":MIN_SCORE,"minimum_vote_margin":MIN_VOTE_MARGIN,
        "reason":", ".join(reasons) if reasons else "No setup confirmed",
        "rsi":round(rv[-1],2),"adx":round(adx(cs),2),"atr":round(a,6),
        "macd":round(ml[-1],6),"macd_signal":round(ms[-1],6),
        "ema9":round(e9[-1],6),"ema21":round(e21[-1],6),"ema50":round(e50[-1],6),"ema200":round(e200[-1],6),
        "support":min(sup,key=lambda x:abs(x-c["close"])) if sup else None,
        "resistance":min(res,key=lambda x:abs(x-c["close"])) if res else None,
        "candlestick_patterns":sorted(pat),"candle_time":c["time"],"candles_analyzed":len(cs),
        "strategy_note":"Several chart-pattern rules are explicitly rough proxies, not full visual pattern recognition. Backtest out-of-sample before live use."}

if __name__=="__main__":
    result=analyze_market(get_candles())
    print("\\n========== PROFESSIONAL BOT ==========")
    for k,v in result.items(): print(f"{k.upper()}: {v}")
    print("======================================")

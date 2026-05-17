#!/usr/bin/env python3
"""Mission Control v3 - Modern dashboard with equity curves and real-time trade feed"""
import json, os, sys, time, signal, subprocess, threading
from datetime import datetime
from pathlib import Path
from http.server import HTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse

PROJECT_ROOT = Path("/home/yahwehatwork/human-ai")
TRADES_BIN   = PROJECT_ROOT/"agents/trading-agent/trades/binance"
TRADES_MT5   = PROJECT_ROOT/"agents/trading-agent/trades/mt5"
PID_BIN      = TRADES_BIN/"binance_trader.pid"
PID_MT5      = TRADES_MT5/"ea_trader.pid"
MT5_FILES    = Path.home()/".wine/drive_c/Program Files/MetaTrader 5/MQL5/Files"
MT5_STATUS   = MT5_FILES/"mt5_status.json"

def _pid(f):
    try: pid=int(Path(f).read_text().strip()); os.kill(pid,0); return pid
    except: return None

def _running(f): return _pid(f) is not None

def _start(script, log):
    try:
        p=subprocess.Popen(["python3","-u",str(script)],stdout=open(PROJECT_ROOT/"logs"/log,"a"),
            stderr=subprocess.STDOUT,cwd=str(PROJECT_ROOT),start_new_session=True)
        time.sleep(1.5); return {"status":"started","pid":p.pid}
    except Exception as e: return {"status":"error","error":str(e)}

def _stop(pf):
    pid=_pid(pf)
    if not pid: return {"status":"not_running"}
    try: os.kill(pid,signal.SIGTERM); return {"status":"stopped","pid":pid}
    except Exception as e: return {"status":"error","error":str(e)}

def _curve(trades_dir, limit=40):
    cum=0; pts=[]; lbls=[]
    for f in sorted(Path(trades_dir).glob("trades_*.jsonl")):
        for l in open(f):
            if l.strip():
                t=json.loads(l)
                if t.get("type")=="EXIT" and t.get("pnl") is not None:
                    cum+=float(t["pnl"]); pts.append(round(cum,2))
                    lbls.append(t.get("timestamp","")[:16])
    return pts[-limit:], lbls[-limit:]

def _today_trades(d):
    f=Path(d)/f"trades_{datetime.now().strftime('%Y%m%d')}.jsonl"
    return [json.loads(l) for l in open(f) if l.strip()] if f.exists() else []

def _wr(trades):
    ex=[t for t in trades if t.get("type")=="EXIT"]
    if not ex: return 0
    return round(len([t for t in ex if float(t.get("pnl",0))>0])/len(ex)*100,1)

class API:
    def status(self):
        return {"ts":datetime.now().isoformat(),"agents":self._agents(),"equity":self._equity(),
                "tasks":self._tasks(),"tba":self._tba(),"ints":self._ints(),"svcs":self._svcs()}

    def _agents(self):
        rf=PROJECT_ROOT/"core"/"config"/"llm_routing.json"; r={}
        if rf.exists(): r=json.loads(rf.read_text()).get("llm_routing",{}).get("agents",{})
        return [
            {"n":"OpenClaw","r":"Gateway","st":"active","m":r.get("openclaw",{}).get("model","")},
            {"n":"Hermes","r":"Architect","st":"active","m":r.get("hermes",{}).get("model","")},
            {"n":"OpenCode","r":"Engineer","st":"active","m":r.get("opencode",{}).get("model","")},
            {"n":"Pi.dev","r":"Guardian","st":"active","m":r.get("pidev",{}).get("model","")},
            {"n":"FreqTrade","r":"BTC/USDT","st":"running" if _running(PID_BIN) else "stopped","m":"Binance Demo"},
            {"n":"EA/MT5","r":"XAU/XAG","st":"running" if _running(PID_MT5) else "stopped","m":"yfinance LIVE"},
            {"n":"Social","r":"Content","st":"configured","m":r.get("social_media",{}).get("model","")},
            {"n":"Research","r":"Research","st":"active","m":"DeepSeek"},
        ]

    def _equity(self):
        out={}
        sf=TRADES_BIN/"state.json"
        if sf.exists():
            s=json.loads(sf.read_text()); td=_today_trades(TRADES_BIN); c,lb=_curve(TRADES_BIN,40)
            out["binance"]={"balance":s.get("current_balance",0),"starting":s.get("starting_balance",0),
                "pnl":s.get("total_pnl",0),"trades_today":len([t for t in td if t.get("type")=="EXIT"]),
                "running":_running(PID_BIN),"curve":c,"curve_labels":lb,"win_rate":_wr(td),"open":0}
        sf=TRADES_MT5/"state.json"
        if sf.exists():
            s=json.loads(sf.read_text()); td=_today_trades(TRADES_MT5); c,lb=_curve(TRADES_MT5,40)
            # state.json is now fully dynamic — written every 60s by liveea.py
            # Primary values come directly from state.json (already has MT5 live data)
            real_balance  = s.get("balance",   s.get("mt5_balance", s.get("deposit",5000)))
            real_equity   = s.get("equity",    s.get("mt5_equity",  s.get("deposit",5000)))
            real_open     = s.get("open_positions", s.get("mt5_positions", 0))
            real_float    = s.get("floating_pnl",   s.get("mt5_floating", 0))
            mt5_live_ok   = s.get("mt5_live", False)
            session_active= s.get("session_active", False)
            pnl_today     = s.get("pnl_today", 0.0)
            daily_loss_pct= s.get("daily_loss_pct", 0.0)
            drawdown_pct  = s.get("drawdown_pct", 0.0)
            out["ea"]={"equity":real_equity,"balance":real_balance,"deposit":s.get("deposit",5000),
                "pnl":s.get("total_pnl",0),"pnl_today":pnl_today,
                "trades":s.get("trade_count",0),
                "floating_pnl":real_float,
                "trades_today":len([t for t in td if t.get("type")=="EXIT"]),
                "open":real_open,"running":_running(PID_MT5),
                "curve":c,"curve_labels":lb,"win_rate":_wr(td),
                "mt5_live":mt5_live_ok,"session_active":session_active,
                "daily_loss_pct":daily_loss_pct,"drawdown_pct":drawdown_pct,
                "mt5_account":s.get("mt5_account",""),
                "mt5_server":s.get("mt5_server","ICMarketsCS-Demo")}
        return out

    def _tasks(self):
        tf=PROJECT_ROOT/"unified_tasks.json"
        if not tf.exists(): return {"pending":0,"completed":0,"in_progress":0}
        d=json.loads(tf.read_text()); tq=d.get("task_queue",{})
        return {"pending":len(tq.get("pending",[])),"completed":len(tq.get("completed",[])),"in_progress":len(tq.get("in_progress",[]))}

    def _tba(self):
        from collections import Counter
        tf=PROJECT_ROOT/"unified_tasks.json"
        if not tf.exists(): return {}
        d=json.loads(tf.read_text())
        return dict(Counter(t.get("agent","?") for t in d.get("task_queue",{}).get("pending",[])))

    def _ints(self):
        import requests; from dotenv import load_dotenv; load_dotenv(PROJECT_ROOT/".env")
        results=[]; lock=threading.Lock()
        def chk(name,fn):
            try: st,det=fn()
            except Exception as e: st,det="error",str(e)[:40]
            with lock: results.append({"s":name,"st":st,"d":det})
        def _or():
            k=os.getenv("OPENROUTER_API_KEY","")
            if not k: return "missing","No key"
            r=requests.get("https://openrouter.ai/api/v1/models",headers={"Authorization":f"Bearer {k}"},timeout=5)
            return ("connected",f"{len(r.json().get('data',[]))} models") if r.ok else ("error",str(r.status_code))
        def _nv():
            k=os.getenv("NVIDIA_API_KEY","")
            if not k: return "missing","No key"
            r=requests.get("https://integrate.api.nvidia.com/v1/models",headers={"Authorization":f"Bearer {k}"},timeout=5)
            return ("connected",f"{len(r.json().get('data',[]))} models") if r.ok else ("error",str(r.status_code))
        def _sb():
            try:
                r=requests.get("http://localhost:3000/",timeout=3)
                return ("connected","PostgREST OK") if r.status_code in(200,400) else ("error",str(r.status_code))
            except: return "stopped","Docker down"
        def _alp():
            k=os.getenv("ALPACA_API_KEY",""); s=os.getenv("ALPACA_SECRET_KEY","")
            if not k: return "missing","No key"
            r=requests.get("https://paper-api.alpaca.markets/v2/account",
                headers={"APCA-API-KEY-ID":k,"APCA-API-SECRET-KEY":s},timeout=5)
            return ("connected",f"Paper {r.json().get('account_number','')[:8]}") if r.ok else ("error",str(r.status_code))
        def _cmc():
            k=os.getenv("COINMARKETCAP_API_KEY","")
            if not k: return "missing","No key"
            r=requests.get("https://pro-api.coinmarketcap.com/v1/global-metrics/quotes/latest",
                headers={"X-CMC_PRO_API_KEY":k},timeout=5)
            if r.ok: return "connected",f"BTC dom {r.json()['data']['btc_dominance']:.1f}%"
            return "error",str(r.status_code)
        def _fg():
            try:
                r=requests.get("https://api.alternative.me/fng/?limit=1",timeout=5)
                d=r.json()["data"][0]; return "connected",f"F/G {d['value']} ({d['value_classification']})"
            except Exception as e: return "error",str(e)[:30]
        ths=[threading.Thread(target=chk,args=(n,f)) for n,f in
             [("OpenRouter",_or),("NVIDIA NIM",_nv),("Supabase",_sb),("Alpaca",_alp),("CoinMarketCap",_cmc),("Fear/Greed",_fg)]]
        for t in ths: t.daemon=True; t.start()
        for t in ths: t.join(timeout=7)
        return results

    def _svcs(self):
        svcs=[]
        try:
            r=subprocess.run(["docker","ps","--format","{{.Names}}:{{.Status}}"],capture_output=True,text=True,timeout=5)
            running={l.split(":")[0] for l in r.stdout.strip().split("\n") if ":"}
        except: running=set()
        for n,k in [("PostgreSQL","db"),("PostgREST","rest"),("Adminer","adminer")]:
            svcs.append({"n":n,"st":"running" if any(k in r for r in running) else "stopped"})
        svcs.append({"n":"Binance Trader","st":"running" if _running(PID_BIN) else "stopped"})
        svcs.append({"n":"EA Trader","st":"running" if _running(PID_MT5) else "stopped"})
        try:
            r=subprocess.run(["pgrep","-f","automode.py"],capture_output=True,text=True)
            svcs.append({"n":"Automode","st":"running" if r.returncode==0 else "stopped"})
        except: svcs.append({"n":"Automode","st":"unknown"})
        od=PROJECT_ROOT/"obsidian"/"trades"; last="never"
        if od.exists():
            fs=list(od.glob("*.md"))
            if fs: lf=max(fs,key=lambda x:x.stat().st_mtime); last=f"{(time.time()-lf.stat().st_mtime)/60:.0f}m ago"
        svcs.append({"n":"Obsidian","st":"active","d":last})
        return svcs

    def events(self, limit=30):
        evs=[]
        for qf in [PROJECT_ROOT/"data"/"feeds"/"binance_live_trades.jsonl",PROJECT_ROOT/"data"/"feeds"/"ea_live_trades.jsonl"]:
            if not qf.exists(): continue
            try:
                for l in open(qf).readlines()[-15:]:
                    if l.strip():
                        o=json.loads(l); o["_src"]=qf.stem; evs.append(o)
            except: pass
        evs.sort(key=lambda e:e.get("timestamp",""),reverse=True)
        return evs[:limit]

    def ctrl(self, trader, action):
        m={"binance":(PROJECT_ROOT/"agents/trading-agent/live_trading_binance.py",PID_BIN,"live_trading_binance.log"),
           "ea":(PROJECT_ROOT/"agents/trading-agent/live_trading_ea.py",PID_MT5,"live_trading_ea.log")}
        if trader not in m: return {"status":"error"}
        script,pf,log=m[trader]
        if action=="start":
            if _running(pf): return {"status":"already_running","pid":_pid(pf)}
            return _start(script,log)
        return _stop(pf)

    def automode(self,agent=""):
        try:
            cmd=["python3","-u",str(PROJECT_ROOT/"core"/"orchestration"/"automode.py")]
            if agent: cmd.append(agent)
            p=subprocess.Popen(cmd,stdout=open(PROJECT_ROOT/"data"/"logs"/"automode_dash.log","a"),stderr=subprocess.STDOUT,cwd=str(PROJECT_ROOT),start_new_session=True)
            return {"status":"started","pid":p.pid}
        except Exception as e: return {"status":"error","error":str(e)}

    def trigger(self,agent,command):
        e={"agent":agent,"command":command,"timestamp":datetime.now().isoformat()}
        q=PROJECT_ROOT/"data"/"feeds"/"openclaw_notifications.jsonl"; q.parent.mkdir(exist_ok=True)
        with open(q,"a") as f: f.write(json.dumps(e)+"\n")
        return {"status":"queued"}

HTML = r"""<!DOCTYPE html>
<html>
<head>
<meta charset="UTF-8">
<title>Mission Control v3</title>
<style>
:root{--bg:#060910;--bg2:#0c1220;--bg3:#111928;--border:#1e2d45;--green:#10b981;--red:#ef4444;--blue:#3b82f6;--yellow:#f59e0b;--cyan:#06b6d4;--purple:#8b5cf6;--text:#e2e8f0;--muted:#64748b}
*{margin:0;padding:0;box-sizing:border-box;font-family:'Courier New',monospace}
body{background:var(--bg);color:var(--text);min-height:100vh;font-size:13px}
.topbar{background:linear-gradient(90deg,#0a0f1e,#0c1629);border-bottom:1px solid var(--border);padding:10px 20px;display:flex;justify-content:space-between;align-items:center}
.topbar h1{color:var(--cyan);font-size:1.1em;letter-spacing:3px;text-shadow:0 0 20px rgba(6,182,212,.4)}
.topbar .meta{text-align:right;font-size:.75em;color:var(--muted)}
.grid{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;padding:12px}
.panel{background:var(--bg2);border:1px solid var(--border);border-radius:8px;padding:12px;position:relative}
.panel::before{content:'';position:absolute;top:0;left:0;right:0;height:2px;border-radius:8px 8px 0 0}
.panel.p-trade::before{background:linear-gradient(90deg,var(--green),var(--cyan))}
.panel.p-agents::before{background:linear-gradient(90deg,var(--blue),var(--purple))}
.panel.p-tasks::before{background:linear-gradient(90deg,var(--yellow),var(--red))}
.panel.p-ints::before{background:linear-gradient(90deg,var(--purple),var(--blue))}
.panel.p-svc::before{background:linear-gradient(90deg,var(--cyan),var(--green))}
.panel.p-log::before{background:linear-gradient(90deg,var(--muted),var(--border))}
h2{color:var(--blue);font-size:.75em;letter-spacing:1.5px;text-transform:uppercase;margin-bottom:10px;padding-bottom:6px;border-bottom:1px solid var(--border)}
.row{display:flex;justify-content:space-between;align-items:center;padding:4px 0;border-bottom:1px solid rgba(30,45,69,.5)}
.label{color:var(--muted);font-size:.78em}.val{font-weight:bold;font-size:.78em}
.g{color:var(--green)}.r{color:var(--red)}.b{color:var(--blue)}.y{color:var(--yellow)}.c{color:var(--cyan)}.m{color:var(--muted)}
.eq-big{font-size:1.6em;font-weight:bold;margin:6px 0;color:var(--cyan);text-shadow:0 0 15px rgba(6,182,212,.3)}
.eq-sub{font-size:.75em;color:var(--muted);margin-bottom:8px}
.badge{padding:2px 7px;border-radius:20px;font-size:.65em;font-weight:bold;letter-spacing:.5px}
.b-live{background:rgba(16,185,129,.15);color:var(--green);border:1px solid rgba(16,185,129,.4)}
.b-off{background:rgba(239,68,68,.1);color:var(--red);border:1px solid rgba(239,68,68,.3)}
.dot{width:7px;height:7px;border-radius:50%;display:inline-block;margin-right:5px}
.dot-g{background:var(--green);box-shadow:0 0 6px var(--green)}.dot-r{background:var(--red)}.dot-y{background:var(--yellow)}
.btn{padding:5px 12px;border-radius:5px;cursor:pointer;font-family:inherit;font-size:.72em;border:1px solid;transition:all .15s;letter-spacing:.3px}
.btn-g{background:rgba(16,185,129,.1);border-color:rgba(16,185,129,.5);color:var(--green)}.btn-g:hover{background:rgba(16,185,129,.25)}
.btn-r{background:rgba(239,68,68,.1);border-color:rgba(239,68,68,.4);color:var(--red)}.btn-r:hover{background:rgba(239,68,68,.2)}
.btn-b{background:rgba(59,130,246,.1);border-color:rgba(59,130,246,.4);color:var(--blue)}.btn-b:hover{background:rgba(59,130,246,.2)}
.btn-m{background:rgba(100,116,139,.1);border-color:rgba(100,116,139,.3);color:var(--muted)}.btn-m:hover{background:rgba(100,116,139,.2)}
.controls{margin-top:8px;display:flex;flex-wrap:wrap;gap:4px}
.trade-box{background:var(--bg3);border:1px solid var(--border);border-radius:6px;padding:9px;margin-top:8px}
.trade-box h3{font-size:.72em;color:var(--blue);text-transform:uppercase;letter-spacing:1px;margin-bottom:5px}
canvas.sparkline{width:100%!important;height:50px;margin-top:6px;border-radius:4px}
.log-area{max-height:180px;overflow-y:auto;font-size:.72em;margin-top:4px}
.log-row{display:flex;gap:6px;padding:3px 0;border-bottom:1px solid rgba(30,45,69,.4)}
.lt{color:var(--muted);min-width:55px}.ls{color:var(--blue);min-width:95px}.lm{color:#94a3b8;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.full{grid-column:1/-1}.two{grid-column:span 2}
.stat-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:6px}
.stat{background:var(--bg3);border:1px solid var(--border);border-radius:5px;padding:6px;text-align:center}
.stat .sv{font-size:1.1em;font-weight:bold}.stat .sk{font-size:.65em;color:var(--muted);margin-top:2px}
.pnl-pos{color:var(--green)}.pnl-neg{color:var(--red)}.pnl-z{color:var(--muted)}
</style>
</head>
<body>
<div class="topbar">
  <h1>⬡ HUMAN-AI SWARM // MISSION CONTROL v3</h1>
  <div class="meta"><div id="clk">—</div><div>auto-refresh 10s</div></div>
</div>
<div class="grid">

<div class="panel p-trade two" id="trade-panel">
  <h2>⚡ Trading Agents</h2>
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px">
    <div class="trade-box">
      <h3>Binance BTC/USDT <span id="b-badge" class="badge b-off">OFF</span></h3>
      <div id="b-eq" class="eq-big">—</div>
      <div id="b-sub" class="eq-sub">—</div>
      <div class="stat-row" id="b-stats"></div>
      <canvas id="b-chart" class="sparkline"></canvas>
      <div class="controls">
        <button class="btn btn-g" onclick="ctrl('binance','start')">▶ START</button>
        <button class="btn btn-r" onclick="ctrl('binance','stop')">■ STOP</button>
        <button class="btn btn-b" onclick="trig('freqtrade','backtest')">⟳ Backtest</button>
      </div>
    </div>
    <div class="trade-box">
      <h3>EA Metals XAUUSD <span id="e-badge" class="badge b-off">OFF</span> <span id="e-src" style="font-size:.55em;color:#f59e0b"></span></h3>
      <div style="font-size:.65em;color:var(--muted);margin-bottom:4px" id="e-acct"></div>
      <div id="e-eq" class="eq-big">—</div>
      <div id="e-sub" class="eq-sub">—</div>
      <div class="stat-row" id="e-stats"></div>
      <canvas id="e-chart" class="sparkline"></canvas>
      <div class="controls">
        <button class="btn btn-g" onclick="ctrl('ea','start')">▶ START</button>
        <button class="btn btn-r" onclick="ctrl('ea','stop')">■ STOP</button>
        <button class="btn btn-b" onclick="trig('ea','backtest')">⟳ Backtest</button>
      </div>
    </div>
  </div>
</div>

<div class="panel p-tasks">
  <h2>📋 Task Queue</h2>
  <div id="task-panel"></div>
  <div class="controls" style="margin-top:10px">
    <button class="btn btn-g" onclick="automode('')">⚡ AUTO ALL</button>
    <button class="btn btn-m" onclick="automode('Hermes')">Hermes</button>
    <button class="btn btn-m" onclick="automode('OpenCode')">OpenCode</button>
    <button class="btn btn-m" onclick="automode('Pi.dev')">Pi.dev</button>
  </div>
</div>

<div class="panel p-agents">
  <h2>🤖 Agents</h2>
  <div id="agents-panel"></div>
</div>

<div class="panel p-ints">
  <h2>🔌 Integrations</h2>
  <div id="ints-panel"></div>
</div>

<div class="panel p-svc">
  <h2>⚙️ Services</h2>
  <div id="svc-panel"></div>
  <div class="controls" style="margin-top:8px">
    <button class="btn btn-m" onclick="trig('system','sync')">↑ Obsidian</button>
    <button class="btn btn-m" onclick="trig('system','backup')">💾 GDrive</button>
    <button class="btn btn-m" onclick="trig('social','post')">📱 Social</button>
  </div>
</div>

<div class="panel p-log full">
  <h2>📡 Live Trade Feed</h2>
  <div class="log-area" id="log-area">
    <div class="log-row"><span class="lt">--:--:--</span><span class="ls">[system]</span><span class="lm">Waiting...</span></div>
  </div>
</div>

</div>

<script>
function clk(){document.getElementById('clk').textContent=new Date().toUTCString().replace(' GMT',' UTC')}
setInterval(clk,1000);clk();

function sparkline(canvasId, data, color){
  const c=document.getElementById(canvasId); if(!c||!data||!data.length)return;
  const ctx=c.getContext('2d'); const W=c.offsetWidth||300; const H=50;
  c.width=W; c.height=H;
  const mn=Math.min(...data), mx=Math.max(...data), rng=mx-mn||1;
  ctx.clearRect(0,0,W,H);
  // Fill
  ctx.beginPath();
  data.forEach((v,i)=>{const x=i/(data.length-1)*W,y=H-(v-mn)/rng*(H-4)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)});
  ctx.lineTo(W,H);ctx.lineTo(0,H);ctx.closePath();
  ctx.fillStyle=color+'20';ctx.fill();
  // Line
  ctx.beginPath();
  data.forEach((v,i)=>{const x=i/(data.length-1)*W,y=H-(v-mn)/rng*(H-4)-2;i===0?ctx.moveTo(x,y):ctx.lineTo(x,y)});
  ctx.strokeStyle=color;ctx.lineWidth=1.5;ctx.stroke();
}

async function fetchAll(){
  try{
    const[s,ev]=await Promise.all([fetch('/api/status').then(r=>r.json()),fetch('/api/events').then(r=>r.json())]);
    renderTrade(s.equity);
    renderAgents(s.agents);
    renderTasks(s.tasks,s.tba);
    renderInts(s.ints);
    renderSvcs(s.svcs);
    renderEvents(ev);
  }catch(e){console.error(e)}
}

function pnlCls(v){return v>0?'pnl-pos':v<0?'pnl-neg':'pnl-z'}
function pnlPfx(v){return v>=0?'+':''}

function renderTrade(eq){
  if(eq&&eq.binance){
    const b=eq.binance; const run=b.running;
    document.getElementById('b-badge').className='badge '+(run?'b-live':'b-off');
    document.getElementById('b-badge').textContent=run?'LIVE':'OFF';
    document.getElementById('b-eq').innerHTML=`$${(b.balance||0).toLocaleString('en',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
    document.getElementById('b-eq').className='eq-big '+(run?'g':'m');
    document.getElementById('b-sub').innerHTML=`PnL: <span class="${pnlCls(b.pnl)}">${pnlPfx(b.pnl)}$${(b.pnl||0).toFixed(4)}</span> &nbsp; WR: <span class="c">${b.win_rate||0}%</span>`;
    document.getElementById('b-stats').innerHTML=`
      <div class="stat"><div class="sv c">${b.trades_today||0}</div><div class="sk">Today</div></div>
      <div class="stat"><div class="sv ${pnlCls(b.pnl)}">${pnlPfx(b.pnl)}$${(b.pnl||0).toFixed(2)}</div><div class="sk">Total PnL</div></div>
      <div class="stat"><div class="sv y">${b.win_rate||0}%</div><div class="sk">Win Rate</div></div>`;
    if(b.curve&&b.curve.length>1) sparkline('b-chart',b.curve,b.pnl>=0?'#10b981':'#ef4444');
  }
  if(eq&&eq.ea){
    const e=eq.ea; const run=e.running;
    document.getElementById('e-badge').className='badge '+(run?'b-live':'b-off');
    document.getElementById('e-badge').textContent=run?'LIVE':'OFF';
    // Primary display: MT5 live account if active, otherwise local simulation estimate
    const isLive = e.mt5_live;
    document.getElementById('e-src').textContent = isLive ? '● MT5 LIVE' : '● LOCAL EST';
    document.getElementById('e-src').style.color  = isLive ? '#10b981' : '#f59e0b';
    // Account info line
    // Account info: server + account number
    if(e.mt5_account){
      document.getElementById('e-acct').textContent=`${e.mt5_server||'ICMarketsCS-Demo'}  #${e.mt5_account}`;
    }
    // Main balance — always MT5 real balance from dynamic state.json
    const primaryBal = e.balance || e.equity || 5000;
    document.getElementById('e-eq').innerHTML=`$${primaryBal.toLocaleString('en',{minimumFractionDigits:2,maximumFractionDigits:2})}`;
    document.getElementById('e-eq').className='eq-big '+(run?'g':'m');
    // Sub-line: floating, open positions, session status
    const floatStr = `Float: <span class="${pnlCls(e.floating_pnl||0)}">${pnlPfx(e.floating_pnl||0)}$${(e.floating_pnl||0).toFixed(2)}</span> &nbsp; `;
    const sessionStr = `<span class="${e.session_active?'g':'m'}" style="font-size:.7em">${e.session_active?'● SESSION':'○ CLOSED'}</span>`;
    document.getElementById('e-sub').innerHTML=`${floatStr}Open: <span class="c">${e.open||0}</span> &nbsp; ${sessionStr} &nbsp; Today: <span class="${pnlCls(e.pnl_today||0)}">${pnlPfx(e.pnl_today||0)}$${(e.pnl_today||0).toFixed(2)}</span>`;
    // Stats: daily loss %, drawdown %, total trades, win rate
    const dlCls = (e.daily_loss_pct||0) > 2 ? 'r' : (e.daily_loss_pct||0) > 1 ? 'y' : 'g';
    const ddCls = (e.drawdown_pct||0)   > 4 ? 'r' : (e.drawdown_pct||0)   > 2 ? 'y' : 'g';
    document.getElementById('e-stats').innerHTML=`
      <div class="stat"><div class="sv ${dlCls}">${(e.daily_loss_pct||0).toFixed(1)}%/3%</div><div class="sk">Daily Loss</div></div>
      <div class="stat"><div class="sv ${ddCls}">${(e.drawdown_pct||0).toFixed(1)}%/5%</div><div class="sk">Drawdown</div></div>
      <div class="stat"><div class="sv y">${e.win_rate||0}%</div><div class="sk">Win Rate</div></div>`;
    if(e.curve&&e.curve.length>1) sparkline('e-chart',e.curve,e.pnl>=0?'#10b981':'#ef4444');
  }
}

function renderAgents(ag){
  document.getElementById('agents-panel').innerHTML=ag.map(a=>{
    const sc=a.st==='running'||a.st==='active'?'g':a.st==='configured'?'y':'r';
    const dc=sc==='g'?'dot-g':sc==='y'?'dot-y':'dot-r';
    const m=(a.m||'').split('/').pop().split(':')[0].substr(0,16);
    return `<div class="row"><span class="label"><span class="dot ${dc}"></span>${a.n} <span class="m" style="font-size:.68em">${m}</span></span><span class="${sc}" style="font-size:.7em">${a.st.toUpperCase()}</span></div>`;
  }).join('');
}

function renderTasks(t,by){
  let h=`<div class="row"><span class="label">Pending</span><span class="val y">${t.pending}</span></div>
         <div class="row"><span class="label">In Progress</span><span class="val b">${t.in_progress}</span></div>
         <div class="row"><span class="label">Completed</span><span class="val g">${t.completed}</span></div>`;
  if(by){
    h+='<div style="margin-top:8px;border-top:1px solid var(--border);padding-top:6px">';
    Object.entries(by).sort((a,b)=>b[1]-a[1]).slice(0,6).forEach(([ag,cnt])=>{
      h+=`<div class="row"><span class="label" style="font-size:.72em">${ag}</span><span class="val" style="font-size:.72em">${cnt}</span></div>`;
    });
    h+='</div>';
  }
  document.getElementById('task-panel').innerHTML=h;
}

function renderInts(ints){
  if(!ints) return;
  document.getElementById('ints-panel').innerHTML=ints.map(i=>{
    const sc=i.st==='connected'?'g':i.st==='configured'?'y':'r';
    const dc=sc==='g'?'dot-g':sc==='y'?'dot-y':'dot-r';
    return `<div class="row"><span class="label"><span class="dot ${dc}"></span>${i.s}</span><span class="${sc}" style="font-size:.7em" title="${i.d||''}">${i.st.toUpperCase()}</span></div>`;
  }).join('');
}

function renderSvcs(svcs){
  if(!svcs) return;
  document.getElementById('svc-panel').innerHTML=svcs.map(s=>{
    const sc=s.st==='running'||s.st==='active'?'g':s.st==='stopped'?'r':'y';
    const dc=sc==='g'?'dot-g':sc==='r'?'dot-r':'dot-y';
    return `<div class="row"><span class="label"><span class="dot ${dc}"></span>${s.n}</span><span class="${sc}" style="font-size:.7em">${s.st.toUpperCase()}${s.d?' ('+s.d+')':''}</span></div>`;
  }).join('');
}

function renderEvents(evs){
  if(!evs||!evs.length) return;
  document.getElementById('log-area').innerHTML=evs.map(e=>{
    const src=e._src||'sys'; const d=e.data||e;
    let msg='';
    if(d.type==='ENTRY') msg=`ENTRY ${d.symbol||''} ${d.direction||d.side||''} @ $${(d.entry_price||d.price||0).toFixed(2)}`;
    else if(d.type==='EXIT'){const p=d.pnl||d.pnl_usdt||0;msg=`EXIT ${d.symbol||''} PnL: <span class="${p>=0?'pnl-pos':'pnl-neg'}">${p>=0?'+':''}$${Number(p).toFixed(4)}</span> [${d.reason||''}]`;}
    else msg=d.message||d.command||d.status||JSON.stringify(d).substr(0,60);
    return `<div class="log-row"><span class="lt">${(e.timestamp||'').substr(11,8)}</span><span class="ls">[${src.replace('_live_trades','')}]</span><span class="lm">${msg}</span></div>`;
  }).join('');
}

async function ctrl(trader,action){
  if(action==='stop'&&!confirm('Stop '+trader.toUpperCase()+'?')) return;
  const r=await fetch('/api/ctrl',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({trader,action})});
  const d=await r.json();
  alert(trader.toUpperCase()+' '+action+': '+d.status+(d.pid?' PID '+d.pid:''));
  setTimeout(fetchAll,2000);
}

async function automode(agent){
  const r=await fetch('/api/automode',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent})});
  const d=await r.json();
  alert('AutoMode '+(agent||'ALL')+': '+d.status);
}

async function trig(agent,cmd){
  await fetch('/api/trigger',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({agent,command:cmd})});
}

fetchAll();
setInterval(fetchAll,10000);
</script>
</body>
</html>"""

_api = API()

class Handler(SimpleHTTPRequestHandler):
    def do_GET(self):
        p=urlparse(self.path).path
        if p in('/','index.html'): self._html(HTML)
        elif p=='/api/status': self._json(_api.status())
        elif p=='/api/events': self._json(_api.events())
        else: self.send_response(404);self.end_headers()

    def do_POST(self):
        p=urlparse(self.path).path
        n=int(self.headers.get('Content-Length',0))
        b=json.loads(self.rfile.read(n)) if n else {}
        if p=='/api/ctrl': self._json(_api.ctrl(b.get('trader',''),b.get('action','')))
        elif p=='/api/trigger': self._json(_api.trigger(b.get('agent',''),b.get('command','')))
        elif p=='/api/automode': self._json(_api.automode(b.get('agent','')))
        else: self.send_response(404);self.end_headers()

    def _html(self,c): self.send_response(200);self.send_header('Content-Type','text/html');self.end_headers();self.wfile.write(c.encode())
    def _json(self,d): self.send_response(200);self.send_header('Content-Type','application/json');self.send_header('Access-Control-Allow-Origin','*');self.end_headers();self.wfile.write(json.dumps(d,default=str).encode())
    def log_message(self,*_): pass

def main():
    port=int(os.environ.get('MC_PORT',10000))
    s=HTTPServer(('0.0.0.0',port),Handler)
    print(f"Mission Control v3 → http://localhost:{port}")
    try: s.serve_forever()
    except KeyboardInterrupt: s.shutdown()

if __name__=="__main__": main()

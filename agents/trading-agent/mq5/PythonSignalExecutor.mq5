//+------------------------------------------------------------------+
//| MetalEA.mq5                                                      |
//| Reads trade signals from Python via MQL5/Files/python_signal.json|
//| Attach to any XAUUSD or XAGUSD chart                             |
//| Start Python side: python3 ~/human-ai/liveea.py                 |
//+------------------------------------------------------------------+
#property copyright "Human-AI Swarm"
#property version   "3.0"
#property description "MetalEA — bridges Python signals to MT5 orders"
#property strict

input double  DefaultLot    = 0.01;    // Fallback lot size
input double  MaxLot        = 2.0;     // Maximum lot size
input int     MagicNumber   = 20260512;
input int     SlippagePips  = 30;
input bool    EnableTrading = true;
input string  SignalFile    = "python_signal.json";
input string  StatusFile    = "mt5_status.json";
input int     CheckEveryMS  = 2000;    // Check signal every 2 seconds

string lastSignalID = "";
datetime lastWrite  = 0;

int OnInit()
{
   EventSetMillisecondTimer(CheckEveryMS);
   WriteStatus("initialized");
   Print("PythonSignalExecutor v2 initialized | Magic: ", MagicNumber);
   Print("Reading signals from: ", SignalFile);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteStatus("stopped");
}

void OnTimer()
{
   if(!EnableTrading) return;
   ReadAndExecuteSignal();
   WriteStatus("running");
}

void ReadAndExecuteSignal()
{
   int handle = FileOpen(SignalFile, FILE_READ|FILE_TXT|FILE_ANSI);
   if(handle == INVALID_HANDLE) return;

   string content = "";
   while(!FileIsEnding(handle))
      content += FileReadString(handle);
   FileClose(handle);

   if(content == "") return;

   // Parse fields
   string sig_id  = ExtractStr(content, "id");
   string action  = ExtractStr(content, "action");
   string symbol  = ExtractStr(content, "symbol");
   double lot     = ExtractDbl(content, "lot");
   double sl      = ExtractDbl(content, "sl");
   double tp      = ExtractDbl(content, "tp");

   // Skip if already processed
   if(sig_id == lastSignalID || sig_id == "") return;
   lastSignalID = sig_id;

   if(lot <= 0)  lot = DefaultLot;
   if(lot > MaxLot) lot = MaxLot;

   Print("Signal: ", action, " ", symbol, " lot=", lot, " sl=", sl, " tp=", tp, " id=", sig_id);

   bool ok = false;
   if(action == "BUY")        ok = OpenBuy(symbol, lot, sl, tp);
   else if(action == "SELL")  ok = OpenSell(symbol, lot, sl, tp);
   else if(action == "CLOSE") ok = CloseAll(symbol);
   else if(action == "CLOSE_ALL") { ok = CloseAllPositions(); }   // EA shutdown / prop limit halt
   else if(action == "CLOSE_BUY")  ok = CloseByType(symbol, POSITION_TYPE_BUY);
   else if(action == "CLOSE_SELL") ok = CloseByType(symbol, POSITION_TYPE_SELL);

   // Write result back for Python to confirm
   WriteResult(sig_id, action, symbol, ok);
}

bool OpenBuy(string sym, double lot, double sl, double tp)
{
   double price = SymbolInfoDouble(sym, SYMBOL_ASK);
   if(price <= 0) { Print("ERR: No ASK for ", sym); return false; }

   // Normalize SL/TP to symbol digits
   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * point;

   if(sl > 0 && (price - sl) < minStop) sl = price - minStop;
   if(tp > 0 && (tp - price) < minStop) tp = price + minStop;

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action   = TRADE_ACTION_DEAL;
   req.symbol   = sym;
   req.volume   = NormalizeDouble(lot, 2);
   req.type     = ORDER_TYPE_BUY;
   req.price    = price;
   req.sl       = sl > 0 ? NormalizeDouble(sl, digits) : 0;
   req.tp       = tp > 0 ? NormalizeDouble(tp, digits) : 0;
   req.deviation = SlippagePips;
   req.magic    = MagicNumber;
   req.comment  = "PySignal_BUY";
   req.type_filling = ORDER_FILLING_IOC;

   if(!OrderSend(req, res))
   {
      Print("BUY failed: retcode=", res.retcode, " comment=", res.comment);
      return false;
   }
   Print("BUY opened: ticket=", res.order, " price=", res.price, " vol=", res.volume);
   return true;
}

bool OpenSell(string sym, double lot, double sl, double tp)
{
   double price = SymbolInfoDouble(sym, SYMBOL_BID);
   if(price <= 0) { Print("ERR: No BID for ", sym); return false; }

   int digits = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * point;

   if(sl > 0 && (sl - price) < minStop) sl = price + minStop;
   if(tp > 0 && (price - tp) < minStop) tp = price - minStop;

   MqlTradeRequest req = {};
   MqlTradeResult  res = {};
   req.action   = TRADE_ACTION_DEAL;
   req.symbol   = sym;
   req.volume   = NormalizeDouble(lot, 2);
   req.type     = ORDER_TYPE_SELL;
   req.price    = price;
   req.sl       = sl > 0 ? NormalizeDouble(sl, digits) : 0;
   req.tp       = tp > 0 ? NormalizeDouble(tp, digits) : 0;
   req.deviation = SlippagePips;
   req.magic    = MagicNumber;
   req.comment  = "PySignal_SELL";
   req.type_filling = ORDER_FILLING_IOC;

   if(!OrderSend(req, res))
   {
      Print("SELL failed: retcode=", res.retcode, " comment=", res.comment);
      return false;
   }
   Print("SELL opened: ticket=", res.order, " price=", res.price, " vol=", res.volume);
   return true;
}

bool CloseAllPositions()
{
   // Closes every open position across ALL symbols — used for EA shutdown / prop firm halt
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string sym   = PositionGetString(POSITION_SYMBOL);
      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action   = TRADE_ACTION_DEAL;
      req.position = ticket;
      req.symbol   = sym;
      req.volume   = PositionGetDouble(POSITION_VOLUME);
      req.type     = PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price    = req.type==ORDER_TYPE_SELL ? SymbolInfoDouble(sym,SYMBOL_BID) : SymbolInfoDouble(sym,SYMBOL_ASK);
      req.deviation = SlippagePips;
      req.magic    = MagicNumber;
      req.comment  = "PySignal_CLOSE_ALL";
      req.type_filling = ORDER_FILLING_IOC;
      if(OrderSend(req,res)) { Print("CloseAll: closed ticket ", ticket, " sym=", sym); any=true; }
      else Print("CloseAll: FAILED ticket ", ticket, " retcode=", res.retcode);
   }
   return any;
}

bool CloseAll(string sym)
{
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action   = TRADE_ACTION_DEAL;
      req.position = ticket;
      req.symbol   = sym;
      req.volume   = PositionGetDouble(POSITION_VOLUME);
      req.type     = PositionGetInteger(POSITION_TYPE)==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price    = req.type==ORDER_TYPE_SELL ? SymbolInfoDouble(sym,SYMBOL_BID) : SymbolInfoDouble(sym,SYMBOL_ASK);
      req.deviation = SlippagePips;
      req.magic    = MagicNumber;
      req.comment  = "PySignal_CLOSE";
      req.type_filling = ORDER_FILLING_IOC;
      if(OrderSend(req,res)) { Print("Closed ticket ", ticket); any=true; }
   }
   return any;
}

bool CloseByType(string sym, ENUM_POSITION_TYPE ptype)
{
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if(PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if(PositionGetInteger(POSITION_TYPE) != ptype) continue;
      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action   = TRADE_ACTION_DEAL;
      req.position = ticket;
      req.symbol   = sym;
      req.volume   = PositionGetDouble(POSITION_VOLUME);
      req.type     = ptype==POSITION_TYPE_BUY ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price    = req.type==ORDER_TYPE_SELL ? SymbolInfoDouble(sym,SYMBOL_BID) : SymbolInfoDouble(sym,SYMBOL_ASK);
      req.deviation = SlippagePips;
      req.magic    = MagicNumber;
      req.comment  = "PySignal_CLOSE";
      req.type_filling = ORDER_FILLING_IOC;
      if(OrderSend(req,res)) any=true;
   }
   return any;
}

void WriteStatus(string state)
{
   int h = FileOpen(StatusFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   int total_pos = 0; double total_pnl = 0;
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong t = PositionGetTicket(i);
      if(PositionGetInteger(POSITION_MAGIC)==MagicNumber) { total_pos++; total_pnl+=PositionGetDouble(POSITION_PROFIT); }
   }
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);
   string status = StringFormat(
      "{\"state\":\"%s\",\"account\":%d,\"server\":\"%s\",\"balance\":%.2f,\"equity\":%.2f,\"floating_pnl\":%.2f,\"open_positions\":%d,\"ts\":\"%s\"}",
      state, (int)AccountInfoInteger(ACCOUNT_LOGIN), AccountInfoString(ACCOUNT_SERVER),
      balance, equity, total_pnl, total_pos,
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
   );
   FileWriteString(h, status);
   FileClose(h);
}

void WriteResult(string sig_id, string action, string symbol, bool ok)
{
   int h = FileOpen("python_result.json", FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   string r = StringFormat("{\"sig_id\":\"%s\",\"action\":\"%s\",\"symbol\":\"%s\",\"success\":%s,\"ts\":\"%s\"}",
      sig_id, action, symbol, ok?"true":"false", TimeToString(TimeCurrent(),TIME_DATE|TIME_SECONDS));
   FileWriteString(h, r);
   FileClose(h);
}

string ExtractStr(string json, string key)
{
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if(pos < 0) return "";
   pos += StringLen(search);
   int end = StringFind(json, "\"", pos);
   return end > pos ? StringSubstr(json, pos, end-pos) : "";
}

double ExtractDbl(string json, string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if(pos < 0) return 0;
   pos += StringLen(search);
   int end = pos;
   while(end < StringLen(json) && (StringGetCharacter(json,end)=='-' || (StringGetCharacter(json,end)>='0' && StringGetCharacter(json,end)<='9') || StringGetCharacter(json,end)=='.')) end++;
   string val = StringSubstr(json, pos, end-pos);
   return StringToDouble(val);
}

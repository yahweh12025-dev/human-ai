//+------------------------------------------------------------------+
//| MetalEA_v2.mq5  — Single unified EA                              |
//| Merges: PythonSignalExecutor + status writer                      |
//| Attach to ONE chart (XAUUSD or XAGUSD — doesn't matter which)    |
//| Python side: python3 ~/human-ai/liveea.py                        |
//|                                                                  |
//| Protocol:                                                        |
//|   Python writes: MQL5/Files/python_signal.json                   |
//|   EA reads it every 2 seconds, executes, then writes result to   |
//|   MQL5/Files/python_result.json                                  |
//|   EA also writes MQL5/Files/mt5_status.json every 2 seconds      |
//|   so Python knows EA is alive + current balance/equity           |
//|                                                                  |
//| Supported signal actions:                                        |
//|   BUY, SELL           — open position on specified symbol        |
//|   CLOSE               — close all positions on specified symbol  |
//|   CLOSE_ALL           — close all managed positions              |
//|   CLOSE_BUY / CLOSE_SELL — close by direction on symbol         |
//|   TEST_BUY / TEST_SELL   — 0.01 lot test trade, auto-close 60s  |
//+------------------------------------------------------------------+
#property copyright "AntFarm Swarm"
#property link      "https://docs.openclaw.ai"
#property version   "2.00"
#property description "MetalEA v2 — unified signal executor + status writer"
#property strict

input double  DefaultLot     = 0.01;
input double  MaxLot         = 2.0;
input int     MagicNumber    = 20260512;
input int     SlippagePips   = 30;
input bool    EnableTrading  = true;
input string  SignalFile     = "python_signal.json";
input string  ResultFile     = "python_result.json";
input string  StatusFile     = "mt5_status.json";
input int     CheckEveryMS   = 2000;

string lastSignalID = "";
datetime testCloseAt = 0;   // auto-close test trade at this time
string testSymbol = "";

int OnInit()
{
   EventSetMillisecondTimer(CheckEveryMS);
   WriteStatus("initialized");
   Print("MetalEA v2 initialized | Magic: ", MagicNumber, " | EnableTrading: ", EnableTrading);
   Print("Reads: ", SignalFile, " | Writes: ", ResultFile, ", ", StatusFile);
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
   WriteStatus("stopped");
   Print("MetalEA v2 stopped. Reason: ", reason);
}

void OnTimer()
{
   // Auto-close test trade after 60 seconds
   if(testCloseAt > 0 && TimeCurrent() >= testCloseAt && testSymbol != "")
   {
      Print("TEST: auto-closing test trade on ", testSymbol);
      CloseAll(testSymbol);
      testCloseAt = 0; testSymbol = "";
   }

   if(EnableTrading)
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

   string sig_id = ExtractStr(content, "id");
   string action = ExtractStr(content, "action");
   string symbol = ExtractStr(content, "symbol");
   double lot    = ExtractDbl(content, "lot");
   double sl     = ExtractDbl(content, "sl");
   double tp     = ExtractDbl(content, "tp");

   if(sig_id == lastSignalID || sig_id == "") return;
   lastSignalID = sig_id;

   if(lot <= 0)   lot = DefaultLot;
   if(lot > MaxLot) lot = MaxLot;

   Print("MetalEA v2 | Signal: ", action, " ", symbol, " lot=", lot,
         " sl=", sl, " tp=", tp, " id=", sig_id);

   bool ok = false;

   if(action == "BUY")
      ok = OpenBuy(symbol, lot, sl, tp);
   else if(action == "SELL")
      ok = OpenSell(symbol, lot, sl, tp);
   else if(action == "CLOSE")
      ok = CloseAll(symbol);
   else if(action == "CLOSE_ALL")
      ok = CloseAllPositions();
   else if(action == "CLOSE_BUY")
      ok = CloseByType(symbol, POSITION_TYPE_BUY);
   else if(action == "CLOSE_SELL")
      ok = CloseByType(symbol, POSITION_TYPE_SELL);
   else if(action == "TEST_BUY")
   {
      ok = OpenBuy(symbol, 0.01, 0, 0);
      if(ok) { testSymbol = symbol; testCloseAt = TimeCurrent() + 60; }
      Print("TEST BUY placed on ", symbol, " — auto-close in 60s");
   }
   else if(action == "TEST_SELL")
   {
      ok = OpenSell(symbol, 0.01, 0, 0);
      if(ok) { testSymbol = symbol; testCloseAt = TimeCurrent() + 60; }
      Print("TEST SELL placed on ", symbol, " — auto-close in 60s");
   }

   WriteResult(sig_id, action, symbol, ok);
}

//+------------------------------------------------------------------+
//| Open BUY market order                                            |
//+------------------------------------------------------------------+
bool OpenBuy(string sym, double lot, double sl, double tp)
{
   double price = SymbolInfoDouble(sym, SYMBOL_ASK);
   if(price <= 0) { Print("ERR OpenBuy: no ASK for ", sym); return false; }

   int    digits  = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * point;

   if(sl > 0 && (price - sl) < minStop) sl = NormalizeDouble(price - minStop * 2, digits);
   if(tp > 0 && (tp - price) < minStop) tp = NormalizeDouble(price + minStop * 2, digits);

   MqlTradeRequest req = {}; MqlTradeResult res = {};
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = sym;
   req.volume       = NormalizeDouble(lot, 2);
   req.type         = ORDER_TYPE_BUY;
   req.price        = price;
   req.sl           = sl > 0 ? NormalizeDouble(sl, digits) : 0;
   req.tp           = tp > 0 ? NormalizeDouble(tp, digits) : 0;
   req.deviation    = SlippagePips;
   req.magic        = MagicNumber;
   req.comment      = "MetalEA_BUY";
   req.type_filling = ORDER_FILLING_IOC;

   if(!OrderSend(req, res))
   {
      Print("BUY FAILED: sym=", sym, " retcode=", res.retcode, " desc=", res.comment);
      return false;
   }
   Print("BUY OK: sym=", sym, " ticket=", res.order, " price=", res.price, " vol=", res.volume);
   return true;
}

//+------------------------------------------------------------------+
//| Open SELL market order                                           |
//+------------------------------------------------------------------+
bool OpenSell(string sym, double lot, double sl, double tp)
{
   double price = SymbolInfoDouble(sym, SYMBOL_BID);
   if(price <= 0) { Print("ERR OpenSell: no BID for ", sym); return false; }

   int    digits  = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   double point   = SymbolInfoDouble(sym, SYMBOL_POINT);
   double minStop = SymbolInfoInteger(sym, SYMBOL_TRADE_STOPS_LEVEL) * point;

   if(sl > 0 && (sl - price) < minStop) sl = NormalizeDouble(price + minStop * 2, digits);
   if(tp > 0 && (price - tp) < minStop) tp = NormalizeDouble(price - minStop * 2, digits);

   MqlTradeRequest req = {}; MqlTradeResult res = {};
   req.action       = TRADE_ACTION_DEAL;
   req.symbol       = sym;
   req.volume       = NormalizeDouble(lot, 2);
   req.type         = ORDER_TYPE_SELL;
   req.price        = price;
   req.sl           = sl > 0 ? NormalizeDouble(sl, digits) : 0;
   req.tp           = tp > 0 ? NormalizeDouble(tp, digits) : 0;
   req.deviation    = SlippagePips;
   req.magic        = MagicNumber;
   req.comment      = "MetalEA_SELL";
   req.type_filling = ORDER_FILLING_IOC;

   if(!OrderSend(req, res))
   {
      Print("SELL FAILED: sym=", sym, " retcode=", res.retcode, " desc=", res.comment);
      return false;
   }
   Print("SELL OK: sym=", sym, " ticket=", res.order, " price=", res.price, " vol=", res.volume);
   return true;
}

//+------------------------------------------------------------------+
//| Close all positions for a specific symbol (our magic only)       |
//+------------------------------------------------------------------+
bool CloseAll(string sym)
{
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;

      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action       = TRADE_ACTION_DEAL;
      req.position     = ticket;
      req.symbol       = sym;
      req.volume       = PositionGetDouble(POSITION_VOLUME);
      req.type         = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
                         ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price        = (req.type == ORDER_TYPE_SELL)
                         ? SymbolInfoDouble(sym, SYMBOL_BID)
                         : SymbolInfoDouble(sym, SYMBOL_ASK);
      req.deviation    = SlippagePips;
      req.magic        = MagicNumber;
      req.comment      = "MetalEA_CLOSE";
      req.type_filling = ORDER_FILLING_IOC;

      if(OrderSend(req, res)) { Print("Closed ticket=", ticket, " sym=", sym); any = true; }
      else Print("Close FAILED: ticket=", ticket, " retcode=", res.retcode);
   }
   return any;
}

//+------------------------------------------------------------------+
//| Close all our positions across ALL symbols                       |
//+------------------------------------------------------------------+
bool CloseAllPositions()
{
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      string sym = PositionGetString(POSITION_SYMBOL);

      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action       = TRADE_ACTION_DEAL;
      req.position     = ticket;
      req.symbol       = sym;
      req.volume       = PositionGetDouble(POSITION_VOLUME);
      req.type         = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY)
                         ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price        = (req.type == ORDER_TYPE_SELL)
                         ? SymbolInfoDouble(sym, SYMBOL_BID)
                         : SymbolInfoDouble(sym, SYMBOL_ASK);
      req.deviation    = SlippagePips;
      req.magic        = MagicNumber;
      req.comment      = "MetalEA_CLOSEALL";
      req.type_filling = ORDER_FILLING_IOC;

      if(OrderSend(req, res)) { Print("CloseAll: closed ticket=", ticket, " sym=", sym); any = true; }
      else Print("CloseAll FAILED: ticket=", ticket, " retcode=", res.retcode);
   }
   return any;
}

//+------------------------------------------------------------------+
//| Close positions by type (BUY or SELL) on one symbol             |
//+------------------------------------------------------------------+
bool CloseByType(string sym, ENUM_POSITION_TYPE ptype)
{
   bool any = false;
   for(int i = PositionsTotal()-1; i >= 0; i--)
   {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) != sym) continue;
      if((int)PositionGetInteger(POSITION_MAGIC) != MagicNumber) continue;
      if((ENUM_POSITION_TYPE)PositionGetInteger(POSITION_TYPE) != ptype) continue;

      MqlTradeRequest req = {}; MqlTradeResult res = {};
      req.action       = TRADE_ACTION_DEAL;
      req.position     = ticket;
      req.symbol       = sym;
      req.volume       = PositionGetDouble(POSITION_VOLUME);
      req.type         = (ptype == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
      req.price        = (req.type == ORDER_TYPE_SELL)
                         ? SymbolInfoDouble(sym, SYMBOL_BID)
                         : SymbolInfoDouble(sym, SYMBOL_ASK);
      req.deviation    = SlippagePips;
      req.magic        = MagicNumber;
      req.comment      = "MetalEA_CLOSE";
      req.type_filling = ORDER_FILLING_IOC;

      if(OrderSend(req, res)) any = true;
   }
   return any;
}

//+------------------------------------------------------------------+
//| Write status JSON for Python to read                             |
//+------------------------------------------------------------------+
void WriteStatus(string state)
{
   int total_pos = 0; double total_pnl = 0;
   string pos_detail = "";
   for(int i = 0; i < PositionsTotal(); i++)
   {
      ulong t = PositionGetTicket(i);
      if((int)PositionGetInteger(POSITION_MAGIC) == MagicNumber)
      {
         total_pos++;
         total_pnl += PositionGetDouble(POSITION_PROFIT);
         string sym = PositionGetString(POSITION_SYMBOL);
         string typ = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
         double prc = PositionGetDouble(POSITION_PRICE_OPEN);
         double vol = PositionGetDouble(POSITION_VOLUME);
         pos_detail += sym + ":" + typ + "@" + DoubleToString(prc, 2) + "x" + DoubleToString(vol, 2) + ";";
      }
   }

   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double equity  = AccountInfoDouble(ACCOUNT_EQUITY);

   // Also include bid prices for both metals so Python can get live price
   double xau_bid = SymbolInfoDouble("XAUUSD", SYMBOL_BID);
   double xag_bid = SymbolInfoDouble("XAGUSD", SYMBOL_BID);
   double xau_ask = SymbolInfoDouble("XAUUSD", SYMBOL_ASK);
   double xag_ask = SymbolInfoDouble("XAGUSD", SYMBOL_ASK);

   string status = StringFormat(
      "{\"state\":\"%s\",\"account\":%d,\"server\":\"%s\","
      "\"balance\":%.2f,\"equity\":%.2f,\"floating_pnl\":%.2f,"
      "\"open_positions\":%d,\"pos_detail\":\"%s\","
      "\"xauusd_bid\":%.2f,\"xauusd_ask\":%.2f,"
      "\"xagusd_bid\":%.3f,\"xagusd_ask\":%.3f,"
      "\"ts\":\"%s\"}",
      state,
      (int)AccountInfoInteger(ACCOUNT_LOGIN),
      AccountInfoString(ACCOUNT_SERVER),
      balance, equity, total_pnl,
      total_pos, pos_detail,
      xau_bid, xau_ask,
      xag_bid, xag_ask,
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS)
   );

   int h = FileOpen(StatusFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   FileWriteString(h, status);
   FileClose(h);
}

//+------------------------------------------------------------------+
//| Write result JSON back to Python                                 |
//+------------------------------------------------------------------+
void WriteResult(string sig_id, string action, string symbol, bool ok)
{
   int h = FileOpen(ResultFile, FILE_WRITE|FILE_TXT|FILE_ANSI);
   if(h == INVALID_HANDLE) return;
   string r = StringFormat(
      "{\"sig_id\":\"%s\",\"action\":\"%s\",\"symbol\":\"%s\",\"success\":%s,\"ts\":\"%s\"}",
      sig_id, action, symbol, ok ? "true" : "false",
      TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
   FileWriteString(h, r);
   FileClose(h);
}

//+------------------------------------------------------------------+
//| JSON helpers — extract string or double from flat JSON           |
//+------------------------------------------------------------------+
string ExtractStr(string json, string key)
{
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if(pos < 0) return "";
   pos += StringLen(search);
   int end = StringFind(json, "\"", pos);
   return end > pos ? StringSubstr(json, pos, end - pos) : "";
}

double ExtractDbl(string json, string key)
{
   string search = "\"" + key + "\":";
   int pos = StringFind(json, search);
   if(pos < 0) return 0;
   pos += StringLen(search);
   int end = pos;
   while(end < StringLen(json))
   {
      ushort c = StringGetCharacter(json, end);
      if(c == '-' || (c >= '0' && c <= '9') || c == '.') end++;
      else break;
   }
   return StringToDouble(StringSubstr(json, pos, end - pos));
}
//+------------------------------------------------------------------+

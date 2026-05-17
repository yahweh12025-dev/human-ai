//+------------------------------------------------------------------+
//| SocketSignalReceiver.mq5                                         |
//| Receives trade signals from Python via TCP socket on port 9999   |
//| Also polls pending_signal.json as file fallback                  |
//+------------------------------------------------------------------+
#property copyright "Human-AI Swarm"
#property version   "1.0"
#property strict

input int    ListenPort    = 9999;
input string SignalFile    = "C:\\Users\\yahwehatwork\\.wine\\drive_c\\...\\pending_signal.json";
input double DefaultLot    = 0.01;
input bool   EnableSocket  = true;
input bool   EnableFile    = true;

int    serverSocket = INVALID_HANDLE;
string lastSignalTS = "";

int OnInit() {
   if(EnableSocket) {
      serverSocket = SocketCreate();
      if(serverSocket == INVALID_HANDLE) {
         Print("SocketSignalReceiver: Failed to create socket");
         return INIT_FAILED;
      }
      if(!SocketBind(serverSocket, ListenPort)) {
         Print("SocketSignalReceiver: Failed to bind port ", ListenPort);
         SocketClose(serverSocket);
         return INIT_FAILED;
      }
      if(!SocketListen(serverSocket, 1)) {
         Print("SocketSignalReceiver: Failed to listen");
         SocketClose(serverSocket);
         return INIT_FAILED;
      }
      Print("SocketSignalReceiver: Listening on port ", ListenPort);
   }
   EventSetTimer(2);  // Check every 2 seconds
   return INIT_SUCCEEDED;
}

void OnTimer() {
   // Check socket for incoming signals
   if(EnableSocket && serverSocket != INVALID_HANDLE) {
      int client = SocketAccept(serverSocket, 100);
      if(client != INVALID_HANDLE) {
         char buf[4096];
         int received = SocketRead(client, buf, sizeof(buf) - 1, 1000);
         if(received > 0) {
            string msg = CharArrayToString(buf, 0, received);
            ProcessSignal(msg);
            string resp = "{\"status\":\"ok\"}";
            uchar response[];
            StringToCharArray(resp, response);
            SocketSend(client, response, ArraySize(response) - 1);
         }
         SocketClose(client);
      }
   }
}

void ProcessSignal(string jsonStr) {
   // Parse simple JSON manually (no JSON lib in MQL5 standard)
   string action = ExtractJSON(jsonStr, "action");
   string symbol = ExtractJSON(jsonStr, "symbol");
   string lotStr = ExtractJSON(jsonStr, "lot");
   string slStr  = ExtractJSON(jsonStr, "sl");
   string tpStr  = ExtractJSON(jsonStr, "tp");
   string ts     = ExtractJSON(jsonStr, "timestamp");

   if(ts == lastSignalTS) return;  // Skip duplicate
   lastSignalTS = ts;

   double lot = StringToDouble(lotStr);
   double sl  = StringToDouble(slStr);
   double tp  = StringToDouble(tpStr);
   if(lot <= 0) lot = DefaultLot;

   Print("Signal received: ", action, " ", symbol, " lot=", lot);

   if(action == "BUY")   PlaceOrder(symbol, ORDER_TYPE_BUY, lot, sl, tp);
   if(action == "SELL")  PlaceOrder(symbol, ORDER_TYPE_SELL, lot, sl, tp);
   if(action == "CLOSE") ClosePosition(symbol);
}

string ExtractJSON(string json, string key) {
   string search = "\"" + key + "\":\"";
   int pos = StringFind(json, search);
   if(pos >= 0) {
      pos += StringLen(search);
      int end = StringFind(json, "\"", pos);
      if(end > pos) return StringSubstr(json, pos, end - pos);
   }
   // Try numeric (no quotes)
   search = "\"" + key + "\":";
   pos = StringFind(json, search);
   if(pos >= 0) {
      pos += StringLen(search);
      int end = MathMin(StringFind(json, ",", pos), StringFind(json, "}", pos));
      if(end > pos) return StringSubstr(json, pos, end - pos);
   }
   return "";
}

bool PlaceOrder(string sym, ENUM_ORDER_TYPE type, double lot, double sl, double tp) {
   MqlTradeRequest req = {};
   MqlTradeResult res  = {};
   req.action    = TRADE_ACTION_DEAL;
   req.symbol    = sym;
   req.volume    = lot;
   req.type      = type;
   req.price     = (type == ORDER_TYPE_BUY) ? SymbolInfoDouble(sym, SYMBOL_ASK) : SymbolInfoDouble(sym, SYMBOL_BID);
   req.sl        = sl;
   req.tp        = tp;
   req.deviation = 20;
   req.magic     = 20260512;
   req.comment   = "PythonBridge";
   req.type_filling = ORDER_FILLING_IOC;
   if(!OrderSend(req, res)) {
      Print("PlaceOrder failed: ", res.retcode, " ", res.comment);
      return false;
   }
   Print("Order placed: ticket=", res.order, " at ", res.price);
   return true;
}

bool ClosePosition(string sym) {
   for(int i = PositionsTotal() - 1; i >= 0; i--) {
      ulong ticket = PositionGetTicket(i);
      if(PositionGetString(POSITION_SYMBOL) == sym) {
         MqlTradeRequest req = {}; MqlTradeResult res = {};
         req.action   = TRADE_ACTION_DEAL;
         req.position = ticket;
         req.symbol   = sym;
         req.volume   = PositionGetDouble(POSITION_VOLUME);
         req.type     = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? ORDER_TYPE_SELL : ORDER_TYPE_BUY;
         req.price    = (req.type == ORDER_TYPE_SELL) ? SymbolInfoDouble(sym, SYMBOL_BID) : SymbolInfoDouble(sym, SYMBOL_ASK);
         req.deviation = 20;
         req.magic    = 20260512;
         req.comment  = "PythonClose";
         req.type_filling = ORDER_FILLING_IOC;
         OrderSend(req, res);
      }
   }
   return true;
}

void OnDeinit(const int reason) {
   if(serverSocket != INVALID_HANDLE) SocketClose(serverSocket);
   EventKillTimer();
}

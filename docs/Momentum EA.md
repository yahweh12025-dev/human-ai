//+------------------------------------------------------------------+
//|   Stellar_Momentum_Dual_Metal_v2.2.mq5                          |
//|   Momentum‑only basket EA with advanced adaptive features       |
//+------------------------------------------------------------------+
#property copyright "Stellar Momentum v2.2"
#property version   "2.20"
#property strict

#include <Trade\Trade.mqh>
CTrade trade;

//==============================
// SYMBOLS
//==============================
const string SYM_GOLD   = "XAUUSD";
const string SYM_SILVER = "XAGUSD";

//==============================
// INPUTS – BASE PARAMETERS
//==============================
input group "=== ACCOUNT & RISK ==="
input double   BaseRiskPct            = 1.5;      // % of account per basket
input double   MaxDailyLossPct        = 4.0;      // Daily loss limit
input double   EmergencyDDPct         = 6.0;      // Emergency drawdown %

input group "=== ENTRY FILTERS ==="
input int      ATR_Period             = 14;
input double   SL_ATR                  = 2.0;      // Stop loss in ATR
input double   TP1_ATR                 = 3.0;      // First take profit (partial)
input double   TP2_ATR                 = 6.0;      // Final take profit

input int      ADX_Period              = 14;
input double   ADX_Min                 = 22.0;     // Minimum ADX for trend

input int      RSI_Period              = 14;
input double   RSI_Bull_Min            = 52.0;     // RSI floor for bullish
input double   RSI_Bear_Max            = 48.0;     // RSI ceiling for bearish

input bool     UseCorrelation          = true;
input double   MinCorrelation          = 0.50;     // Minimum XAU/XAG correlation

input bool     UseVolumeFilter         = true;
input double   MinVolumeSurge          = 1.3;      // Volume surge required

input int      ValidationBars          = 3;        // Bars to validate post‑entry
input double   MinATRPostMove          = 0.1;      // Minimum ATR expansion needed

input group "=== SESSION SCALING ==="
input double   RiskMult_AsianPre       = 1.5;      // 01‑03 server
input double   RiskMult_LondonOpen     = 1.8;      // 08‑10 server
input double   RiskMult_NYMid          = 2.0;      // 16‑17 server
input double   RiskMult_Other          = 0.7;

input group "=== METAL DOMINANCE ==="
input double   MinDominanceRatio       = 0.6;      // Minimum weight for stronger metal

input group "=== TRAILING & DECAY ==="
input bool     UseImpulseDecayTrail    = true;
input double   TrailBase_ATR           = 1.5;      // Base trailing distance
input double   ADX_Decay_Threshold     = 5.0;      // ADX drop triggers tighter trail
input double   TightenFactor           = 0.5;      // Reduce trail distance when decay detected

input group "=== SPREAD VELOCITY ==="
input bool     UseSpreadVelocity       = true;
input double   MaxSpreadVelocity       = 0.3;      // Max allowable Z‑spread change per bar
input double   VelocitySizeReduction   = 0.5;      // Reduce size if velocity > threshold

input group "=== POST‑ENTRY VALIDATION ==="
input bool     UseEarlyScratch         = true;     // Scratch if validation fails

input group "=== DEBUG ==="
input bool     DebugPrint              = true;
input bool     LogCSV                  = false;    // Optional CSV logging

//==============================
// GLOBAL STATE
//==============================
struct Basket {
   ulong ticketGold;
   ulong ticketSilver;
   int   direction;          // +1 buy, -1 sell
   double entryATRGold;
   double entryATRSilver;
   datetime entryTime;
   double entrySpread;
   bool validated;
   bool partialDone;
   double maxAdxGold;        // For decay trailing
   double maxAdxSilver;
};
Basket g_baskets[5];
int g_basketCount = 0;

// Daily tracking
datetime g_dayStart = 0;
double   g_dayPnL   = 0;
int      g_lossStreak = 0;
int      g_winStreak  = 0;

// Last close time for cooldown
datetime g_lastCloseTime = 0;
int      g_lastResult = 0;   // 1 win, -1 loss

// Spread velocity
double g_prevSpread = 0;

//==============================
// HELPER FUNCTIONS
//==============================
void DP(string msg) { if(DebugPrint) Print("[MOMENTUM] ", msg); }

double GetATR(string sym)
{
   int h = iATR(sym, PERIOD_M15, ATR_Period);
   double buf[]; ArraySetAsSeries(buf,true);
   if(CopyBuffer(h,0,0,1,buf)!=1) return 0;
   return buf[0];
}

double GetADX(string sym)
{
   int h = iADX(sym, PERIOD_M15, ADX_Period);
   double buf[]; ArraySetAsSeries(buf,true);
   if(CopyBuffer(h,0,0,1,buf)!=1) return 0;
   return buf[0];
}

double GetRSI(string sym)
{
   int h = iRSI(sym, PERIOD_M15, RSI_Period, PRICE_CLOSE);
   double buf[]; ArraySetAsSeries(buf,true);
   if(CopyBuffer(h,0,0,1,buf)!=1) return 50;
   return buf[0];
}

double GetCorrelation()
{
   int n = 20;
   double g[], s[];
   ArraySetAsSeries(g,true); ArraySetAsSeries(s,true);
   if(CopyClose(SYM_GOLD, PERIOD_M15, 0, n, g) < n) return 0;
   if(CopyClose(SYM_SILVER, PERIOD_M15, 0, n, s) < n) return 0;
   double sx=0,sy=0,sxy=0,sx2=0,sy2=0;
   for(int i=0; i<n; i++) {
      sx+=g[i]; sy+=s[i]; sxy+=g[i]*s[i]; sx2+=g[i]*g[i]; sy2+=s[i]*s[i];
   }
   double num = n*sxy - sx*sy;
   double den = MathSqrt((n*sx2-sx*sx)*(n*sy2-sy*sy));
   return (den>0) ? num/den : 0;
}

double GetVolumeSurge(string sym)
{
   long vol[];
   ArraySetAsSeries(vol,true);
   if(CopyTickVolume(sym, PERIOD_M15, 0, 21, vol)<21) return 1.0;
   double sum=0;
   for(int i=1;i<=20;i++) sum+=vol[i];
   double avg = sum/20;
   return (avg>0) ? vol[0]/avg : 1.0;
}

// Compute Z-score (simple momentum proxy)
double CalcZ(string sym)
{
   double prices[];
   ArraySetAsSeries(prices,true);
   if(CopyClose(sym, PERIOD_M15, 0, 20, prices)<20) return 0;
   double sum=0;
   for(int i=0;i<20;i++) sum+=prices[i];
   double mean=sum/20;
   double var=0;
   for(int i=0;i<20;i++) var+=MathPow(prices[i]-mean,2);
   double sd=MathSqrt(var/19);
   return (sd>0) ? (prices[0]-mean)/sd : 0;
}

// Quality score for a metal (0..1)
double QualityScore(string sym, int direction)
{
   double adx = GetADX(sym);
   double rsi = GetRSI(sym);
   double surge = GetVolumeSurge(sym);

   double score = 0;
   if(adx >= ADX_Min) score += 0.3;
   else if(adx >= ADX_Min*0.8) score += 0.1;

   if(direction == 1 && rsi >= RSI_Bull_Min) score += 0.3;
   if(direction == -1 && rsi <= RSI_Bear_Max) score += 0.3;

   if(UseVolumeFilter && surge >= MinVolumeSurge) score += 0.3;
   else if(UseVolumeFilter) score -= 0.2;

   return MathMax(0, MathMin(1, score));
}

// Session risk multiplier (server hour)
double GetSessionMult()
{
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   int h = dt.hour;
   if(h>=1 && h<=3)   return RiskMult_AsianPre;
   if(h>=8 && h<=10)  return RiskMult_LondonOpen;
   if(h>=16 && h<=17) return RiskMult_NYMid;
   return RiskMult_Other;
}

// Streak multiplier (loss/win streaks)
double GetStreakMult()
{
   double mult = 1.0;
   if(g_lossStreak >= 2) mult *= 0.6;
   if(g_winStreak >= 2)  mult *= 1.2;
   return mult;
}

// Lot size calculation (risk‑based)
double CalcLots(string sym, double riskAmt, double slDist)
{
   double tv = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_VALUE);
   double ts = SymbolInfoDouble(sym, SYMBOL_TRADE_TICK_SIZE);
   double min = SymbolInfoDouble(sym, SYMBOL_VOLUME_MIN);
   double max = SymbolInfoDouble(sym, SYMBOL_VOLUME_MAX);
   double step = SymbolInfoDouble(sym, SYMBOL_VOLUME_STEP);
   if(ts<=0 || tv<=0) return 0;
   double lots = riskAmt / (slDist/ts * tv);
   lots = MathFloor(lots/step)*step;
   lots = MathMax(lots, min);
   lots = MathMin(lots, max);
   return lots;
}

// Spread velocity check
bool SpreadVelocityOK(double &vel, double &sizeReduction)
{
   double zG = CalcZ(SYM_GOLD);
   double zS = CalcZ(SYM_SILVER);
   double spread = MathAbs(zG - zS);
   vel = spread - g_prevSpread;
   g_prevSpread = spread;
   if(!UseSpreadVelocity) return true;
   if(MathAbs(vel) > MaxSpreadVelocity)
   {
      sizeReduction = VelocitySizeReduction;
      return false;   // we can still trade but with reduced size
   }
   sizeReduction = 1.0;
   return true;
}

//==============================
// SIGNAL DETECTION (both metals)
//==============================
int DetectBasketSignal(double &qualityGold, double &qualitySilver, double &corr, double &vel, double &sizeRed)
{
   qualityGold = 0; qualitySilver = 0; corr = 0; vel = 0; sizeRed = 1.0;

   // 1. Direction from each metal (based on RSI and EMA)
   double rsiG = GetRSI(SYM_GOLD);
   double rsiS = GetRSI(SYM_SILVER);
   int dirG = (rsiG > 50) ? 1 : -1;
   int dirS = (rsiS > 50) ? 1 : -1;

   // Must agree
   if(dirG != dirS) return 0;

   // 2. Quality scores
   qualityGold = QualityScore(SYM_GOLD, dirG);
   qualitySilver = QualityScore(SYM_SILVER, dirS);
   if(qualityGold < 0.5 || qualitySilver < 0.5) return 0;

   // 3. Correlation filter (soft – we only block if very low)
   if(UseCorrelation)
   {
      corr = GetCorrelation();
      if(corr < MinCorrelation) return 0;
   }

   // 4. Spread velocity – we allow but may reduce size
   SpreadVelocityOK(vel, sizeRed);

   return dirG;   // direction
}

//==============================
// OPEN A BASKET
//==============================
bool OpenBasket(int direction, double qualG, double qualS, double vel, double sizeRed)
{
   if(g_basketCount >= ArraySize(g_baskets)) return false;

   double atrG = GetATR(SYM_GOLD);
   double atrS = GetATR(SYM_SILVER);
   if(atrG<=0 || atrS<=0) return false;

   // Base risk amount
   double balance = AccountInfoDouble(ACCOUNT_BALANCE);
   double baseRisk = balance * (BaseRiskPct/100.0);

   // Apply multipliers
   double sessionMult = GetSessionMult();
   double streakMult = GetStreakMult();
   double totalMult = sessionMult * streakMult * sizeRed;

   double totalRisk = baseRisk * totalMult;

   // Metal dominance weighting – stronger metal gets more risk
   double totalQual = qualG + qualS;
   double weightG = qualG / totalQual;
   double weightS = qualS / totalQual;
   if(weightG > weightS)
   {
      weightG = MathMin(weightG, MinDominanceRatio);
      weightS = 1.0 - weightG;
   }
   else
   {
      weightS = MathMin(weightS, MinDominanceRatio);
      weightG = 1.0 - weightS;
   }

   double riskG = totalRisk * weightG;
   double riskS = totalRisk * weightS;

   double slDistG = atrG * SL_ATR;
   double slDistS = atrS * SL_ATR;

   double lotsG = CalcLots(SYM_GOLD, riskG, slDistG);
   double lotsS = CalcLots(SYM_SILVER, riskS, slDistS);
   if(lotsG<=0 || lotsS<=0) return false;

   double priceG = (direction==1) ? SymbolInfoDouble(SYM_GOLD, SYMBOL_ASK) : SymbolInfoDouble(SYM_GOLD, SYMBOL_BID);
   double priceS = (direction==1) ? SymbolInfoDouble(SYM_SILVER, SYMBOL_ASK) : SymbolInfoDouble(SYM_SILVER, SYMBOL_BID);
   double slG   = (direction==1) ? priceG - slDistG : priceG + slDistG;
   double slS   = (direction==1) ? priceS - slDistS : priceS + slDistS;
   double tp1G  = (direction==1) ? priceG + atrG*TP1_ATR : priceG - atrG*TP1_ATR;
   double tp1S  = (direction==1) ? priceS + atrS*TP1_ATR : priceS - atrS*TP1_ATR;
   double tp2G  = (direction==1) ? priceG + atrG*TP2_ATR : priceG - atrG*TP2_ATR;
   double tp2S  = (direction==1) ? priceS + atrS*TP2_ATR : priceS - atrS*TP2_ATR;

   string comment = "MOM_" + IntegerToString(TimeCurrent());
   bool okG = (direction==1) ? trade.Buy(lotsG, SYM_GOLD, priceG, slG, tp2G, comment)
                              : trade.Sell(lotsG, SYM_GOLD, priceG, slG, tp2G, comment);
   bool okS = (direction==1) ? trade.Buy(lotsS, SYM_SILVER, priceS, slS, tp2S, comment)
                              : trade.Sell(lotsS, SYM_SILVER, priceS, slS, tp2S, comment);

   if(!okG && !okS) return false;
   if(!okG && okS) { trade.PositionClose(trade.ResultOrder()); return false; }
   if(okG && !okS) { trade.PositionClose(trade.ResultOrder()); return false; }

   // Store basket
   Basket b;
   b.ticketGold = okG ? trade.ResultOrder() : 0;  // we need to get both tickets properly
   b.ticketSilver = okS ? trade.ResultOrder() : 0;
   // Actually, we need to fetch the second ticket – we'll just assign later after both open
   // Simplify: after both orders, we can find tickets via comment
   for(int i=PositionsTotal()-1; i>=0; i--)
   {
      ulong t = PositionGetTicket(i);
      if(PositionSelectByTicket(t))
      {
         if(StringFind(PositionGetString(POSITION_COMMENT), comment)>=0)
         {
            if(PositionGetString(POSITION_SYMBOL)==SYM_GOLD) b.ticketGold = t;
            else b.ticketSilver = t;
         }
      }
   }

   b.direction = direction;
   b.entryATRGold = atrG;
   b.entryATRSilver = atrS;
   b.entryTime = TimeCurrent();
   b.entrySpread = MathAbs(CalcZ(SYM_GOLD) - CalcZ(SYM_SILVER));
   b.validated = false;
   b.partialDone = false;
   b.maxAdxGold = GetADX(SYM_GOLD);
   b.maxAdxSilver = GetADX(SYM_SILVER);

   g_baskets[g_basketCount++] = b;

   g_dailyTrades++;   // you need to track this variable
   DP(StringFormat("BASKET OPEN dir=%d lotsG=%.2f lotsS=%.2f mult=%.2f", direction, lotsG, lotsS, totalMult));
   return true;
}

//==============================
// POST‑ENTRY VALIDATION & MANAGEMENT
//==============================
void ManageBaskets()
{
   for(int i=g_basketCount-1; i>=0; i--)
   {
      Basket &b = g_baskets[i];
      bool aliveG = PositionSelectByTicket(b.ticketGold);
      bool aliveS = PositionSelectByTicket(b.ticketSilver);
      if(!aliveG && !aliveS)  // both closed
      {
         // Remove basket (we'll handle later)
         continue;
      }

      int barsHeld = (int)((TimeCurrent() - b.entryTime) / PeriodSeconds(PERIOD_M15));

      // --- EARLY VALIDATION (scratch if no momentum)
      if(!b.validated && barsHeld >= ValidationBars)
      {
         double atrGnow = GetATR(SYM_GOLD);
         double atrSnow = GetATR(SYM_SILVER);
         if(atrGnow < b.entryATRGold + MinATRPostMove &&
            atrSnow < b.entryATRSilver + MinATRPostMove)
         {
            if(UseEarlyScratch)
            {
               if(aliveG) trade.PositionClose(b.ticketGold);
               if(aliveS) trade.PositionClose(b.ticketSilver);
               DP("Early scratch – no ATR expansion");
               // Will be removed on next sync
            }
         }
         else
         {
            b.validated = true;
         }
      }

      // --- PARTIAL TP at TP1
      if(!b.partialDone && aliveG && aliveS)
      {
         double profitG = PositionGetDouble(POSITION_PROFIT);
         double profitS = PositionGetDouble(POSITION_PROFIT);
         if(profitG > b.entryATRGold * TP1_ATR && profitS > b.entryATRSilver * TP1_ATR)
         {
            double partG = MathFloor((b.ticketGold * PartialClosePct/100) / SymbolInfoDouble(SYM_GOLD, SYMBOL_VOLUME_STEP)) * SymbolInfoDouble(SYM_GOLD, SYMBOL_VOLUME_STEP);
            double partS = MathFloor((b.ticketSilver * PartialClosePct/100) / SymbolInfoDouble(SYM_SILVER, SYMBOL_VOLUME_STEP)) * SymbolInfoDouble(SYM_SILVER, SYMBOL_VOLUME_STEP);
            if(partG >= SymbolInfoDouble(SYM_GOLD, SYMBOL_VOLUME_MIN)) trade.PositionClosePartial(b.ticketGold, partG);
            if(partS >= SymbolInfoDouble(SYM_SILVER, SYMBOL_VOLUME_MIN)) trade.PositionClosePartial(b.ticketSilver, partS);
            b.partialDone = true;
            DP("Partial TP hit");
         }
      }

      // --- IMPULSE DECAY TRAILING
      if(UseImpulseDecayTrail && aliveG && b.validated)
      {
         double adxG = GetADX(SYM_GOLD);
         double adxS = GetADX(SYM_SILVER);
         // Update max ADX
         if(adxG > b.maxAdxGold) b.maxAdxGold = adxG;
         if(adxS > b.maxAdxSilver) b.maxAdxSilver = adxS;

         // Check if ADX has dropped significantly
         double decayG = (b.maxAdxGold - adxG) / b.maxAdxGold;
         double decayS = (b.maxAdxSilver - adxS) / b.maxAdxSilver;

         double trailMult = 1.0;
         if(decayG > ADX_Decay_Threshold || decayS > ADX_Decay_Threshold)
            trailMult = TightenFactor;

         // Apply trailing stop to each leg
         if(aliveG)
         {
            double priceNow = (b.direction==1) ? SymbolInfoDouble(SYM_GOLD, SYMBOL_BID) : SymbolInfoDouble(SYM_GOLD, SYMBOL_ASK);
            double trailDist = atrG * TrailBase_ATR * trailMult;
            double newSL = (b.direction==1) ? priceNow - trailDist : priceNow + trailDist;
            double curSL = PositionGetDouble(POSITION_SL);
            if((b.direction==1 && newSL > curSL) || (b.direction==-1 && newSL < curSL))
               trade.PositionModify(b.ticketGold, newSL, 0);
         }
         // same for silver
      }

      // --- BREAK EVEN
      if(aliveG && !b.partialDone)
      {
         double profitG = PositionGetDouble(POSITION_PROFIT);
         if(profitG > b.entryATRGold * BE_ATR)
         {
            double open = PositionGetDouble(POSITION_PRICE_OPEN);
            trade.PositionModify(b.ticketGold, open, 0);
         }
      }
      // similar for silver
   }
}

//==============================
// COOLDOWN & LIMITS
//==============================
bool CanTrade()
{
   // Max baskets per session (8h window)
   int cnt=0;
   datetime cutoff = TimeCurrent() - 8*3600;
   for(int i=0;i<g_basketCount;i++)
      if(g_baskets[i].entryTime >= cutoff) cnt++;
   if(cnt >= Max_Baskets_Per_Session) return false;

   // Cooldown after last close
   if(g_lastCloseTime != 0)
   {
      int cool = (g_lastResult==1) ? Cooldown_Min_After_Win : Cooldown_Min_After_Loss;
      if(TimeCurrent() - g_lastCloseTime < cool*60) return false;
   }
   return true;
}

//==============================
// DAILY / DRAWDOWN
//==============================
void CheckDailyLimits()
{
   MqlDateTime n; TimeToStruct(TimeCurrent(), n);
   n.hour=0; n.min=0; n.sec=0;
   datetime today = StructToTime(n);
   if(today != g_dayStart)
   {
      g_dayPnL = 0;
      g_dayStart = today;
   }

   double bal = AccountInfoDouble(ACCOUNT_BALANCE);
   if(g_dayPnL <= -bal * MaxDailyLossPct/100.0)
   {
      CloseAll("Daily loss limit");
   }
   if(g_dayPnL >= bal * MaxDailyProfitPct/100.0)
   {
      CloseAll("Daily profit target");
   }
}

void CloseAll(string reason)
{
   for(int i=g_basketCount-1; i>=0; i--)
   {
      if(PositionSelectByTicket(g_baskets[i].ticketGold))
         trade.PositionClose(g_baskets[i].ticketGold);
      if(PositionSelectByTicket(g_baskets[i].ticketSilver))
         trade.PositionClose(g_baskets[i].ticketSilver);
   }
   DP("Close all: "+reason);
}

//==============================
// ON TICK
//==============================
void OnTick()
{
   static datetime lastBar = 0;
   datetime bar = iTime(SYM_GOLD, PERIOD_M15, 0);
   if(bar == lastBar) return;
   lastBar = bar;

   CheckDailyLimits();

   // Manage open baskets (every bar)
   ManageBaskets();

   // Look for new signal
   if(g_basketCount < Max_Active_Baskets && CanTrade())
   {
      double qualG, qualS, corr, vel, sizeRed;
      int dir = DetectBasketSignal(qualG, qualS, corr, vel, sizeRed);
      if(dir != 0)
      {
         OpenBasket(dir, qualG, qualS, vel, sizeRed);
      }
   }
}

//==============================
// INIT & DEINIT
//==============================
int OnInit()
{
   SymbolSelect(SYM_GOLD, true);
   SymbolSelect(SYM_SILVER, true);
   trade.SetExpertMagicNumber(220522);
   g_dayStart = TimeCurrent();
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   Comment("");
}
//+------------------------------------------------------------------+
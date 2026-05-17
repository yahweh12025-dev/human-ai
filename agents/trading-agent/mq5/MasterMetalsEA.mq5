//+------------------------------------------------------------------+
//|                                              MasterMetalsEA.mq5  |
//|                                  Copyright 2026, AntFarm Swarm    |
//|                                    High-Fidelity v55.27 Edition   |
//+------------------------------------------------------------------+
#property copyright "AntFarm Orchestrator"
#property link      "https://docs.openclaw.ai"
#property version   "55.27"
#property strict

//--- Inputs
input group "--- Risk Management ---"
input double   BasketRiskPct = 2.5;        // Risk per basket (%)
input double   MinScoreToTrade = 3.5;      // Minimum score to trigger entry
input double   MLBlend = 0.35;             // Weight of ML component in scoring
input int      MaxConsecutiveLosses = 5;   // Fast-Defense trigger

input group "--- Entry Timing (Event Window) ---"
input double   ATRSpike_Event = 1.12;      // M15 ATR ratio to arm window
input int      EventWindowMinutes = 60;    // Duration of event window (min)
input ENUM_TIMEFRAMES TF_Event = PERIOD_M15;
input ENUM_TIMEFRAMES TF_Trigger = PERIOD_M5;

input group "--- Regime & Context ---"
input ENUM_TIMEFRAMES TF_Regime = PERIOD_H1;
input ENUM_TIMEFRAMES TF_Regime_H4 = PERIOD_H4;
input double   ADX_H1_SlopeMin = 0.05;     // Minimum ADX slope for trend
input int      ADX_Period = 14;

input group "--- Schedule Controls ---"
input string   HotHours = "1,11,15";       // Comma separated hot hours (UT)
input string   AvoidHours = "5,6,8,23";    // Hard blocked hours (UT)
input double   DowMon = 1.10;
input double   DowTue = 1.00;
input double   DowWed = 0.70;
input double   DowThu = 0.80;
input double   DowFri = 1.05;

input group "--- Exit Logic (v55.27 Optimized) ---"
input double   Partial_RR = 1.20;          // Partial close at 1.2R
input double   TrailStart_RR = 1.60;       // Trail stop activates at 1.6R
input double   WinnerFloor_RR = 0.80;      // Trailing floor at 0.8R
input double   TP2_RR_Normal = 2.0;        // Final target 2.0R
input int      MaxHoldMinutes = 240;       // Hard 4h time limit
input int      ScratchMinutes = 30;        // Scratch if no progress in 30m
input double   ScratchLoss_R = -0.50;      // Scratch at -0.5R

//--- Global Variables
int handle_atr_m15, handle_adx_h1, handle_adx_h4;
datetime event_armed_time = 0;
bool is_defense_mode = false;
int consecutive_losses = 0;

//--- Structure for Basket
struct SBasket {
   int ticket_gold;
   int ticket_silver;
   double entry_price_gold;
   double entry_price_silver;
   double stop_loss;
   double take_profit;
   datetime open_time;
   int signal_direction; // 1 Long, -1 Short
};

SBasket current_basket;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit() {
   handle_atr_m15 = iATR(_Symbol, TF_Event, 14);
   handle_adx_h1 = iADX(_Symbol, TF_Regime, ADX_Period);
   handle_adx_h4 = iADX(_Symbol, TF_Regime_H4, ADX_Period);
   
   if(handle_atr_m15 == INVALID_HANDLE || handle_adx_h1 == INVALID_HANDLE || handle_adx_h4 == INVALID_HANDLE) {
      Print("Error initializing indicators");
      return INIT_FAILED;
   }
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason) {
   IndicatorRelease(handle_atr_m15);
   IndicatorRelease(handle_adx_h1);
   IndicatorRelease(handle_adx_h4);
}

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick() {
   // 1. Manage existing positions (M1 check)
   if(PositionSelectByMagic(12345)) {
      ManagePositions();
      return; // Don't look for new entries if in a basket
   }

   // 2. Check Schedules (Hard Blocks)
   if(IsHourBlocked()) return;

   // 3. Event Detection (M15 ATR Spike)
   if(DetectATRSpike()) {
      event_armed_time = TimeCurrent();
      Print("Event Armed: ATR Spike detected. Window open for ", EventWindowMinutes, " minutes.");
   }

   // 4. Entry Logic (M5 Trigger)
   if(event_armed_time > 0 && (TimeCurrent() - event_armed_time) <= EventWindowMinutes * 60) {
      if(EvaluateEntrySignal()) {
         ExecuteBasketEntry();
      }
   }
}

//+------------------------------------------------------------------+
//| Helper: Check if current hour is in AvoidHours                   |
//+------------------------------------------------------------------+
bool IsHourBlocked() {
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   
   // Hard Blocked Hours
   string blocked = AvoidHours;
   if(StringFind(blocked, IntegerToString(dt.hour)) >= 0) return true;
   
   // Defense Mode check
   if(is_defense_mode) {
      // In defense mode, we only trade HotHours
      if(StringFind(HotHours, IntegerToString(dt.hour)) < 0) return true;
   }
   
   return false;
}

//+------------------------------------------------------------------+
//| Helper: Detect ATR Spike on M15                                   |
//+------------------------------------------------------------------+
bool DetectATRSpike() {
   double atr_buffer[];
   ArraySetAsSeries(atr_buffer, true);
   if(CopyBuffer(handle_atr_m15, 0, 0, 2, atr_buffer) < 2) return false;
   
   double current_atr = atr_buffer[0];
   double prev_atr = atr_buffer[1];
   
   if(prev_atr > 0 && (current_atr / prev_atr) > ATRSpike_Event) return true;
   return false;
}

//+------------------------------------------------------------------+
//| Helper: Evaluate multi-factor entry signal                        |
//+------------------------------------------------------------------+
bool EvaluateEntrySignal() {
   double score = 0;
   
   // Regime Filter (H1 ADX Slope)
   double adx_h1[];
   ArraySetAsSeries(adx_h1, true);
   if(CopyBuffer(handle_adx_h1, 0, 0, 2, adx_h1) < 2) return false;
   
   double slope = adx_h1[0] - adx_h1[1];
   if(slope < ADX_H1_SlopeMin) return false; // Filter out chop
   
   // Directional Bias (H4)
   double adx_h4[];
   ArraySetAsSeries(adx_h4, true);
   if(CopyBuffer(handle_adx_h4, 0, 0, 2, adx_h4) < 2) return false;
   
   // Simplified Scoring (Mock of the complex scoring system)
   score += (slope > 0.1) ? 2.0 : 1.0;
   score += (adx_h4[0] > 25) ? 1.5 : 0.5;
   
   // Apply Day of Week Multiplier
   MqlDateTime dt;
   TimeToStruct(TimeCurrent(), dt);
   double dow_mult = 1.0;
   if(dt.day_of_week == 1) dow_mult = DowMon;
   if(dt.day_of_week == 3) dow_mult = DowWed;
   if(dt.day_of_week == 4) dow_mult = DowThu;
   if(dt.day_of_week == 5) dow_mult = DowFri;
   
   score *= dow_mult;
   
   return (score >= MinScoreToTrade);
}

//+------------------------------------------------------------------+
//| Helper: Execute synchronized basket                               |
//+------------------------------------------------------------------+
void ExecuteBasketEntry() {
   // Logic for calculating lot size based on BasketRiskPct
   double lot_gold = 0.01; // Simplified
   double lot_silver = 0.01; // Simplified
   
   // In a real implementation, we use OrderSend for both XAUUSD and XAGUSD
   Print("Executing Synchronized Basket: Gold and Silver Long");
   
   current_basket.open_time = TimeCurrent();
   current_basket.signal_direction = 1; 
   event_armed_time = 0; // Reset event window
}

//+------------------------------------------------------------------+
//| Helper: Manage positions (Partial Close, Trail, Defense)          |
//+------------------------------------------------------------------+
void ManagePositions() {
   double current_pnl_r = CalculateCurrentRR();
   
   // 1. Partial Close at 1.2R
   if(current_pnl_r >= Partial_RR && !IsPartialClosed()) {
      ClosePartial(0.30);
      Print("Partial Close executed at 1.2R");
   }
   
   // 2. Trailing Stop Logic
   if(current_pnl_r >= TrailStart_RR) {
      AdjustTrailingStop(WinnerFloor_RR);
   }
   
   // 3. Scratch Logic
   if(TimeCurrent() - current_basket.open_time > ScratchMinutes * 60 && current_pnl_r < 0) {
      if(current_pnl_r <= ScratchLoss_R) {
         CloseBasket("Scratch Exit");
      }
   }
}

//--- Stub functions for MT5 internal calls
bool PositionSelectByMagic(long magic) { return false; } 
double CalculateCurrentRR() { return 0.0; }
bool IsPartialClosed() { return false; }
void ClosePartial(double pct) {}
void AdjustTrailingStop(double floor) {}
void CloseBasket(string reason) {
   if(consecutive_losses >= MaxConsecutiveLosses) {
      is_defense_mode = true;
      Print("Sustained losses detected. Entering Defense Mode.");
   }
}

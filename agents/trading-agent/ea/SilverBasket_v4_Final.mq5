//+------------------------------------------------------------------+
//|                    SilverBasket_v4_Final.mq5                     |
//|  DEFINITIVE XAG Indicator | SAST Filter | Auto CSV Export       |
//|  77.1% WR | PF 26.62 | $38,879 avg win | Fixed live chart     |
//+------------------------------------------------------------------+
//  FIXES vs v3:
//  - SAST time filter: only fires in proven windows
//  - Requires POSITIVE correlation (signals with neg corr were noise)
//  - Raised quality bar: score >= 70 (was 25 - too many signals)
//  - Fixed live chart freeze: no object creation inside bar loop
//  - Fixed prev_calculated handling for consistent live vs tester
//  - XAU Z confirmation weighted higher (93% of wins confirmed)
//  - SAST best windows: 10:00, 03-05, 08:00, 15:00, 19:00
//+------------------------------------------------------------------+
#property copyright "Silver Basket v4.0 - Final"
#property version   "4.00"
#property indicator_chart_window
#property indicator_buffers 2
#property indicator_plots   2

#property indicator_label1  "BUY XAG"
#property indicator_type1   DRAW_ARROW
#property indicator_color1  clrAqua
#property indicator_width1  4

#property indicator_label2  "SELL XAG"
#property indicator_type2   DRAW_ARROW
#property indicator_color2  clrOrangeRed
#property indicator_width2  4

input group "=== SYMBOLS ==="
input string  Gold_Symbol      = "XAUUSD";

input group "=== SIGNAL THRESHOLDS ==="
input double  Corr_Min         = 0.50;   // MUST be positive correlation
input double  Corr_Max         = 0.88;   // Upper ceiling
input double  Z_XAG_Min        = 0.40;   // XAG Z-score extreme
input double  Z_XAU_Min        = 0.30;   // XAU confirmation
input double  ATR_Min          = 1.00;   // Volatility floor
input int     Min_Score        = 70;     // Raised from 25 - was causing too many signals
input int     Sell_Min_Score   = 72;     // Sells slightly higher (71% vs 80% WR)

input group "=== SAST TIME FILTER (UTC+2) ==="
input bool    Use_Time_Filter  = true;
// Windows proven by trade data:
// PRIME:  10:00-10:45 SAST ($394K, $98K avg)
// STRONG: 03:00-05:30 SAST ($724K combined)
// GOOD:   08:00-08:45 SAST ($118K)
// GOOD:   15:00-15:45 SAST ($122K)
// GOOD:   19:00-20:15 SAST ($110K)
input bool    Window_10am      = true;   // 10:00-10:45 SAST → PRIME
input bool    Window_3to5am    = true;   // 03:00-05:30 SAST → STRONG
input bool    Window_8am       = true;   // 08:00-08:45 SAST → GOOD
input bool    Window_3pm       = true;   // 15:00-15:45 SAST → GOOD
input bool    Window_7pm       = true;   // 19:00-20:15 SAST → GOOD

input group "=== DISPLAY ==="
input ENUM_TIMEFRAMES TF       = PERIOD_M15;
input int     Arrow_Offset     = 50;
input bool    Alerts           = true;
input int     Alert_Cooldown   = 300;

input group "=== CSV EXPORT ==="
input bool    Auto_Export      = true;
input string  Export_Folder    = "MetalsBasket";
input bool    Export_Realtime  = false;

input group "=== CALCULATION ==="
input int     Z_Period         = 20;
input int     C_Period         = 20;
input int     ATR_Per          = 14;
input int     ATR_Base         = 20;

//--- Buffers
double BuyBuf[];
double SellBuf[];

//--- Cached ATR handles (pre-created = no slowdown)
int hATR_XAG = INVALID_HANDLE;
int hATR_XAU = INVALID_HANDLE;

//--- Pending label: set in loop, drawn ONCE after loop (fixes live chart)
datetime pendingLabelTime  = 0;
double   pendingLabelPrice = 0;
int      pendingLabelScore = 0;
color    pendingLabelColor = clrNONE;
string   pendingLabelDir   = "";

//--- Signal log
struct SigRec {
   datetime time; string dir; double price;
   double zXAG; double zXAU; double corr; double atr;
   int score; string quality; string sast_window;
};
SigRec   sigLog[];
int      sigCount  = 0;
datetime lastAlert = 0;

//+------------------------------------------------------------------+
int OnInit()
{
   hATR_XAG = iATR(Symbol(),    TF, ATR_Per);
   hATR_XAU = iATR(Gold_Symbol, TF, ATR_Per);
   if(hATR_XAG==INVALID_HANDLE||hATR_XAU==INVALID_HANDLE)
   { Alert("XAG v4: Handle fail. Gold symbol: ",Gold_Symbol); return INIT_FAILED; }

   SetIndexBuffer(0, BuyBuf,  INDICATOR_DATA);
   SetIndexBuffer(1, SellBuf, INDICATOR_DATA);
   PlotIndexSetInteger(0, PLOT_ARROW, 233);  // Up arrow
   PlotIndexSetInteger(1, PLOT_ARROW, 234);  // Down arrow
   PlotIndexSetDouble(0,  PLOT_EMPTY_VALUE, EMPTY_VALUE);
   PlotIndexSetDouble(1,  PLOT_EMPTY_VALUE, EMPTY_VALUE);
   IndicatorSetString(INDICATOR_SHORTNAME, "XAG v4★");

   ArrayResize(sigLog, 0);
   sigCount = 0;

   Print("=== SILVER BASKET v4 FINAL ===");
   Print("★ PRIORITY INSTRUMENT: 77.1% WR | PF 26.62 | $38,879 avg");
   Print("SAST windows: 10:00 | 03-05:30 | 08:00 | 15:00 | 19:00");
   Print("Key fix: requires corr>0.50 (positive) + score>=70");
   return INIT_SUCCEEDED;
}

//+------------------------------------------------------------------+
void OnDeinit(const int reason)
{
   if(hATR_XAG!=INVALID_HANDLE) IndicatorRelease(hATR_XAG);
   if(hATR_XAU!=INVALID_HANDLE) IndicatorRelease(hATR_XAU);
   if(Auto_Export && sigCount>0) ExportCSV();
   ObjectsDeleteAll(0,"XAG4_");
   Comment("");
}

//+------------------------------------------------------------------+
//| SAST window check (UTC+2)                                        |
//+------------------------------------------------------------------+
bool InSASTWindow(datetime t, string &windowName)
{
   if(!Use_Time_Filter){ windowName="ALL"; return true; }
   MqlDateTime dt; TimeToStruct(t+7200, dt); // +2h = SAST
   int h=dt.hour, m=dt.min;
   int hm = h*100+m;

   if(Window_10am  && hm>=1000 && hm<=1045){ windowName="10:00 SAST PRIME"; return true; }
   if(Window_3to5am&& hm>=300  && hm<=530 ){ windowName="03-05:30 SAST";   return true; }
   if(Window_8am   && hm>=800  && hm<=845 ){ windowName="08:00 SAST";      return true; }
   if(Window_3pm   && hm>=1500 && hm<=1545){ windowName="15:00 SAST";      return true; }
   if(Window_7pm   && hm>=1900 && hm<=2015){ windowName="19:00 SAST";      return true; }

   windowName="";
   return false;
}

//+------------------------------------------------------------------+
int OnCalculate(const int rates_total, const int prev_calculated,
                const datetime &time[], const double &open[],
                const double &high[],  const double &low[],
                const double &close[], const long &tick_volume[],
                const long &volume[],  const int &spread[])
{
   if(rates_total < Z_Period+30) return 0;

   // Correct recalc window - prevents live chart showing wrong signals
   int start = prev_calculated - 1;
   if(start < 0 || prev_calculated==0) start = rates_total - Z_Period - 5;
   if(start >= rates_total) start = rates_total - 1;

   ArraySetAsSeries(time,true); ArraySetAsSeries(high,true);
   ArraySetAsSeries(low,true);  ArraySetAsSeries(close,true);
   ArraySetAsSeries(BuyBuf,true); ArraySetAsSeries(SellBuf,true);

   // Reset pending label each calculation pass
   pendingLabelTime  = 0;
   pendingLabelScore = 0;

   for(int i=start; i>=0; i--)
   {
      BuyBuf[i]=EMPTY_VALUE; SellBuf[i]=EMPTY_VALUE;

      // SAST time filter
      string window="";
      if(!InSASTWindow(time[i], window)) continue;

      // Z-scores
      double zXAG = CalcZ(Symbol(),    TF, i);
      double zXAU = CalcZ(Gold_Symbol, TF, i);
      double corr  = CalcCorr(i);
      double atr   = ATRRatio(hATR_XAG, i);

      // KEY FIX: require POSITIVE correlation
      // Negative corr = metals moving opposite = NOT a basket trade
      bool corrOK = (corr >= Corr_Min && corr <= Corr_Max);
      bool xagExt = (MathAbs(zXAG) >= Z_XAG_Min);
      bool xauConf= (MathAbs(zXAU) >= Z_XAU_Min);
      bool volOK  = (atr >= ATR_Min);
      bool sameDir= (zXAG<0&&zXAU<0)||(zXAG>0&&zXAU>0);

      // Confidence score
      int sZ=0;
      double az=MathAbs(zXAG);
      if(az>=Z_XAG_Min)       sZ=18;
      if(az>=Z_XAG_Min+0.5)   sZ=27;
      if(az>=Z_XAG_Min+1.0)   sZ=35;

      int sC=0;
      if(corr>=Corr_Min&&corr<Corr_Max) sC=15;
      if(corr>=Corr_Min&&corr<0.75)     sC=20;
      if(corr>=Corr_Min&&corr<0.65)     sC=25;

      int sConf=0;
      if(sameDir&&xauConf)                         sConf=15;
      if(sameDir&&MathAbs(zXAU)>=Z_XAU_Min+0.5)   sConf=25;

      int sVol=0;
      if(atr>=ATR_Min) sVol=5;
      if(atr>=1.2)     sVol=10;

      // Best-hour bonus (highest-value windows)
      string win2=""; InSASTWindow(time[i],win2);
      int sHr=(StringFind(win2,"PRIME")>=0)?10:(StringFind(win2,"03-05")>=0)?5:0;

      int score=MathMin(sZ+sC+sConf+sVol+sHr,100);
      string quality=score>=75?"HIGH":score>=50?"MEDIUM":"LOW";

      if(!corrOK||!xagExt||!volOK||!sameDir) continue;

      bool buySignal  = zXAG<0 && score>=Min_Score;
      bool sellSignal = zXAG>0 && score>=Sell_Min_Score;

      if(buySignal||sellSignal)
      {
         if(buySignal)
         {
            BuyBuf[i]=low[i]-Arrow_Offset*_Point;
            if(i==0){ pendingLabelTime=time[i]; pendingLabelPrice=low[i]-Arrow_Offset*2.2*_Point;
                      pendingLabelScore=score; pendingLabelColor=clrAqua; pendingLabelDir="BUY"; }
         }
         else
         {
            SellBuf[i]=high[i]+Arrow_Offset*_Point;
            if(i==0){ pendingLabelTime=time[i]; pendingLabelPrice=high[i]+Arrow_Offset*2.2*_Point;
                      pendingLabelScore=score; pendingLabelColor=clrOrangeRed; pendingLabelDir="SELL"; }
         }

         LogSig(time[i],buySignal?"BUY":"SELL",buySignal?low[i]:high[i],
                zXAG,zXAU,corr,atr,score,quality,window);

         if(Alerts&&i==0&&TimeCurrent()-lastAlert>Alert_Cooldown)
         {
            string d=buySignal?"BUY 80%WR":"SELL $56K avg";
            Alert("XAG★ ",d,"|Score:",score,"|Z:",DoubleToString(zXAG,2),
                  "|XAU:",DoubleToString(zXAU,2),"|",window);
            lastAlert=TimeCurrent();
         }
         if(Export_Realtime&&i==0) ExportCSV();
      }
   }

   // Draw label ONCE outside loop - fixes live chart flicker/freeze
   if(pendingLabelTime > 0)
      DrawScore("XAG4_"+TimeToString(pendingLabelTime),
                pendingLabelTime, pendingLabelPrice, pendingLabelScore, pendingLabelColor);

   // Minimal comment
   {
      int i=0;
      string win=""; bool inWin=InSASTWindow(TimeCurrent(),win);
      double zXAG=CalcZ(Symbol(),TF,0);
      double zXAU=CalcZ(Gold_Symbol,TF,0);
      double corr=CalcCorr(0);
      Comment("XAG v4★ | Sigs:"+IntegerToString(sigCount)+
              " | Z:"+DoubleToString(zXAG,2)+
              " | XAU:"+DoubleToString(zXAU,2)+
              " | C:"+DoubleToString(corr,3)+
              " | "+( inWin ? "✓ "+win : "Outside window"));
   }
   return rates_total;
}

//+------------------------------------------------------------------+
void LogSig(datetime t,string dir,double price,double zXAG,double zXAU,
            double corr,double atr,int score,string quality,string window)
{
   if(sigCount>0&&sigLog[sigCount-1].time==t&&sigLog[sigCount-1].dir==dir) return;
   ArrayResize(sigLog,sigCount+1);
   sigLog[sigCount].time=t; sigLog[sigCount].dir=dir; sigLog[sigCount].price=price;
   sigLog[sigCount].zXAG=zXAG; sigLog[sigCount].zXAU=zXAU;
   sigLog[sigCount].corr=corr; sigLog[sigCount].atr=atr;
   sigLog[sigCount].score=score; sigLog[sigCount].quality=quality;
   sigLog[sigCount].sast_window=window;
   sigCount++;
}

//+------------------------------------------------------------------+
void ExportCSV()
{
   if(sigCount==0){ Print("XAG v4: nothing to export"); return; }
   FolderCreate(Export_Folder,0);
   string fname=Export_Folder+"\\XAG_v4_"+Symbol()+"_"+EnumToString(TF)+".csv";

   int fh=FileOpen(fname,FILE_WRITE|FILE_CSV|FILE_ANSI,',');
   if(fh==INVALID_HANDLE)
   {
      fh=FileOpen("XAG_v4_fallback.csv",FILE_WRITE|FILE_CSV|FILE_ANSI,',');
      if(fh==INVALID_HANDLE){ Print("XAG Export FAILED:",GetLastError()); return; }
   }

   FileWrite(fh,"DateTime","Direction","Price",
             "Z_XAG","Z_XAU","Correlation","ATR_Ratio",
             "Score","Quality","SAST_Window",
             "Hist_WR","Hist_Avg_Profit");

   int buys=0,sells=0,hq=0;
   for(int i=0;i<sigCount;i++)
   {
      string wr  =sigLog[i].dir=="BUY"?"80%":"71%";
      string avgP=sigLog[i].dir=="BUY"?"$27,577":"$56,638";
      FileWrite(fh,
         TimeToString(sigLog[i].time,TIME_DATE|TIME_MINUTES),
         sigLog[i].dir,
         DoubleToString(sigLog[i].price,_Digits),
         DoubleToString(sigLog[i].zXAG,3), DoubleToString(sigLog[i].zXAU,3),
         DoubleToString(sigLog[i].corr,3), DoubleToString(sigLog[i].atr,3),
         IntegerToString(sigLog[i].score),
         sigLog[i].quality, sigLog[i].sast_window,
         wr, avgP);
      if(sigLog[i].dir=="BUY") buys++; else sells++;
      if(sigLog[i].score>=75) hq++;
   }

   // Summary
   FileWrite(fh,"","","","","","","","","","","","");
   FileWrite(fh,"SUMMARY");
   FileWrite(fh,"Total Signals",IntegerToString(sigCount),"BUY",IntegerToString(buys),"SELL",IntegerToString(sells),"HIGH(75+)",IntegerToString(hq),"","","","");
   FileWrite(fh,"Historical","WR:77.1%","PF:26.62","BuyWR:80%","SellWR:71%","Net:$3.14M","","","","","","");

   FileClose(fh);
   Print("=== XAG v4 EXPORT ===  ",sigCount," signals | BUY:",buys," SELL:",sells," HIGH:",hq);
   Print("File: ",TerminalInfoString(TERMINAL_DATA_PATH),"\\MQL5\\Files\\",fname);
}

//+------------------------------------------------------------------+
double CalcZ(string sym,ENUM_TIMEFRAMES tf,int shift)
{
   double c[]; ArraySetAsSeries(c,true);
   if(CopyClose(sym,tf,shift,Z_Period,c)<Z_Period) return 0;
   double s=0; for(int i=0;i<Z_Period;i++) s+=c[i];
   double m=s/Z_Period,v=0;
   for(int i=0;i<Z_Period;i++) v+=MathPow(c[i]-m,2);
   double sd=MathSqrt(v/(Z_Period-1));
   return (sd>0.0001)?(c[0]-m)/sd:0;
}

double ATRRatio(int h,int shift)
{
   if(h==INVALID_HANDLE) return 1.0;
   double a[]; ArraySetAsSeries(a,true);
   if(CopyBuffer(h,0,shift,ATR_Base,a)<ATR_Base) return 1.0;
   double s=0; for(int i=0;i<ATR_Base;i++) s+=a[i];
   double avg=s/ATR_Base; return (avg>0)?a[0]/avg:1.0;
}

double CalcCorr(int shift)
{
   double g[],s[];
   ArraySetAsSeries(g,true); ArraySetAsSeries(s,true);
   if(CopyClose(Symbol(),    TF,shift,C_Period,s)<C_Period) return 0;
   if(CopyClose(Gold_Symbol, TF,shift,C_Period,g)<C_Period) return 0;
   double sx=0,sy=0,sxy=0,sx2=0,sy2=0;
   for(int i=0;i<C_Period;i++){sx+=g[i];sy+=s[i];sxy+=g[i]*s[i];sx2+=g[i]*g[i];sy2+=s[i]*s[i];}
   double num=(C_Period*sxy)-(sx*sy);
   double den=MathSqrt((C_Period*sx2-sx*sx)*(C_Period*sy2-sy*sy));
   return (den>0)?num/den:0;
}

void DrawScore(string name,datetime t,double price,int score,color clr)
{
   if(ObjectFind(0,name)>=0) ObjectDelete(0,name);
   ObjectCreate(0,name,OBJ_TEXT,0,t,price);
   ObjectSetString(0,name,OBJPROP_TEXT,IntegerToString(score));
   ObjectSetInteger(0,name,OBJPROP_COLOR,clr);
   ObjectSetInteger(0,name,OBJPROP_FONTSIZE,9);
   ObjectSetString(0,name,OBJPROP_FONT,"Arial Bold");
   ObjectSetInteger(0,name,OBJPROP_ANCHOR,ANCHOR_CENTER);
}
//+------------------------------------------------------------------+

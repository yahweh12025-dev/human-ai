# Trend Filter Specification

## Goal
Suppress strong short signals when a sustained bullish trend is detected.

## Input
- Price series `P_t` (closing price at time `t`)
- Short‑term score `S_t` (raw short‑signal score from scoring engine)
- Lookback window `L` (e.g., 20 periods)

## Parameters
- `MA_long = SMA(P, N)` – `N`‑period simple moving average (e.g., 50)
- `ΔMA = MA_long(t) - MA_long(t-1)`
- `R = (P_t - MA_long(t)) / MA_long(t)` – relative distance to long MA
- `BullThresh = 0.04` – minimum relative distance to declare bullish
- `SlopeThresh = 0.02` – minimum positive slope of MA over last `M` bars (e.g., 5)
- `α = 5` – aggressiveness factor

## Logic
1. **Detect Bull Run**  
   - Condition A: `R > BullThresh`  
   - Condition B: `ΔMA > SlopeThresh` (MA is rising)  
   - If both true → `BullRun = true`

2. **Compute Adjustment Factor**  
   - `AdjFactor = 1 / (1 + α * R)` when `BullRun` is true, otherwise `AdjFactor = 1`

3. **Scale Short Score**  
   - `S_filtered_t = S_t * AdjFactor`  
   - If `BullRun` and `AdjFactor < 0.2` then `S_filtered_t = 0` (strong short signals are suppressed)

## Output
- `S_filtered_t` is fed into the overall position sizing logic. No other scoring components are altered.

## Implementation Notes
- All calculations are integer‑safe; use fixed‑point precision of 1e‑6.  
- `MA_long` and `ΔMA` are recomputed on each bar; `BullRun` resets only when conditions fail for `M` consecutive bars.  
- The filter is applied only to short‑leg signals; long‑leg signals remain unchanged.
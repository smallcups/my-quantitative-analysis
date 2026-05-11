"""生成自动因子选择与权重优化原理文档"""
from fpdf import FPDF
import fpdf.fpdf as _fp

# Monkey-patch: prevent crash on long strings
_orig_mc = _fp.FPDF.multi_cell
def _safe_mc(self, w, h, txt='', **kw):
    if txt:
        parts = []
        for word in str(txt).split(' '):
            if len(word) > 50:
                for i in range(0, len(word), 50):
                    parts.append(word[i:i+50])
            else:
                parts.append(word)
        txt = ' '.join(parts)
    try:
        return _orig_mc(self, w, h, txt, **kw)
    except:
        return _orig_mc(self, w, h, '(.)', **kw)
_fp.FPDF.multi_cell = _safe_mc


class PDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Courier', 'I', 7)
            self.set_text_color(120, 120, 120)
            self.cell(0, 6, 'Automatic Factor Selection & Weight Optimization', 0, 1, 'C')

    def footer(self):
        self.set_y(-14)
        self.set_font('Courier', 'I', 7)
        self.cell(0, 10, str(self.page_no()), 0, 0, 'C')

    def t(self, s):
        self.set_font('Courier', 'B', 14)
        self.set_text_color(0, 40, 90)
        self.cell(0, 10, s, 0, 1)
        self.ln(3)

    def h1(self, s):
        self.ln(3)
        self.set_font('Courier', 'B', 11)
        self.set_text_color(0, 60, 130)
        self.cell(0, 8, s, 0, 1)
        self.ln(2)

    def h2(self, s):
        self.set_font('Courier', 'B', 9)
        self.set_text_color(50, 50, 50)
        self.cell(0, 6, s, 0, 1)
        self.ln(1)

    def p(self, s):
        self.set_font('Courier', '', 8.5)
        self.set_text_color(40, 40, 40)
        self.set_left_margin(12)
        self.multi_cell(0, 4.5, s)
        self.ln(1)

    def code(self, lines):
        if not isinstance(lines, list):
            lines = lines.split('\n')
        lines = [l[:95] for l in lines]
        self.set_font('Courier', '', 7)
        self.set_fill_color(248, 248, 252)
        self.set_draw_color(190, 190, 210)
        h = len(lines) * 3.3 + 4
        if self.get_y() + h > 265:
            self.add_page()
        y0 = self.get_y()
        self.rect(10, y0, 190, h, 'DF')
        self.set_xy(12, y0 + 2)
        for l in lines:
            self.set_x(12)
            self.cell(0, 3.3, l, 0, 1)
        self.set_y(y0 + h + 3)

    def formula(self, s):
        self.set_font('Courier', 'B', 9)
        self.set_text_color(0, 70, 70)
        self.cell(0, 6, s, 0, 1)
        self.ln(2)


pdf = PDF()
pdf.alias_nb_pages()
pdf.set_auto_page_break(True, 20)

# === Cover ===
pdf.add_page()
pdf.ln(30)
pdf.set_font('Courier', 'B', 22)
pdf.set_text_color(0, 40, 90)
pdf.cell(0, 12, 'Automatic Factor Selection', 0, 1, 'C')
pdf.cell(0, 12, '& Weight Optimization', 0, 1, 'C')
pdf.ln(8)
pdf.set_font('Courier', '', 11)
pdf.set_text_color(60, 60, 60)
pdf.cell(0, 7, 'Principle and Implementation', 0, 1, 'C')
pdf.ln(10)
pdf.set_font('Courier', '', 9)
pdf.set_text_color(100, 100, 100)
pdf.cell(0, 6, 'Based on Rank IC (Information Coefficient) Analysis', 0, 1, 'C')
pdf.cell(0, 6, 'Multi-Factor Stock Selection System', 0, 1, 'C')

# === 1 ===
pdf.add_page()
pdf.t('1. Core Problem')
pdf.p(
    'In a multi-factor stock selection system, we face two fundamental questions: '
    '(1) Which factors actually predict stock returns? (2) How much weight should each factor have? '
    'Without an automated method, these are decided manually, leading to subjective bias, '
    'inability to adapt to changing market conditions, and lack of statistical rigour.'
)
pdf.p(
    'The solution presented here uses Rank IC (Information Coefficient) analysis, the '
    'standard quantitative method for evaluating factor effectiveness. It automatically '
    'selects the most effective factors and computes optimal, data-driven weights.'
)

# === 2 ===
pdf.t('2. The Core Metric: Rank IC')
pdf.h1('2.1 Definition')
pdf.p(
    'Rank IC (Rank Information Coefficient) measures the predictive power of a factor. '
    'It is defined as the Spearman rank correlation between factor values on date T and '
    'future N-day stock returns.'
)
pdf.formula('Rank IC(t, f, N) = SpearmanRho( factor_value(T), forward_return(T, T+N) )')
pdf.p(
    'Where factor_value(T) is the cross-sectional factor value for all stocks on date T, '
    'and forward_return(T, T+N) = (close_price[T+N] - close_price[T]) / close_price[T].'
)

pdf.h1('2.2 Why Spearman Instead of Pearson?')
pdf.p(
    'Stock factor values and returns are typically non-normally distributed with heavy tails. '
    'Pearson correlation assumes normal distribution and is sensitive to outliers. '
    'Spearman rank correlation is distribution-free: it only cares about the rank order '
    'of values, not their absolute magnitudes. This makes it robust to the extreme values '
    'common in financial data.'
)

pdf.h1('2.3 What Does IC Actually Mean?')
pdf.p(
    'An IC of +0.10 means that stocks with higher factor values tend to have higher '
    'future returns, and the rank correspondence is moderate. An IC of -0.10 means the '
    'opposite direction (mean-reversion). An IC of 0.00 means the factor has no predictive '
    'power at all - its values and future returns are completely unrelated.'
)
pdf.p(
    'IC is computed on a single date. To evaluate a factor over time, we compute IC on '
    'every trading date in the evaluation window, producing an IC time series. From this '
    'series we derive four aggregate statistics.'
)

# === 3 ===
pdf.t('3. Rolling IC Statistics')
pdf.p(
    'For each factor, IC is computed on every trading date between start_date and end_date. '
    'Given N valid IC observations, we compute:'
)

pdf.formula('IC_mean  = (1/N) * SUM(IC_i)              -- Average predictive power')
pdf.formula('IC_std   = SQRT( (1/(N-1)) * SUM(IC_i - IC_mean)^2 )  -- Stability')
pdf.formula('IC_IR    = IC_mean / IC_std               -- Information Ratio')
pdf.formula('IC_win_rate = COUNT(IC_i > 0) / N          -- Consistency')

pdf.h1('3.1 Why IC_IR is the Key Metric')
pdf.p(
    'IC_IR (Information Ratio of IC) is the primary metric because it captures both '
    'predictive power AND stability in a single number. Consider two factors:\n\n'
    '  Factor A: IC_mean = 0.05, IC_std = 0.02  ->  IC_IR = 2.5\n'
    '  Factor B: IC_mean = 0.10, IC_std = 0.10  ->  IC_IR = 1.0\n\n'
    'Factor B has higher average IC, but Factor A is far more stable. Factor A is '
    'preferred because its predictive ability is reliable, not sporadic. A factor that '
    'is great on Monday but terrible on Tuesday is dangerous for trading.'
)

# === 4 ===
pdf.t('4. Single-Day IC Computation (Algorithm)')
pdf.code('''# Step 1: Get factor values for ALL stocks on date T
factor_df = factor_engine.get_factor_exposure(factor_id, trade_date)
# Returns: ts_code, factor_value, z_score, percentile_rank

# Step 2: Get current close prices (single SQL query, ~5473 rows)
current_data = query(StockDailyHistory).filter(trade_date == T)

# Step 3: Get all future prices (single query)
price_data = query(StockDailyHistory).filter(trade_date > T)

# Step 4: For each stock, get the N-th future close (vectorized)
# Using groupby.cumcount avoids per-stock Python loops
position = price_data.groupby('ts_code').cumcount()
future_close = price_data[position == N-1][['ts_code', 'close']]

# Step 5: Compute forward returns and merge with factor values
merged = merge(current_close, future_close, factor_df, on='ts_code')
merged['forward_return'] = (merged['future_close']-merged['close'])/merged['close']

# Step 6: Spearman rank correlation
ic, p_value = spearmanr(merged['factor_value'], merged['forward_return'])
# Returns: ic_value = ±1.0 range, p_value for significance test''')

# === 5 ===
pdf.t('5. Factor Selection (Two-Stage)')
pdf.h1('5.1 Stage 1: IC_IR Threshold Filtering')
pdf.p(
    'All factors with |IC_IR| below a configurable threshold (default 0.3) are eliminated. '
    'Factors with |IC_IR| near zero have no statistically meaningful predictive power. '
    'If too few factors pass the threshold, the system automatically relaxes it and takes '
    'the top N factors by absolute IC_IR to ensure a minimum number of selected factors.'
)
pdf.code('''valid = [f for f in all_factors if abs(f.ic_ir) > threshold]

# Automatic relaxation if too few factors pass
if len(valid) < min_factors:
    valid = sorted(all_factors, key=lambda x: abs(x.ic_ir), reverse=True)
    valid = valid[:max(max_factors, min_factors)]''')

pdf.h1('5.2 Stage 2: Correlation Redundancy Removal')
pdf.p(
    'Factors that are highly correlated with each other provide redundant information. '
    'For example, momentum_5d and momentum_20d are both momentum-type factors and tend '
    'to have similar values. Including both gives double weight to momentum without '
    'adding new information.'
)
pdf.p(
    'Redundancy is removed using a greedy algorithm: (1) Compute the Spearman correlation '
    'matrix between all factor values. (2) Sort factors by |IC_IR| descending. (3) Iterate '
    'through the sorted list: if a factor has correlation > max_correlation (default 0.7) '
    'with any already-selected factor, skip it. Otherwise, add it to the selected set.'
)
pdf.code('''corr_matrix = factor_values_pivot.corr(method='spearman')
selected, selected_ids = [], set()

for f in sorted(valid_factors, key=lambda x: abs(x.ic_ir), reverse=True):
    redundant = False
    for sid in selected_ids:
        if abs(corr_matrix.loc[sid, f.id]) > max_correlation:  # e.g., 0.7
            redundant = True
            break
    if not redundant:
        selected_ids.add(f.id)
        selected.append(f)''')

# === 6 ===
pdf.t('6. Weight Calculation')
pdf.p(
    'Once the optimal set of factors is selected, weights are calculated proportional '
    'to each factor's absolute IC_IR value, then normalized to sum to 1.0:'
)
pdf.formula('weight_i = |IC_IR_i| / SUM( |IC_IR_j| )     for all selected j')
pdf.p(
    'Three weight methods are available. The default ic_ir_weighted uses |IC_IR| as '
    'the weighting basis, favouring factors that are both predictive and stable. '
    'ic_mean_weighted uses absolute IC mean, emphasising raw predictive power. '
    'equal_weight assigns uniform weights, useful as a baseline for comparison.'
)

pdf.h1('6.1 Weight Calculation Code')
pdf.code('''ic_irs = [abs(f['ic_ir']) for f in selected_factors]
weights = ic_irs / ic_irs.sum()
# Normalized to sum = 1.0

# Example output from real A-share data (2025 Q1):
# {
#   "volatility_20d": 0.423,   # strongest: high IC_IR, most stable
#   "momentum_5d":    0.301,   # second
#   "momentum_20d":   0.157,   # third
#   "momentum_1d":    0.120    # weakest but still significant
# }''')

# === 7 ===
pdf.t('7. End-to-End Pipeline')
pdf.h1('7.1 Data Flow')
pdf.code('''[1] Raw market data (stock_daily_history: 1.47M rows, 5,473 stocks, 272 days)
     |
     v
[2] Factor computation (scripts/calculate_factors.py)
     Price data -> pandas vectorized ops -> 6 technical factors
     factor_values: 8.37M rows
     |
     v
[3] IC analysis (FactorOptimizer.analyze_all_factors)
     For each factor x each trading date:
       factor_value + future_return -> Spearman correlation -> IC
     -> Rolling statistics: IC_mean, IC_IR, IC_win_rate
     -> Persist to factor_effectiveness table
     |
     v
[4] Factor selection (FactorOptimizer.select_factors)
     Stage 1: |IC_IR| > threshold filter
     Stage 2: Correlation redundancy removal (greedy)
     Output: 4 selected factors from 6 candidates
     |
     v
[5] Weight calculation (FactorOptimizer._compute_weights)
     weights = |IC_IR| / sum(|IC_IR|)
     Output: {volatility_20d: 0.423, momentum_5d: 0.301, ...}
     |
     v
[6] Stock scoring (StockScoringEngine._rank_ic_scoring)
     factor_scores * weights -> composite_score per stock
     -> rank by score -> Top N stocks selected
     |
     v
[7] Backtesting (BacktestEngine)
     Monthly rebalance with auto-weights -> performance metrics''')

pdf.h1('7.2 API Endpoint')
pdf.code('''POST /api/ml-factor/factors/auto-weight
{
    "evaluation_date": "2025-04-01",    # analysis end date
    "start_date": "2025-01-03",          # analysis start date
    "forward_period": 5,                 # return horizon (days)
    "weight_method": "ic_ir_weighted",   # weighting method
    "ic_ir_threshold": 0.1,              # min |IC_IR| to keep
    "max_correlation": 0.7,              # max inter-factor correlation
    "min_factors": 2,                    # min factors to select
    "max_factors": 8                     # max factors to select
}''')

# === 8 ===
pdf.t('8. Real Data Results')
pdf.p('Analysis of A-share data from 2025-01-03 to 2025-04-15 (66 trading days, 6 technical factors):')
pdf.code('''Factor               IC_mean     IC_IR    WinRate    Selected?  Weight
volatility_20d       -0.1566    -0.64     29%        YES        42.3%
momentum_5d          -0.0533    -0.45     26%        YES        30.1%
momentum_20d         -0.0376    -0.24     39%        YES        15.7%
momentum_1d          -0.0289    -0.18     40%        YES        12.0%
volume_ratio_20d     -0.0015    -0.02     50%        NO         (IC_IR too low)
price_to_ma20        -0.0115    -0.16     47%        NO         (redundant)

Key findings:
1. All factors showed NEGATIVE IC in this period (mean-reversion market)
2. volatility_20d dominates with 42% weight (highest |IC_IR|)
3. volume_ratio_20d eliminated: IC too close to zero
4. price_to_ma20 eliminated: redundant with momentum factors
5. Weights correctly sum to 1.0''')

# === 9 ===
pdf.t('9. Comparison with Manual Weighting')
pdf.p(
    'Without automated factor optimization, the typical approach is to assign equal '
    'weights (1/N) to all factors, or use subjective weights based on intuition. '
    'Both approaches have significant drawbacks: equal weighting gives noise factors '
    'the same influence as predictive factors; subjective weighting is inconsistent '
    'and unreproducible.'
)
pdf.p(
    'The Rank IC approach is data-driven: weights are derived from actual historical '
    'performance, noise factors are automatically filtered out, redundant factors are '
    'eliminated, and the entire process is reproducible. When market conditions change, '
    'the analysis can be re-run with a new date window to adapt weights dynamically.'
)

# === 10 ===
pdf.t('10. Practical Usage')
pdf.p('The system supports three integration modes:')
pdf.code('''[Mode 1] Direct API call
  POST /api/ml-factor/factors/auto-weight
  Returns optimized weights for immediate use.

[Mode 2] Frontend workflow (/ml-factor/optimization)
  Configure parameters -> Run IC analysis -> View weight chart
  -> One-click backtest with auto-weights vs equal-weight comparison.

[Mode 3] Backtest integration (/ml-factor/backtest)
  Select "auto IC weight" scoring method -> Calculate optimal weights
  -> Auto-checked factors -> Run backtest -> Compare strategies.

[Mode 4] Automated scoring
  StockScoringEngine with method="rank_ic"
  Automatically fetches optimized weights on each scoring call.''')


out_path = 'D:/quantitative_analysis/pdf/Automatic Factor Selection and Weight Optimization.pdf'
pdf.output(out_path)
print(f'Created: {out_path}')

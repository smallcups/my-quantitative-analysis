"""生成完整项目技术文档 PDF"""
from fpdf import FPDF
import fpdf.fpdf as _fp

# Monkey-patch: prevent crash on unbreakable long strings
_orig_mc = _fp.FPDF.multi_cell
def _safe_mc(self, w, h, txt='', **kw):
    if txt:
        parts = []
        for word in str(txt).split(' '):
            if len(word) > 45:
                for i in range(0, len(word), 45):
                    parts.append(word[i:i+45])
            else:
                parts.append(word)
        txt = ' '.join(parts)
    try:
        return _orig_mc(self, w, h, txt, **kw)
    except Exception:
        return _orig_mc(self, w, h, '(.)', **kw)
_fp.FPDF.multi_cell = _safe_mc

project_root = 'D:/quantitative_analysis'

class DocPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font('Courier', 'I', 7)
            self.set_text_color(120,120,120)
            self.cell(0, 6, 'Multi-Factor Stock Selection System - Technical Documentation', 0, 1, 'C')

    def footer(self):
        self.set_y(-14)
        self.set_font('Courier', 'I', 7)
        self.cell(0, 10, str(self.page_no()), 0, 0, 'C')

    def section_title(self, s):
        self.set_font('Courier', 'B', 16)
        self.set_text_color(0, 40, 90)
        self.cell(0, 12, s, 0, 1)
        self.ln(3)

    def h1(self, s):
        self.ln(3)
        self.set_font('Courier', 'B', 12)
        self.set_text_color(0, 60, 130)
        self.cell(0, 8, s, 0, 1)
        self.ln(2)

    def h2(self, s):
        self.set_font('Courier', 'B', 9.5)
        self.set_text_color(50, 50, 50)
        self.cell(0, 6, s, 0, 1)
        self.ln(1)

    def _break_long(self, s, max_chunk=40):
        if not s:
            return s
        parts = []
        for word in str(s).split(' '):
            if len(word) > max_chunk:
                for i in range(0, len(word), max_chunk):
                    parts.append(word[i:i+max_chunk])
            else:
                parts.append(word)
        return ' '.join(parts)

    def p(self, s):
        s = self._break_long(s)
        self.set_font('Courier', '', 8)
        self.set_text_color(40, 40, 40)
        self.set_left_margin(12)
        self.set_right_margin(10)
        self.multi_cell(0, 4.2, s)
        self.ln(1)

    def code(self, lines, trim=30):
        if not isinstance(lines, list):
            lines = lines.split('\n')
        if len(lines) > trim:
            lines = lines[:trim]
        self.set_font('Courier', '', 6.2)
        self.set_fill_color(248, 248, 252)
        self.set_draw_color(190, 190, 210)
        trimmed = [self._break_long(l[:100], 85) for l in lines]
        h = len(trimmed) * 3.3 + 4
        if self.get_y() + h > 268:
            self.add_page()
        y0 = self.get_y()
        self.rect(10, y0, 190, h, 'DF')
        self.set_xy(12, y0 + 2)
        for l in trimmed:
            self.set_x(12)
            self.cell(0, 3.3, l, 0, 1)
        self.set_y(y0 + h + 3)

    def bullet(self, items):
        self.set_font('Courier', '', 8)
        for item in items:
            item = self._break_long(item, 35)
            self.set_x(10)
            self.multi_cell(0, 4.2, '- ' + item)
        self.ln(1)


def pdf1_system_architecture():
    """PDF1: System Architecture & API Reference"""
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(True, 20)

    # === Cover ===
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Courier', 'B', 24)
    pdf.set_text_color(0, 40, 90)
    pdf.cell(0, 14, 'Multi-Factor Stock', 0, 1, 'C')
    pdf.cell(0, 14, 'Selection System', 0, 1, 'C')
    pdf.ln(6)
    pdf.set_font('Courier', '', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, 'System Architecture & API Reference', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Courier', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Flask + SQLAlchemy + Redis + WebSocket', 0, 1, 'C')
    pdf.cell(0, 6, 'A-Share Quantitative Analysis Platform', 0, 1, 'C')

    # === 1. Overview ===
    pdf.add_page()
    pdf.section_title('1. Project Overview')
    pdf.p(
        'The Multi-Factor Stock Selection System is a comprehensive quantitative analysis platform '
        'for China A-share markets. It integrates factor computation (18+ built-in factors), machine '
        'learning modeling (Random Forest, XGBoost, LightGBM), automated factor optimization via Rank IC '
        'analysis, portfolio optimization (Mean-Variance, Risk Parity), backtesting, real-time WebSocket '
        'data streaming, and natural language Text2SQL queries. The system is built with Python 3.13 '
        'and Flask 3.1, using MySQL for persistence and Redis for caching.'
    )
    pdf.bullet([
        'Factor Management: 18 built-in factors (momentum, volatility, PE/PB, ROE, money flow, etc.)',
        'ML Modeling: RF/XGBoost/LightGBM for stock return prediction with automated feature importance',
        'Factor Optimization: Rank IC-based automatic factor selection and weight calculation',
        'Stock Scoring: Multi-method scoring (equal/IC-weighted/ML-ensemble/manual-weight)',
        'Portfolio Optimization: CVXPY/Scipy solvers for mean-variance, risk parity, equal weight',
        'Backtesting: Full strategy engine with performance metrics, benchmark comparison',
        'Real-time Analysis: Flask-SocketIO + eventlet for minute-level indicator streaming',
        'Text2SQL: jieba NLP + LLM for natural language to SQL query conversion',
        'Data Sources: Tushare (API), Baostock (free), akshare (HTTP scraping)',
    ])

    # === 2. Architecture ===
    pdf.h1('2. System Architecture')
    pdf.p(
        'The system follows a classic three-layer architecture with Flask application factory pattern. '
        '13 blueprints register API and page routes. Services use lazy-initialized singleton pattern. '
        'Data layer uses SQLAlchemy ORM with 19+ models mapping to MySQL tables.'
    )

    pdf.h2('2.1 Application Factory')
    pdf.code('''# app/__init__.py
def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    db.init_app(app)
    socketio.init_app(app, message_queue=...)
    CORS(app)

    # Register 13+ blueprints
    from app.api import api_bp              # /api/*
    from app.api.ml_factor_api import ml_factor_bp  # /api/ml-factor/*
    from app.api.text2sql_api import text2sql_bp
    from app.api.realtime_analysis import realtime_analysis_bp
    from app.routes.ml_factor_routes import ml_factor_routes  # /ml-factor/*
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(ml_factor_bp)
    app.register_blueprint(ml_factor_routes)
    ...
    return app''')

    pdf.h2('2.2 Three-Layer Design')
    pdf.bullet([
        'API Layer (app/api/): 11 blueprint modules handling HTTP requests/responses with JSON',
        'Service Layer (app/services/): 17 service classes containing core business logic',
        'Data Layer (app/models/): 19 SQLAlchemy ORM models mapping to MySQL tables',
        'Frontend (app/templates/ + app/static/): Jinja2 + Bootstrap 5 + ECharts + Axios',
    ])

    pdf.h2('2.3 Technology Stack')
    pdf.bullet([
        'Web: Flask 3.1 + Flask-SocketIO 5.6 + Flask-RESTful + Flask-CORS',
        'Database: MySQL + PyMySQL + SQLAlchemy 2.0 ORM + Redis 7',
        'ML: scikit-learn 1.8 + XGBoost 3.2 + LightGBM 4.6',
        'Optimization: CVXPY 1.8 + SciPy 1.17 + clarabel solver',
        'Data: pandas 3.0 + numpy 2.4 + scipy + statsmodels',
        'NLP: jieba 0.42 (Chinese word segmentation)',
        'Realtime: APScheduler + eventlet + Flask-SocketIO',
        'Frontend: Jinja2 + Bootstrap 5.1 + ECharts 5.4 + Axios 1.5',
    ])

    # === 3. Data Layer ===
    pdf.h1('3. Database Schema')
    pdf.p('The database (stock_cursor) contains 20+ tables organized into categories:')

    pdf.h2('3.1 Core Data Tables')
    pdf.code('''stock_basic               # 5,473 A-share stocks (code, name, industry, area, list_date)
stock_daily_history       # 1,472,328 rows of daily OHLCV (2025-01 ~ 2026-02)
stock_daily_basic         # 376,125 rows of daily fundamentals (PE, PB, turnover, MV)
stock_factor              # 1,130,126 rows of technical indicators (MACD, KDJ, RSI, etc.)
stock_moneyflow           # 459,389 rows of money flow by order size
stock_cyq_perf            # 218,073 rows of chip distribution data
stock_income_statement    # Financial income statements (TTM)
stock_balance_sheet       # Financial balance sheets
stock_trade_calendar      # 4,383 trading calendar dates (2024-2026)''')

    pdf.h2('3.2 Factor & ML Tables')
    pdf.code('''factor_definition       # Custom factor definitions (id, formula, type, params)
factor_values           # 8,372,406 rows of computed factor values (ts_code + date + factor_id)
factor_effectiveness    # IC analysis results (factor_id + eval_date + forward_period PK)
ml_model_definition     # ML model metadata (type, factor_list, params, feature_importance)
ml_predictions          # 23,846 rows of model predictions (ts_code + date + model_id PK)''')

    pdf.h2('3.3 Real-time & Text2SQL Tables')
    pdf.code('''realtime_indicator      # Real-time technical indicators (minute-level)
trading_signal          # Trading signal records with confidence scores
risk_alert              # Risk alerts with severity levels
portfolio_position      # Portfolio holdings and weight tracking
realtime_report         # Analysis reports generated in real-time
table_metadata          # Text2SQL table schema metadata
field_metadata          # Text2SQL field descriptions
query_template          # Text2SQL query templates
query_history           # Text2SQL query execution history
business_dictionary     # Chinese-English business term mappings''')

    # === 4. Factor Engine ===
    pdf.h1('4. Factor Engine')
    pdf.p(
        'The FactorEngine (app/services/factor_engine.py, 900 lines) computes 18 built-in factors '
        'across four categories: technical, fundamental, money flow, and chip distribution. Custom '
        'factors can be registered via the API. Factor values are stored with Z-scores and percentile '
        'rankings for cross-sectional comparison.'
    )

    pdf.h2('4.1 Built-in Factors')
    pdf.bullet([
        'Technical (6): momentum_1d/5d/20d, volatility_20d, volume_ratio_20d, price_to_ma20',
        'Fundamental (7): pe_percentile, pb_percentile, ps_percentile, roe_ttm, roa_ttm, revenue_growth, profit_growth',
        'Money Flow (3): money_flow_strength, big_order_ratio, money_flow_momentum',
        'Chip Distribution (2): chip_concentration, winner_rate_change',
    ])

    pdf.h2('4.2 Factor Calculation Pipeline')
    pdf.code('''# Optimized batch computation (scripts/calculate_factors.py)
# Pre-load all 1.47M stock daily records into pandas DataFrame
price_df = pd.read_sql('SELECT ts_code, trade_date, close, pre_close, vol FROM stock_daily_history', db.engine)

for trade_date in all_dates:
    # Single fetch, compute all 6 technical factors in one pass
    hist = price_df[price_df['trade_date'] <= trade_dt]
    records.extend(compute_momentum_1d(day_data))
    records.extend(compute_momentum_5d(close_series))
    records.extend(compute_momentum_20d(close_series))
    records.extend(compute_volatility_20d(close_series))
    records.extend(compute_volume_ratio(vol_data, day_data))
    records.extend(compute_price_to_ma20(close_series, day_data))

    # Batch insert every 10 dates
    if i % 10 == 9:
        cursor.executemany(sql, batch); conn.commit()''')

    # === 5. ML Models ===
    pdf.h1('5. Machine Learning Models')
    pdf.p(
        'MLModelManager supports Random Forest, XGBoost, and LightGBM. Models are trained on factor '
        'values with future N-day returns as targets. After training, feature importances are '
        'persisted to the database for ensemble scoring. Model files are saved to disk (models/*.pkl).'
    )
    pdf.code('''# Model configuration
model_configs = {
    'random_forest': RandomForestRegressor(n_estimators=100, max_depth=10),
    'xgboost':       XGBRegressor(n_estimators=100, max_depth=6, learning_rate=0.1),
    'lightgbm':      LGBMRegressor(n_estimators=100, max_depth=6, learning_rate=0.1)
}

# Training pipeline
X, y = prepare_training_data(model_id, start_date, end_date)
X_processed, features = feature_engineering(X, y, config)  # RobustScaler + SelectKBest
X_train, X_test, y_train, y_test = train_test_split(X_processed, y, shuffle=False)
model.fit(X_train, y_train)

# Persist feature importance for ensemble scoring
model_def.feature_importance = dict(zip(features, model.feature_importances_))
db.session.commit()
joblib.dump(model, f'models/{model_id}.pkl')''')

    # === 6. Factor Optimizer ===
    pdf.h1('6. Factor Optimization Engine')
    pdf.p(
        'FactorOptimizer (app/services/factor_optimizer.py, 500+ lines) implements automatic factor '
        'selection and weight optimization based on Rank IC analysis - the standard quantitative method '
        'for evaluating factor effectiveness.'
    )

    pdf.h2('6.1 Rank IC Computation')
    pdf.code('''# Rank IC = Spearman correlation between factor values and forward N-day returns
def compute_rank_ic(self, factor_id, trade_date, forward_period=5):
    factor_df = get_factor_exposure(factor_id, trade_date)  # N stocks x factor values
    prices = get_future_prices(trade_date, forward_period)   # N stocks x future close
    merged = factor_df.merge(prices, on='ts_code')
    merged['forward_return'] = (merged['future_close'] - merged['current_close']) / merged['current_close']
    ic, p_value = spearmanr(merged['factor_value'], merged['forward_return'])
    return {'ic_value': float(ic), 'sample_count': len(merged), 'success': True}''')

    pdf.h2('6.2 Rolling IC Statistics')
    pdf.p(
        'For each factor, IC is computed on every trading date in the evaluation window. Four metrics '
        'are aggregated: IC_mean (average predictive power), IC_std (stability), IC_IR = IC_mean/IC_std '
        '(comprehensive score), and IC_win_rate (percentage of positive IC days).'
    )

    pdf.h2('6.3 Factor Selection (Two-Stage)')
    pdf.code('''# Stage 1: IC_IR threshold filtering
valid = [f for f in data if abs(f['ic_ir']) > threshold]  # default threshold = 0.3

# Stage 2: Correlation redundancy removal (greedy algorithm)
corr_matrix = factor_values.pivot().corr(method='spearman')
for f in sorted(valid, key=lambda x: abs(x['ic_ir']), reverse=True):
    if max(|corr| with any already_selected) > max_correlation:  # default 0.7
        continue  # redundant, skip
    selected.append(f)''')

    pdf.h2('6.4 Weight Calculation')
    pdf.code('''# Default: ic_ir_weighted - weight proportional to |IC_IR|
ic_irs = [abs(f['ic_ir']) for f in selected_factors]
weights = ic_irs / sum(ic_irs)  # normalized to sum = 1.0

# Also available: ic_mean_weighted, equal_weight

# Example output:
# {'volatility_20d': 0.423, 'momentum_5d': 0.301,
#  'momentum_20d': 0.157, 'momentum_1d': 0.120}''')

    pdf.h2('6.5 API Endpoints')
    pdf.code('''POST /api/ml-factor/factors/auto-weight
# 8 parameters, all optional with defaults:
#   evaluation_date, start_date, forward_period, weight_method
#   ic_ir_threshold, max_correlation, min_factors, max_factors

GET  /api/ml-factor/factors/effectiveness?factor_id=&forward_period=&limit=

POST /api/ml-factor/factors/optimize
# Full pipeline: IC analysis + selection + weights''')

    # === 7. Stock Scoring ===
    pdf.h1('7. Stock Scoring Engine')
    pdf.p(
        'StockScoringEngine supports four scoring methods. rank_ic and ml_ensemble were previously '
        'TODO stubs and are now fully implemented with automatic weight fetching.'
    )
    pdf.code('''scoring_methods = {
    'equal_weight':  lambda scores, w: scores.mean(axis=1),
    'factor_weight': lambda scores, w: (scores * normalized(w)).sum(axis=1),
    'rank_ic':       calls FactorOptimizer -> gets IC-optimized weights -> factor_weight,
    'ml_ensemble':   reads model_def.feature_importance -> averages across models -> factor_weight
}''')

    pdf.h2('7.1 Data Flow')
    pdf.code('''FactorValues (DB)
  -> calculate_factor_scores(trade_date, factor_list)
  -> pivot table: rows=ts_code, cols=factor_id, values=z_score
  -> calculate_composite_score(factor_scores, weights, method)
  -> composite_score per stock
  -> rank_stocks(composite_scores, top_n, filters)
  -> top N stocks with basic info (name, industry, area)''')

    # === 8. Backtest Engine ===
    pdf.h1('8. Backtest Engine')
    pdf.p(
        'BacktestEngine supports factor-based and ML-based stock selection with configurable '
        'rebalancing frequency (daily/weekly/monthly/quarterly), transaction cost modeling, and '
        'comprehensive performance metrics.'
    )
    pdf.code('''# Backtest configuration
POST /api/ml-factor/backtest/run
{
    "strategy_config": {
        "selection_method": "factor_based",   # or "ml_based"
        "scoring_method": "rank_ic",           # equal_weight, factor_weight, rank_ic
        "factor_list": [...], "top_n": 20,
        "optimization": {"method": "equal_weight"},
        "transaction_cost": 0.001
    },
    "start_date": "2025-01-03", "end_date": "2026-02-12",
    "initial_capital": 1000000, "rebalance_frequency": "monthly"
}

# Performance metrics returned:
# total_return, annualized_return, sharpe_ratio, max_drawdown
# calmar_ratio, volatility, win_rate
# portfolio_values, daily_returns, daily_positions, daily_turnover''')

    pdf.h2('8.1 Scoring Method Integration')
    pdf.p(
        'When scoring_method="rank_ic", the backtest engine calls _rank_ic_scoring on each rebalance '
        'date. This automatically fetches IC-optimized weights from FactorOptimizer. When the '
        'scoring_method is omitted or "equal_weight", all factors are weighted equally.'
    )

    # === 9. Portfolio Optimization ===
    pdf.h1('9. Portfolio Optimization')
    pdf.p(
        'PortfolioOptimizer uses CVXPY convex optimization and SciPy numerical optimization to solve '
        'for optimal portfolio weights given expected returns and risk constraints.'
    )
    pdf.bullet([
        'Mean-Variance: maximize(expected_return - 0.5 * risk_aversion * variance) via CVXPY ECOS solver',
        'Risk Parity: minimize squared difference from equal risk contribution via scipy.optimize',
        'Equal Weight: simple 1/N allocation',
        'Risk model: Ledoit-Wolf shrinkage estimator for covariance matrix estimation',
        'Factor Neutral and Black-Litterman: TODO stubs, fallback to mean-variance',
    ])

    # === 10. Realtime Analysis ===
    pdf.h1('10. Real-time Analysis System')
    pdf.p(
        'The real-time module uses Flask-SocketIO + eventlet for WebSocket streaming of minute-level '
        'market data, technical indicators, trading signals, and risk alerts.'
    )
    pdf.bullet([
        'Data: stock_minute_data table (5/15/30/60 min K-lines) via Tushare stk_mins API',
        'Indicator Engine: computes 20+ real-time technical indicators',
        'Signal Engine: generates buy/sell signals based on indicator crossovers',
        'Risk Manager: monitors position risk, stop-loss, and VaR',
        'Monitor Dashboard: WebSocket push of real-time metrics to browser',
        'Report Generator: automated daily/weekly analysis reports',
    ])

    # === 11. Text2SQL ===
    pdf.h1('11. Text2SQL Natural Language Query')
    pdf.p(
        'The Text2SQL module converts Chinese natural language queries into SQL using jieba word '
        'segmentation and LLM-powered schema understanding.'
    )
    pdf.code('''# Query pipeline
User query: "show me stocks with PE < 15 and ROE > 10%"
  -> NLP Processor (jieba tokenization + entity extraction)
  -> SQL Generator (LLM + table metadata + query templates)
  -> "SELECT * FROM stock_daily_basic WHERE pe_ttm < 15 AND roe_ttm > 10"
  -> Execute against MySQL -> Return results

# Components:
# nlp_processor.py: Chinese word segmentation, entity recognition
# llm_service.py: OpenAI-compatible API integration (Aliyun DashScope qwen-coder by default)
# sql_generator.py: Template-based SQL generation with LLM refinement
# text2sql_engine.py: Orchestration of the full pipeline''')

    # === 12. Data Sources ===
    pdf.h1('12. Data Sources & Pipeline')
    pdf.h2('12.1 Available Sources')
    pdf.bullet([
        'Tushare (tushare.pro): API token required, supports stock_basic, daily, stk_mins, moneyflow',
        'Baostock (baostock.com): Free, no token, Python 3.13 compatible',
        'akshare (HTTP): Wraps public web sources (Sina, EastMoney), IP rate-limited',
        'SQL Dumps: Pre-loaded MySQL dumps covering 2025-01 ~ 2026-02 (8 tables, 300MB+)',
    ])

    pdf.h2('12.2 Data Pipeline')
    pdf.code('''# Data import flow
SQL dumps (stock_data/*.sql)
  -> mysql < file.sql (DROP TABLE + CREATE + INSERT)
  -> Python fast_import.py (batch INSERT 10k rows/transaction, 20x faster)

# Factor calculation flow
stock_daily_history (1.47M rows)
  -> scripts/calculate_factors.py
  -> 6 technical factors x 272 trading days
  -> factor_values (8.37M rows)

# IC analysis flow
factor_values + stock_daily_history
  -> FactorOptimizer.analyze_all_factors()
  -> factor_effectiveness (IC stats per factor per period)
  -> auto-weight API endpoint''')

    # === 13. Frontend ===
    pdf.h1('13. Frontend Pages')
    pdf.bullet([
        '/ml-factor: Factor management dashboard (list, create, calculate custom factors)',
        '/ml-factor/scoring: Stock scoring (factor-based, ML-based, portfolio integrated)',
        '/ml-factor/models: ML model management (create, train, predict, evaluate)',
        '/ml-factor/portfolio: Portfolio optimization and rebalancing',
        '/ml-factor/analysis: Factor contribution and sector analysis reports',
        '/ml-factor/backtest: Backtest configuration with scoring method selector, auto-weight preview, and results visualization',
        '/ml-factor/optimization: Factor optimization workflow (IC analysis -> weights -> backtest comparison)',
        'Real-time analysis pages: monitor dashboard, indicators, signals, risk, reports',
    ])
    pdf.p(
        'All pages use Jinja2 template inheritance from base.html, Bootstrap 5.1 with custom '
        'financial theme CSS, ECharts for interactive charts, and Axios for AJAX API calls. '
        'The layout follows container > row > column with metric cards, data tables, and modals.'
    )

    # === 14. API Index ===
    pdf.h1('14. Complete API Index')
    pdf.code('''GET  /api/ml-factor/factors/list              # List all factors
POST /api/ml-factor/factors/calculate           # Calculate factor values
POST /api/ml-factor/factors/custom              # Create custom factor
POST /api/ml-factor/factors/optimize            # Full factor optimization   [NEW]
GET  /api/ml-factor/factors/effectiveness       # IC effectiveness report    [NEW]
POST /api/ml-factor/factors/auto-weight         # Auto-compute optimal weights [NEW]
POST /api/ml-factor/models/create               # Create ML model
POST /api/ml-factor/models/train                # Train model
POST /api/ml-factor/models/predict              # Predict with model
POST /api/ml-factor/models/evaluate             # Evaluate model
GET  /api/ml-factor/models/list                 # List all models
POST /api/ml-factor/scoring/factor-based        # Factor-based stock scoring
POST /api/ml-factor/scoring/ml-based            # ML-based stock scoring
POST /api/ml-factor/analysis/factor-contribution # Factor contribution analysis
POST /api/ml-factor/analysis/sector             # Sector analysis
POST /api/ml-factor/batch/calculate-and-score   # Batch: calculate + score
POST /api/ml-factor/batch/train-and-predict     # Batch: train + predict
POST /api/ml-factor/portfolio/optimize          # Portfolio optimization
POST /api/ml-factor/portfolio/rebalance         # Portfolio rebalancing
POST /api/ml-factor/portfolio/integrated-selection # Integrated selection + optimization
POST /api/ml-factor/backtest/run                # Run backtest
POST /api/ml-factor/backtest/compare            # Compare multiple strategies''')

    return pdf


def pdf2_algorithms():
    """PDF2: Core Algorithms & Data Flow"""
    pdf = DocPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(True, 20)

    # === Cover ===
    pdf.add_page()
    pdf.ln(30)
    pdf.set_font('Courier', 'B', 24)
    pdf.set_text_color(0, 40, 90)
    pdf.cell(0, 14, 'Multi-Factor Stock', 0, 1, 'C')
    pdf.cell(0, 14, 'Selection System', 0, 1, 'C')
    pdf.ln(6)
    pdf.set_font('Courier', '', 12)
    pdf.set_text_color(60, 60, 60)
    pdf.cell(0, 8, 'Core Algorithms & Data Flow', 0, 1, 'C')
    pdf.ln(20)
    pdf.set_font('Courier', '', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, 'Rank IC Analysis - Factor Optimization - Backtesting', 0, 1, 'C')
    pdf.cell(0, 6, 'Stock Scoring - ML Training - Portfolio Construction', 0, 1, 'C')

    # === 1. End-to-End Data Flow ===
    pdf.add_page()
    pdf.section_title('1. End-to-End Data Flow')
    pdf.p(
        'The complete pipeline from raw market data to backtest results:'
    )
    pdf.p(
        '[1] DATA ACQUISITION\n'
        '    Tushare/Baostock/SQL dumps -> stock_daily_history (1.47M), stock_daily_basic (376K),\n'
        '    stock_factor (1.13M), stock_moneyflow (459K), stock_cyq_perf (218K)\n\n'
        '[2] FACTOR COMPUTATION (scripts/calculate_factors.py)\n'
        '    Price data -> pandas vectorized ops -> 6 technical factors\n'
        '    factor_values: 8.37M rows, 272 trading days, 5,473 stocks\n\n'
        '[3] FACTOR OPTIMIZATION (FactorOptimizer)\n'
        '    factor_values + prices -> Rank IC (Spearman) -> Rolling IC stats (IC_mean,\n'
        '    IC_IR, win_rate) -> Factor selection (threshold + redundancy) -> Weight\n'
        '    calculation (|IC_IR| proportional) -> factor_effectiveness table\n\n'
        '[4] STOCK SCORING (StockScoringEngine)\n'
        '    factor_values + optimized_weights -> composite_score per stock\n'
        '    -> rank_stocks -> Top N stocks with basic info\n\n'
        '[5] BACKTEST (BacktestEngine)\n'
        '    Monthly rebalance -> select -> optimize -> execute -> track P&L\n'
        '    -> metrics (total_return, sharpe, max_drawdown, win_rate, calmar_ratio)'
    )

    # === 2. Rank IC Deep Dive ===
    pdf.h1('2. Rank IC Algorithm Deep Dive')

    pdf.h2('2.1 Mathematical Definition')
    pdf.p(
        'Rank IC(t, f, N) = SpearmanRho( f_value(t), forward_return(t, t+N) )\n\n'
        'Where:\n'
        '  f_value(t) = cross-sectional factor values for all stocks on date t\n'
        '  forward_return(t, t+N) = (close(t+N) - close(t)) / close(t) for each stock\n'
        '  SpearmanRho = Pearson correlation on rank-transformed data\n\n'
        'Spearman is used instead of Pearson because stock factor values and returns are '
        'typically non-normally distributed. Rank-based correlation is distribution-free '
        'and robust to outliers.'
    )

    pdf.h2('2.2 Single-Day IC Computation (Vectorized)')
    pdf.code('''# Step 1: Get factor exposure for ALL stocks on date T
factor_df = factor_engine.get_factor_exposure(factor_id, trade_date)
# Returns DataFrame: ts_code, factor_value, z_score, percentile_rank

# Step 2: Get current close prices (single query, 5473 rows)
current_data = pd.read_sql(
    StockDailyHistory.query.filter(trade_date == trade_dt).statement, db.engine)

# Step 3: Get future prices (single query, all future data)
price_data = pd.read_sql(
    StockDailyHistory.query.filter(trade_date > trade_dt).statement, db.engine)

# Step 4: For each stock, get the forward_period-th future close
# Using pandas groupby.cumcount for vectorized indexing (avoids per-stock loop)
position_counts = price_data.groupby('ts_code').cumcount()
future_prices = price_data[position_counts == (forward_period - 1)][['ts_code', 'close']]

# Step 5: Merge and compute
merged = pd.merge(current_data[['ts_code','close']], future_prices, on='ts_code')
merged['forward_return'] = (merged['close_y'] - merged['close_x']) / merged['close_x']

# Step 6: Spearman rank correlation
final = pd.merge(factor_df[['ts_code','factor_value']], merged[['ts_code','forward_return']])
ic, p_value = spearmanr(final['factor_value'], final['forward_return'])''')

    pdf.h2('2.3 Rolling Statistics Aggregation')
    pdf.p(
        'Once single-day ICs are computed for all dates in the evaluation window:\n\n'
        '  IC_mean = (1/n) * sum(IC_i)              # Average prediction ability\n'
        '  IC_std  = sqrt((1/(n-1)) * sum(IC_i - IC_mean)^2)  # Stability\n'
        '  IC_IR   = IC_mean / IC_std               # Information Ratio\n'
        '  IC_win_rate = count(IC_i > 0) / n        # Consistency\n\n'
        'IC_IR is the primary metric because it captures both magnitude and consistency. '
        'A factor with IC_mean=0.05 and IC_std=0.02 (IC_IR=2.5) is preferred over one with '
        'IC_mean=0.10 and IC_std=0.10 (IC_IR=1.0) despite the latter having higher average IC.'
    )

    # === 3. Factor Selection Algorithm ===
    pdf.h1('3. Factor Selection Algorithm')
    pdf.h2('3.1 Stage 1: IC_IR Threshold')
    pdf.code('''threshold = 0.3  # default, user-configurable
valid_factors = []
for f in all_factors:
    if f.ic_ir is not None and abs(f.ic_ir) > threshold:
        valid_factors.append(f)

# If too few factors pass, relax threshold and take top N
if len(valid_factors) < min_factors:
    valid_factors = sorted(all_factors, key=abs(ic_ir))[-max(min_factors, max_factors):]''')

    pdf.h2('3.2 Stage 2: Correlation Redundancy Removal')
    pdf.code('''# Compute cross-sectional factor correlation matrix
pivot = factor_values.pivot(index='ts_code', columns='factor_id', values='factor_value')
corr_matrix = pivot.corr(method='spearman')

# Greedy selection: pick highest |IC_IR| first, skip correlated
selected = []
for f in sorted(valid_factors, key=lambda x: abs(x.ic_ir), reverse=True):
    redundant = False
    for s in selected:
        if abs(corr_matrix.loc[s.id, f.id]) > max_correlation:
            redundant = True; break
    if not redundant:
        selected.append(f)''')

    pdf.h2('3.3 Weight Methods')
    pdf.bullet([
        'ic_ir_weighted (default): weight_i = |IC_IR_i| / sum(|IC_IR_j|). Favors stable predictive factors.',
        'ic_mean_weighted: weight_i = |IC_mean_i| / sum(|IC_mean_j|). Favors strong raw signal.',
        'equal_weight: weight_i = 1/n. Useful as baseline comparison.',
        'Weights always normalized to sum=1.0. Factors with IC near zero get near-zero weight.',
    ])

    # === 4. Stock Scoring Pipeline ===
    pdf.h1('4. Stock Scoring Pipeline')
    pdf.code('''# 1. Load factor Z-scores for trade_date
factor_scores = pd.pivot_table(
    FactorValues.query.filter(trade_date=T, factor_id in factor_list),
    index='ts_code', columns='factor_id', values='z_score'
).fillna(0)  # shape: (5473 stocks, N factors)

# 2. Apply weights via scoring method
if method == 'rank_ic':
    weights = FactorOptimizer.get_optimized_weights(evaluation_date=T)
else:
    weights = user_provided or equal_weights

composite_scores = (factor_scores * weights).sum(axis=1)

# 3. Rank and select top N
result = composite_scores.sort_values(ascending=False).head(top_n)

# 4. Enrich with stock info (name, industry, area)
stock_info = StockBasic.query.filter(ts_code in result.index)''')

    # === 5. Backtest Algorithm ===
    pdf.h1('5. Backtest Algorithm')
    pdf.code('''# Monthly rebalance backtest
positions, cash, portfolio_values = {}, initial_capital, []

for trade_date in monthly_dates(start, end):
    # 1. Select stocks for this rebalance date
    selected = scoring_engine.calculate_factor_scores(trade_date, factor_list)
    composite = scoring_engine.calculate_composite_score(selected, weights, method)
    top_stocks = scoring_engine.rank_stocks(composite, top_n)
    target_weights = optimizer.optimize_portfolio(expected_returns)

    # 2. Get current prices for holdings + targets
    prices = get_current_prices(trade_date, positions.keys() | target_weights.keys())

    # 3. Calculate current portfolio value
    current_value = sum(positions[s] * prices[s] for s in positions) + cash

    # 4. Execute rebalance with transaction costs
    new_positions, new_cash, turnover = rebalance(
        positions, cash, target_weights, prices, current_value, tx_cost
    )

    # 5. Record portfolio value
    positions, cash = new_positions, new_cash
    portfolio_values.append({'date': trade_date, 'total_value': current_value})

# 6. Compute performance metrics
daily_returns = [(pv[i+1].total_value / pv[i].total_value - 1) for i in range(len(pv)-1)]
total_return = (portfolio_values[-1].total_value / initial_capital) - 1
annualized_return = (1 + total_return) ^ (252 / len(daily_returns)) - 1
sharpe_ratio = mean(daily_returns) / std(daily_returns) * sqrt(252)
max_drawdown = min(cumulative_min / cumulative_max - 1)
calmar_ratio = annualized_return / |max_drawdown|
win_rate = count(daily_returns > 0) / len(daily_returns)''')

    # === 6. ML Training Pipeline ===
    pdf.h1('6. ML Model Training Pipeline')
    pdf.code('''# 1. Prepare training data
factor_data = pd.pivot_table(
    FactorValues.query.filter(factor_id in model_def.factor_list,
                               trade_date between start and end),
    index=['ts_code', 'trade_date'], columns='factor_id', values='factor_value'
)
# Compute target: forward N-day return
target = calculate_forward_returns(factor_data, model_def.target_type)  # return_5d, return_20d

# 2. Feature engineering
X = RobustScaler().fit_transform(factor_data[model_def.factor_list])
if feature_selection_enabled:
    X, selected = SelectKBest(f_regression, k=min(k, n_features)).fit_transform(X, y)

# 3. Time-series split (preserve temporal order, no shuffle)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, shuffle=False)

# 4. Train and evaluate
model = RandomForestRegressor(n_estimators=100, max_depth=10, n_jobs=-1)
model.fit(X_train, y_train)

# 5. Cross-validation with TimeSeriesSplit
tscv = TimeSeriesSplit(n_splits=5)
cv_scores = cross_val_score(model, X, y, cv=tscv, scoring='r2')

# 6. Persist model and feature importance
joblib.dump(model, f'models/{model_id}.pkl')
model_def.feature_importance = dict(zip(features, model.feature_importances_))
db.session.commit()''')

    # === 7. Portfolio Optimization ===
    pdf.h1('7. Portfolio Optimization Algorithms')
    pdf.code('''# Mean-Variance Optimization (CVXPY)
w = cp.Variable(n)
expected_return = mu @ w
risk = cp.quad_form(w, Sigma)
objective = cp.Maximize(expected_return - 0.5 * risk_aversion * risk)
constraints = [cp.sum(w) == 1, w >= 0]  # long-only, fully invested
problem = cp.Problem(objective, constraints)
problem.solve(solver='ECOS')

# Risk Parity (SciPy)
def risk_parity_objective(w):
    portfolio_vol = sqrt(w.T @ Sigma @ w)
    marginal_risk = Sigma @ w
    risk_contrib = w * marginal_risk / portfolio_vol
    target_contrib = portfolio_vol / n  # equal risk contribution
    return sum((risk_contrib - target_contrib)**2)

result = minimize(risk_parity_objective, x0=ones(n)/n,
                  constraints={'type': 'eq', 'fun': lambda x: sum(x)-1},
                  bounds=[(0,1)]*n)''')

    # === 8. Performance Metrics ===
    pdf.h1('8. Performance Metrics Reference')
    pdf.bullet([
        'Total Return: (final_value / initial_capital) - 1',
        'Annualized Return: (1 + total_return)^(252/trading_days) - 1',
        'Sharpe Ratio: mean(daily_returns) / std(daily_returns) * sqrt(252)',
        'Max Drawdown: max peak-to-trough decline in portfolio value',
        'Calmar Ratio: annualized_return / |max_drawdown|',
        'Volatility: std(daily_returns) * sqrt(252) (annualized)',
        'Win Rate: percentage of rebalance periods with positive returns',
        'Turnover: percentage of portfolio value traded each rebalance',
    ])

    # === 9. IC Analysis Case Study ===
    pdf.h1('9. IC Analysis - Real Data Results')
    pdf.p('Analysis period: 2025-01-03 ~ 2025-04-15, 66 trading days, 6 technical factors:')
    pdf.code('''Factor               IC_mean     IC_IR    WinRate    Weight     Selected?
volatility_20d       -0.1566    -0.64     29%       42.3%      YES
momentum_5d          -0.0533    -0.45     26%       30.1%      YES
momentum_20d         -0.0376    -0.24     39%       15.7%      YES
momentum_1d          -0.0289    -0.18     40%       12.0%      YES
volume_ratio_20d     -0.0015    -0.02     50%       0%         NO (IC_IR too low)
price_to_ma20        -0.0115    -0.16     47%       0%         NO (redundant with momentum)

Key finding: All factors showed NEGATIVE IC in this period, indicating a mean-reversion
market. The optimization engine correctly identified volatility_20d as the strongest
predictor and assigned it the highest weight (42.3%).''')

    # === 10. Backtest Real-Data Results ===
    pdf.h1('10. Backtest Results (Real Data)')
    pdf.p('Full period backtest: 2025-01-03 ~ 2026-02-12, 14 monthly rebalances, 20-stock portfolio:')
    pdf.code('''Total Return:     +2.96%
Annualized Return: +2.66%
Sharpe Ratio:      -0.003
Max Drawdown:      -23.2% (March-April 2025 crash)
Win Rate:          53.8% (7/14 months positive)
Calmar Ratio:      0.11

Monthly Performance:
  Jan 2025:   998k   Feb:   986k   Mar: 1,140k (+15.6%, best)
  Apr:        931k   May:   875k   Jun:   928k
  Jul:        934k   Aug:   940k   Sep: 1,027k
  Oct:      1,090k   Nov: 1,112k   Dec: 1,097k
  Jan 2026: 1,046k   Feb: 1,030k

Notes:
- Look-ahead bias exists: all months use the same global IC weights
- Early months (Jan-Feb) have incomplete factor data (1-2 factors only)
- 23% max drawdown suggests excessive exposure to small-cap volatile stocks
- Strategy needs more factor types (fundamental, money flow) for diversification''')

    # === 11. Configuration ===
    pdf.h1('11. System Configuration')
    pdf.code('''# config.py - Key settings
class Config:
    SECRET_KEY = 'dev-secret-key'
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://root:123456@localhost/stock_cursor'
    REDIS_URL = 'redis://localhost:6379/0'

# Database: MySQL 8.0 (stock_cursor)
# Redis: localhost:6379 (cache and message queue)
# LLM: OpenAI-compatible API, default Aliyun DashScope qwen-coder-turbo
# WebSocket: eventlet async mode, port 5001
# Logging: loguru -> logs/stock_analysis.log''')

    # === 12. Startup & Deployment ===
    pdf.h1('12. Startup & Deployment')
    pdf.code('''# Development startup
python run.py                  # Flask dev server on port 5001
python run_system.py           # Interactive system manager (check deps, init DB, start)

# Data import
mysql -uroot -p < stock_data/stock_basic.sql
mysql -uroot -p < stock_data/stock_daily_history.sql   # 336MB
# ... (8 SQL files total)
python scripts/fast_import.py  # Optimized batch import (10k rows/txn)

# Factor computation
python scripts/calculate_factors.py  # 272 days x 6 factors -> 8.37M rows

# Factor optimization (via API or direct)
POST /api/ml-factor/factors/optimize
# or: FactorOptimizer.get_optimized_weights(evaluation_date)

# Backtest (via API or UI)
POST /api/ml-factor/backtest/run
# or: http://127.0.0.1:5001/ml-factor/backtest''')

    return pdf


# Generate
if __name__ == '__main__':
    out = f'{project_root}/pdf'

    p1 = pdf1_system_architecture()
    p1.output(f'{out}/System Architecture and API Reference.pdf')
    print('Created: System Architecture and API Reference.pdf')

    p2 = pdf2_algorithms()
    p2.output(f'{out}/Core Algorithms and Data Flow.pdf')
    print('Created: Core Algorithms and Data Flow.pdf')

import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from loguru import logger
import warnings
warnings.filterwarnings('ignore')

from app.extensions import db
from app.models import StockDailyHistory, FactorValues, MLPredictions
from app.services.factor_engine import FactorEngine
from app.services.ml_models import MLModelManager
from app.services.stock_scoring import StockScoringEngine
from app.services.portfolio_optimizer import PortfolioOptimizer


class BacktestEngine:
    """回测验证引擎"""
    
    def __init__(self):
        self.factor_engine = None
        self.ml_manager = None
        self.scoring_engine = None
        self.portfolio_optimizer = None
        self._price_batch = None  # {(trade_date_str, ts_code): close}
        self._price_batch_start = None
        self._price_batch_end = None
        self._predictions_batch = None  # pre-loaded ML predictions DataFrame
        self._pred_batch_start = None
        self._pred_batch_end = None
        self._pred_batch_model_ids = None
        self._factor_values_batch = None  # pre-loaded factor values DataFrame
        self._fv_batch_start = None
        self._fv_batch_end = None
        self._factor_scores_cache = {}  # {trade_date: factor_scores DataFrame}
        self._factor_directions = {}  # {factor_id: 'positive'/'negative'}
        self._stock_info_cache = {}  # {ts_code: stock_info_dict}
    
    def _get_factor_engine(self):
        """延迟初始化因子引擎"""
        if self.factor_engine is None:
            self.factor_engine = FactorEngine()
        return self.factor_engine
    
    def _get_ml_manager(self):
        """延迟初始化ML管理器"""
        if self.ml_manager is None:
            self.ml_manager = MLModelManager()
        return self.ml_manager
    
    def _get_scoring_engine(self):
        """延迟初始化评分引擎"""
        if self.scoring_engine is None:
            self.scoring_engine = StockScoringEngine()
        return self.scoring_engine
    
    def _get_portfolio_optimizer(self):
        """延迟初始化投资组合优化器"""
        if self.portfolio_optimizer is None:
            self.portfolio_optimizer = PortfolioOptimizer()
        return self.portfolio_optimizer
        
    def run_backtest(self, strategy_config: Dict[str, Any], 
                    start_date: str, end_date: str,
                    initial_capital: float = 1000000.0,
                    rebalance_frequency: str = 'monthly') -> Dict[str, Any]:
        """
        运行回测
        
        Args:
            strategy_config: 策略配置
            start_date: 开始日期
            end_date: 结束日期
            initial_capital: 初始资金
            rebalance_frequency: 再平衡频率 ('daily', 'weekly', 'monthly')
            
        Returns:
            回测结果
        """
        try:
            logger.info(f"开始回测: {start_date} to {end_date}")

            # 批量预加载数据，消除逐日查询
            self._batch_warm_prices(start_date, end_date)
            self._warm_stock_info()
            selection_method = strategy_config.get('selection_method', 'factor_based')
            has_factor = bool(strategy_config.get('factor_list'))
            has_model = bool(self._extract_model_ids(strategy_config))
            if selection_method in ('ml_based', 'hybrid') and has_model:
                model_ids = self._extract_model_ids(strategy_config)
                self._batch_warm_predictions(model_ids, start_date, end_date)
            if selection_method in ('factor_based', 'hybrid') and has_factor:
                self._batch_warm_factor_values(start_date, end_date)

            # 预计算 IC 权重（rank_ic 模式只算一次，避免每日期重复调用 FactorOptimizer）
            scoring_method = strategy_config.get('scoring_method', '')
            if scoring_method == 'rank_ic' and strategy_config.get('factor_list'):
                try:
                    from app.services.factor_optimizer import FactorOptimizer
                    opt = FactorOptimizer()
                    ic_result = opt.get_optimized_weights(
                        evaluation_date=end_date, start_date=start_date,
                        forward_period=5, method='ic_ir_weighted',
                        ic_ir_threshold=0.1, min_factors=2, max_factors=8
                    )
                    if ic_result.get('weights'):
                        strategy_config = dict(strategy_config)
                        strategy_config['weights'] = ic_result['weights']
                        strategy_config['scoring_method'] = 'factor_weight'
                        logger.info('IC weights pre-computed for backtest: {}'.format(
                            len(ic_result['weights'])))
                except Exception as e:
                    logger.warning(f'IC weight pre-compute failed: {e}')

            # 生成交易日期（调仓日）
            trade_dates = self._generate_trade_dates(start_date, end_date, rebalance_frequency)

            # 预计算调仓日的因子分数（消除逐日 pandas 过滤）
            if self._factor_values_batch is not None and strategy_config.get('factor_list'):
                use_factors = strategy_config['factor_list']
                scoring = self._get_scoring_engine()
                wt = strategy_config.get('weights') or strategy_config.get('factor_weights') or {}
                sm = strategy_config.get('scoring_method', 'equal_weight')

                # 获取因子方向（IC符号），修正负向因子
                self._factor_directions = {}
                from app.models import FactorEffectiveness
                eff_rows = db.session.query(
                    FactorEffectiveness.factor_id, FactorEffectiveness.factor_direction
                ).filter(FactorEffectiveness.factor_id.in_(use_factors)).distinct().all()
                for r in eff_rows:
                    if r[1]:
                        self._factor_directions[r[0]] = r[1]

                self._factor_scores_cache.clear()
                for d_str in trade_dates:
                    fs = scoring.calculate_factor_scores(d_str, use_factors,
                                                         factor_values_batch=self._factor_values_batch)
                    if not fs.empty:
                        comp = scoring.calculate_composite_score(
                            fs, wt, sm, factor_directions=self._factor_directions
                        )
                        if not comp.empty:
                            self._factor_scores_cache[d_str] = comp
                logger.info('Factor scores pre-computed for {} rebalance dates'.format(
                    len(self._factor_scores_cache)))

            # 初始化回测状态
            portfolio_values = []
            positions = {}
            cash = initial_capital
            total_value = initial_capital

            # 记录每日数据
            daily_returns = []
            daily_positions = []
            daily_turnover = []

            for i, trade_date in enumerate(trade_dates):
                logger.info(f"处理交易日: {trade_date}")
                
                try:
                    # 获取当日选股结果
                    selected_stocks = self._get_stock_selection(strategy_config, trade_date, start_date)
                    
                    if not selected_stocks:
                        logger.warning(f"日期 {trade_date} 没有选出股票")
                        continue
                    
                    # 组合优化
                    target_weights = self._get_target_weights(
                        selected_stocks, strategy_config.get('optimization', {})
                    )
                    
                    # 取价必须包含：当前持仓 + 本期目标持仓，否则首调仓 positions 为空时无法拿到新买入股票的收盘价
                    price_ts_codes = list(set(positions.keys()) | set(target_weights.keys()))
                    current_prices = self._get_batch_prices(trade_date, price_ts_codes)
                    
                    # 再平衡前组合市值（用于下单金额）
                    current_portfolio_value = self._calculate_portfolio_value(
                        positions, current_prices, cash
                    )
                    
                    # 执行再平衡
                    new_positions, new_cash, turnover = self._rebalance_portfolio(
                        positions, cash, target_weights, current_prices, 
                        current_portfolio_value, strategy_config.get('transaction_cost', 0.001)
                    )
                    
                    # 更新状态；记录再平衡后的真实净值
                    positions = new_positions
                    cash = new_cash
                    total_value = self._calculate_portfolio_value(
                        new_positions, current_prices, new_cash
                    )
                    
                    # 调仓区间收益：在写入本期净值前取上一期，避免与 trade_dates 下标错位
                    if len(portfolio_values) > 0:
                        prev_tv = portfolio_values[-1]['total_value']
                        if prev_tv and prev_tv > 0:
                            daily_returns.append((total_value - prev_tv) / prev_tv)
                        else:
                            daily_returns.append(0.0)
                    
                    portfolio_values.append({
                        'date': trade_date,
                        'total_value': total_value,
                        'cash': cash,
                        'positions_value': total_value - cash
                    })
                    
                    daily_positions.append(positions.copy())
                    daily_turnover.append(turnover)
                    
                except Exception as e:
                    logger.error(f"处理交易日 {trade_date} 时出错: {e}")
                    continue
            
            # 无任何成功调仓时不视为成功回测
            if not portfolio_values:
                return {
                    'success': False,
                    'error': '回测区间内未能完成任何一次有效调仓（无选股结果、因子/预测数据不足或行情缺失）',
                    'strategy_config': strategy_config,
                    'backtest_period': f"{start_date} to {end_date}",
                    'initial_capital': initial_capital,
                    'final_value': initial_capital,
                    'total_return': 0.0,
                    'portfolio_values': [],
                    'daily_returns': [],
                    'daily_positions': [],
                    'daily_turnover': [],
                    'performance_metrics': {},
                    'benchmark_returns': {}
                }
            
            # 计算回测指标（与顶层 total_return 统一以 initial_capital 为分母）
            performance_metrics = self._calculate_performance_metrics(
                portfolio_values, daily_returns, start_date, end_date,
                initial_capital=initial_capital
            )
            
            # 获取基准收益（与策略调仓日对齐）
            benchmark_returns = self._get_benchmark_returns(
                start_date, end_date, portfolio_values=portfolio_values
            )

            # 超额收益 & 信息比率
            bench_total = benchmark_returns.get('total_return', 0) if isinstance(benchmark_returns, dict) else 0
            excess_return = performance_metrics.get('total_return', 0) - bench_total
            strategy_annual = performance_metrics.get('annualized_return', 0)
            bench_annual = benchmark_returns.get('annualized_return', 0) if isinstance(benchmark_returns, dict) else 0
            excess_annual = strategy_annual - bench_annual

            aligned = benchmark_returns.get('aligned_returns', []) if isinstance(benchmark_returns, dict) else []
            if len(aligned) >= 2 and len(daily_returns) >= len(aligned) - 1:
                bench_period_rets = [(aligned[i+1]['value'] - aligned[i]['value'])
                                     / (1 + aligned[i]['value'])
                                     for i in range(len(aligned) - 1)]
                if len(bench_period_rets) == len(daily_returns):
                    tracking_errors = [daily_returns[i] - bench_period_rets[i]
                                       for i in range(len(daily_returns))]
                    days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                    years = max(days / 365.25, 0.01)
                    periods_per_year = len(daily_returns) / years
                    annual_factor = np.sqrt(max(periods_per_year, 1))
                    te = float(np.std(tracking_errors) * annual_factor)
                    info_ratio = (excess_annual / te) if te > 0 else 0.0
                else:
                    te = info_ratio = 0.0
            else:
                te = info_ratio = 0.0

            performance_metrics['excess_return'] = excess_return
            performance_metrics['excess_annual'] = excess_annual
            performance_metrics['benchmark_return'] = bench_total
            performance_metrics['benchmark_annual'] = bench_annual
            performance_metrics['benchmark_volatility'] = benchmark_returns.get('volatility', 0.0) if isinstance(benchmark_returns, dict) else 0.0
            performance_metrics['benchmark_max_dd'] = benchmark_returns.get('max_drawdown', 0.0) if isinstance(benchmark_returns, dict) else 0.0
            performance_metrics['tracking_error'] = te
            performance_metrics['information_ratio'] = info_ratio

            return {
                'success': True,
                'strategy_config': strategy_config,
                'backtest_period': f"{start_date} to {end_date}",
                'initial_capital': initial_capital,
                'final_value': total_value,
                'total_return': (total_value - initial_capital) / initial_capital if initial_capital > 0 else 0.0,
                'portfolio_values': portfolio_values,
                'daily_returns': daily_returns,
                'daily_positions': daily_positions,
                'daily_turnover': daily_turnover,
                'performance_metrics': performance_metrics,
                'benchmark_returns': benchmark_returns
            }
            
        except Exception as e:
            logger.error(f"回测失败: {e}")
            return {'error': str(e)}
    
    def _generate_trade_dates(self, start_date: str, end_date: str, 
                            frequency: str) -> List[str]:
        """生成交易日期"""
        try:
            # 获取所有交易日
            query = db.session.query(StockDailyHistory.trade_date).distinct()
            query = query.filter(
                StockDailyHistory.trade_date >= start_date,
                StockDailyHistory.trade_date <= end_date
            )
            all_dates = [row[0] for row in query.order_by(StockDailyHistory.trade_date)]
            
            if frequency == 'daily':
                return all_dates
            elif frequency == 'weekly':
                # 每周第一个交易日
                weekly_dates = []
                current_week = None
                for date in all_dates:
                    week = pd.to_datetime(date).isocalendar()[1]
                    if week != current_week:
                        weekly_dates.append(date)
                        current_week = week
                return weekly_dates
            elif frequency == 'monthly':
                # 每月第一个交易日
                monthly_dates = []
                current_month = None
                for date in all_dates:
                    month = pd.to_datetime(date).month
                    if month != current_month:
                        monthly_dates.append(date)
                        current_month = month
                return monthly_dates
            elif frequency == 'quarterly':
                # 每季度第一个交易日 (按自然季)
                quarterly_dates = []
                current_quarter_key = None
                for date in all_dates:
                    dt = pd.to_datetime(date)
                    qk = (dt.year, (dt.month - 1) // 3)
                    if qk != current_quarter_key:
                        quarterly_dates.append(date)
                        current_quarter_key = qk
                return quarterly_dates
            else:
                # 未知频率时按日回测，避免静默误用
                logger.warning(f"未知再平衡频率 '{frequency}'，按 daily 处理")
                return all_dates
                
        except Exception as e:
            logger.error(f"生成交易日期失败: {e}")
            return []
    
    def _extract_model_ids(self, strategy_config: dict) -> list:
        """兼容 model_id/model_ids 两种入参格式。"""
        model_ids = strategy_config.get('model_ids')
        if not model_ids:
            single = strategy_config.get('model_id')
            model_ids = [single] if single is not None else []
        elif not isinstance(model_ids, list):
            model_ids = [model_ids]
        normalized = []
        seen = set()
        for mid in model_ids:
            if mid is None:
                continue
            mid_str = str(mid).strip()
            if not mid_str or mid_str in seen:
                continue
            normalized.append(mid_str)
            seen.add(mid_str)
        return normalized

    def _get_stock_selection(self, strategy_config: Dict[str, Any],
                           trade_date: str, start_date: str = None) -> List[Dict[str, Any]]:
        """获取股票选择结果"""
        try:
            selection_method = strategy_config.get('selection_method', 'factor_based')
            top_n = strategy_config.get('top_n', 50)
            
            if selection_method == 'ml_based':
                model_ids = self._extract_model_ids(strategy_config)
                if not model_ids:
                    return []

                selected = self._get_scoring_engine().ml_based_selection(
                    trade_date, model_ids, top_n, 'average',
                    predictions_batch=self._predictions_batch
                )
                if selected:
                    return selected

                if not strategy_config.get('enable_live_scoring_fallback', True):
                    logger.warning(f"日期 {trade_date} 预计算预测缺失，且已禁用现场打分回退")
                    return []

                logger.info(f"日期 {trade_date} 预计算预测缺失，尝试现场打分")
                return self._get_live_ml_selection(trade_date, model_ids, top_n)

            elif selection_method == 'hybrid':
                factor_list = strategy_config.get('factor_list', [])
                model_ids = self._extract_model_ids(strategy_config)
                if not model_ids or not factor_list:
                    logger.warning("混合方法需要同时提供 model_ids 和 factor_list")
                    return []

                weights_config = strategy_config.get('weights') or strategy_config.get('factor_weights') or {}
                if weights_config:
                    weights_config = {k: float(v) for k, v in weights_config.items()}

                scoring_method = strategy_config.get('scoring_method', 'rank_ic')
                blend_weight = strategy_config.get('blend_weight')

                return self._get_scoring_engine().hybrid_selection(
                    trade_date, factor_list, model_ids, top_n,
                    blend_weight=blend_weight,
                    factor_scoring_method=scoring_method,
                    factor_scoring_weights=weights_config,
                    ensemble_method='average',
                    predictions_batch=self._predictions_batch,
                    factor_values_batch=self._factor_values_batch,
                    start_date=start_date
                )

            else:
                factor_list = strategy_config.get('factor_list', [])
                if not factor_list:
                    return []

                # 优先使用预计算的综合分数
                composite_scores = self._factor_scores_cache.get(trade_date)
                if composite_scores is None:
                    factor_scores = self._get_scoring_engine().calculate_factor_scores(
                        trade_date, factor_list,
                        factor_values_batch=self._factor_values_batch
                    )
                    if factor_scores.empty:
                        return []
                    scoring_method = strategy_config.get('scoring_method', '')
                    weights_config = strategy_config.get('weights') or strategy_config.get('factor_weights') or {}
                    if weights_config:
                        weights_config = {
                            k: float(v) for k, v in weights_config.items()
                            if k in factor_scores.columns
                        }
                    if not scoring_method:
                        scoring_method = 'factor_weight' if weights_config else 'equal_weight'
                    composite_scores = self._get_scoring_engine().calculate_composite_score(
                        factor_scores, weights_config, scoring_method,
                        factor_directions=self._factor_directions
                    )
                    if composite_scores.empty:
                        return []

                return self._get_scoring_engine().rank_stocks(composite_scores, top_n)
                
        except Exception as e:
            logger.error(f"获取股票选择结果失败: {e}")
            return []

    def _batch_warm_prices(self, start_date: str, end_date: str):
        """批量预加载整个回测区间的收盘价。"""
        if (self._price_batch is not None
                and self._price_batch_start is not None
                and str(start_date) >= str(self._price_batch_start)
                and str(end_date) <= str(self._price_batch_end)):
            return
        query = db.session.query(
            StockDailyHistory.ts_code, StockDailyHistory.trade_date, StockDailyHistory.close
        ).filter(
            StockDailyHistory.trade_date >= start_date,
            StockDailyHistory.trade_date <= end_date
        )
        df = pd.read_sql(query.statement, db.engine)
        self._price_batch = {}
        for _, row in df.iterrows():
            self._price_batch[(str(row.trade_date)[:10], row.ts_code)] = float(row.close)
        self._price_batch_start = str(start_date)
        self._price_batch_end = str(end_date)
        logger.info(f'Price batch warmed: {len(self._price_batch)} entries, {start_date} to {end_date}')

    def _batch_warm_predictions(self, model_ids: list, start_date: str, end_date: str):
        """批量预加载整个回测区间的 ML 预测数据。"""
        if (self._predictions_batch is not None
                and self._pred_batch_start is not None
                and str(start_date) >= str(self._pred_batch_start)
                and str(end_date) <= str(self._pred_batch_end)
                and set(model_ids) == set(self._pred_batch_model_ids or [])):
            return
        query = db.session.query(
            MLPredictions.model_id, MLPredictions.ts_code, MLPredictions.trade_date,
            MLPredictions.predicted_return, MLPredictions.probability_score, MLPredictions.rank_score
        ).filter(
            MLPredictions.model_id.in_(model_ids),
            MLPredictions.trade_date >= start_date,
            MLPredictions.trade_date <= end_date
        )
        self._predictions_batch = pd.read_sql(query.statement, db.engine)
        if not self._predictions_batch.empty:
            self._predictions_batch['trade_date'] = pd.to_datetime(self._predictions_batch['trade_date'])
        self._pred_batch_start = str(start_date)
        self._pred_batch_end = str(end_date)
        self._pred_batch_model_ids = list(model_ids)
        logger.info(f'Predictions batch warmed: {len(self._predictions_batch)} rows, {start_date} to {end_date}')

    def _batch_warm_factor_values(self, start_date: str, end_date: str):
        """批量预加载整个回测区间的因子数据。"""
        if (self._factor_values_batch is not None
                and self._fv_batch_start is not None
                and str(start_date) >= str(self._fv_batch_start)
                and str(end_date) <= str(self._fv_batch_end)):
            return
        query = db.session.query(
            FactorValues.ts_code, FactorValues.trade_date,
            FactorValues.factor_id, FactorValues.z_score
        ).filter(
            FactorValues.trade_date >= start_date,
            FactorValues.trade_date <= end_date
        )
        self._factor_values_batch = pd.read_sql(query.statement, db.engine)
        if not self._factor_values_batch.empty:
            self._factor_values_batch['trade_date'] = pd.to_datetime(self._factor_values_batch['trade_date'])
        self._fv_batch_start = str(start_date)
        self._fv_batch_end = str(end_date)
        logger.info(f'Factor values batch warmed: {len(self._factor_values_batch)} rows, {start_date} to {end_date}')

    def _warm_stock_info(self):
        """缓存全量股票基本信息。"""
        if self._stock_info_cache:
            return
        from app.models import StockBasic
        stocks = StockBasic.query.all()
        self._stock_info_cache = {
            s.ts_code: {
                'ts_code': s.ts_code, 'name': s.name, 'industry': getattr(s, 'industry', ''),
                'area': getattr(s, 'area', ''), 'market': getattr(s, 'market', ''),
                'list_date': str(getattr(s, 'list_date', ''))
            }
            for s in stocks
        }
        logger.info(f'Stock info cached: {len(self._stock_info_cache)} stocks')

    def _get_batch_prices(self, trade_date: str, ts_codes: list) -> dict:
        """从批量缓存获取价格。"""
        if self._price_batch is None:
            return self._get_current_prices(trade_date, ts_codes)
        # trade_date 可能是 date/datetime 对象，统一转成字符串匹配缓存 key
        date_str = str(trade_date)[:10] if not isinstance(trade_date, str) else trade_date
        return {
            ts_code: self._price_batch[(date_str, ts_code)]
            for ts_code in ts_codes
            if (date_str, ts_code) in self._price_batch
        }

    def _get_batch_stock_info(self, ts_codes: list) -> dict:
        """从缓存获取股票信息。"""
        if not self._stock_info_cache:
            self._warm_stock_info()
        return {ts_code: self._stock_info_cache[ts_code]
                for ts_code in ts_codes if ts_code in self._stock_info_cache}
        """兼容 model_id/model_ids 两种入参格式。"""
        model_ids = strategy_config.get('model_ids')
        if not model_ids:
            single_model_id = strategy_config.get('model_id')
            model_ids = [single_model_id] if single_model_id is not None else []
        elif not isinstance(model_ids, list):
            model_ids = [model_ids]

        normalized = []
        seen = set()
        for model_id in model_ids:
            if model_id is None:
                continue
            model_id_str = str(model_id).strip()
            if not model_id_str or model_id_str in seen:
                continue
            normalized.append(model_id_str)
            seen.add(model_id_str)

        return normalized

    def _get_live_ml_selection(self, trade_date: str, model_ids: List[str],
                               top_n: int) -> List[Dict[str, Any]]:
        """ML预测缺失时，现场运行模型预测并完成选股。"""
        try:
            all_predictions = []
            ml_manager = self._get_ml_manager()
            scoring_engine = self._get_scoring_engine()

            for model_id in model_ids:
                predictions = ml_manager.predict(
                    model_id=model_id,
                    trade_date=trade_date,
                    strict_trade_date=True
                )
                if predictions.empty:
                    logger.warning(f"现场打分失败或无数据: model_id={model_id}, trade_date={trade_date}")
                    continue

                pred_columns = ['ts_code', 'predicted_return', 'probability_score', 'rank_score']
                live_pred = predictions[pred_columns].copy()
                live_pred['model_id'] = model_id
                all_predictions.append(live_pred)

            if not all_predictions:
                return []

            combined_predictions = pd.concat(all_predictions, ignore_index=True)
            ensemble_scores = scoring_engine._ensemble_predictions(combined_predictions, 'average')
            if ensemble_scores.empty:
                return []

            ensemble_scores['rank'] = ensemble_scores['ensemble_score'].rank(
                ascending=False, method='dense'
            ).astype(int)
            ensemble_scores['percentile_rank'] = ensemble_scores['ensemble_score'].rank(pct=True) * 100
            top_stocks = ensemble_scores.sort_values('ensemble_score', ascending=False).head(top_n)

            ts_codes = top_stocks['ts_code'].tolist()
            stock_info = scoring_engine._get_stock_info(ts_codes)

            result = []
            for _, row in top_stocks.iterrows():
                stock_data = {
                    'ts_code': row['ts_code'],
                    'ensemble_score': float(row['ensemble_score']),
                    'rank': int(row['rank']),
                    'percentile_rank': float(row['percentile_rank']),
                    'model_count': int(row['model_count'])
                }
                if row['ts_code'] in stock_info:
                    stock_data.update(stock_info[row['ts_code']])
                result.append(stock_data)

            logger.info(f"现场ML打分完成: trade_date={trade_date}, models={len(model_ids)}, selected={len(result)}")
            return result

        except Exception as e:
            logger.error(f"现场ML打分失败: trade_date={trade_date}, 错误: {e}")
            return []
    
    def _get_target_weights(self, selected_stocks: List[Dict[str, Any]], 
                          optimization_config: Dict[str, Any]) -> Dict[str, float]:
        """获取目标权重"""
        try:
            method = optimization_config.get('method', 'equal_weight')
            
            if method == 'equal_weight':
                # 等权重
                weight = 1.0 / len(selected_stocks)
                return {stock['ts_code']: weight for stock in selected_stocks}
            else:
                # 使用组合优化
                expected_returns = pd.Series({
                    stock['ts_code']: stock.get('composite_score', stock.get('ensemble_score', 0))
                    for stock in selected_stocks
                })
                
                result = self._get_portfolio_optimizer().optimize_portfolio(
                    expected_returns,
                    method=method,
                    constraints=optimization_config.get('constraints')
                )
                
                if 'error' in result:
                    # 如果优化失败，使用等权重
                    weight = 1.0 / len(selected_stocks)
                    return {stock['ts_code']: weight for stock in selected_stocks}
                
                return result['weights']
                
        except Exception as e:
            logger.error(f"获取目标权重失败: {e}")
            # 默认等权重
            weight = 1.0 / len(selected_stocks)
            return {stock['ts_code']: weight for stock in selected_stocks}
    
    def _get_current_prices(self, trade_date: str, ts_codes: List[str]) -> Dict[str, float]:
        """获取当前价格"""
        try:
            if not ts_codes:
                return {}
            
            query = db.session.query(
                StockDailyHistory.ts_code,
                StockDailyHistory.close
            ).filter(
                StockDailyHistory.trade_date == trade_date,
                StockDailyHistory.ts_code.in_(ts_codes)
            )
            
            return {row[0]: float(row[1]) for row in query}
            
        except Exception as e:
            logger.error(f"获取当前价格失败: {e}")
            return {}
    
    def _calculate_portfolio_value(self, positions: Dict[str, int], 
                                 prices: Dict[str, float], cash: float) -> float:
        """计算组合价值"""
        try:
            positions_value = sum(
                positions.get(ts_code, 0) * prices.get(ts_code, 0)
                for ts_code in positions.keys()
            )
            return positions_value + cash
            
        except Exception as e:
            logger.error(f"计算组合价值失败: {e}")
            return cash
    
    def _rebalance_portfolio(self, current_positions: Dict[str, int], 
                           current_cash: float, target_weights: Dict[str, float],
                           prices: Dict[str, float], total_value: float,
                           transaction_cost: float) -> Tuple[Dict[str, int], float, float]:
        """执行组合再平衡"""
        try:
            new_positions = {}
            turnover = 0.0
            
            # 计算目标持仓
            for ts_code, weight in target_weights.items():
                if ts_code in prices and prices[ts_code] > 0:
                    target_value = total_value * weight
                    target_shares = int(target_value / prices[ts_code] / 100) * 100  # 按手数调整
                    new_positions[ts_code] = target_shares
            
            # 计算交易成本和换手率
            total_trade_value = 0.0
            for ts_code in set(list(current_positions.keys()) + list(new_positions.keys())):
                current_shares = current_positions.get(ts_code, 0)
                new_shares = new_positions.get(ts_code, 0)
                price = prices.get(ts_code, 0)
                
                if price > 0:
                    trade_value = abs(new_shares - current_shares) * price
                    total_trade_value += trade_value
            
            turnover = total_trade_value / total_value if total_value > 0 else 0
            transaction_costs = total_trade_value * transaction_cost
            
            # 计算新的现金余额
            new_cash = current_cash
            for ts_code in set(list(current_positions.keys()) + list(new_positions.keys())):
                current_shares = current_positions.get(ts_code, 0)
                new_shares = new_positions.get(ts_code, 0)
                price = prices.get(ts_code, 0)
                
                if price > 0:
                    trade_value = (new_shares - current_shares) * price
                    new_cash -= trade_value
            
            new_cash -= transaction_costs
            
            return new_positions, new_cash, turnover
            
        except Exception as e:
            logger.error(f"组合再平衡失败: {e}")
            return current_positions, current_cash, 0.0
    
    def _calculate_performance_metrics(self, portfolio_values: List[Dict[str, Any]], 
                                     daily_returns: List[float],
                                     start_date: str, end_date: str,
                                     initial_capital: Optional[float] = None) -> Dict[str, Any]:
        """计算回测指标
        
        total_return 默认与 API 顶层一致：相对初始本金 initial_capital；
        若未传 initial_capital，则退化为首期调仓后净值作分母（旧行为）。
        """
        try:
            if not portfolio_values or not daily_returns:
                return {}
            
            initial_value = portfolio_values[0]['total_value']
            final_value = portfolio_values[-1]['total_value']
            if initial_capital is not None and initial_capital > 0:
                total_return = (final_value - initial_capital) / initial_capital
            else:
                total_return = (final_value - initial_value) / initial_value if initial_value > 0 else 0.0
            
            # 年化收益率
            days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
            years = days / 365.25
            annualized_return = (1 + total_return) ** (1 / years) - 1 if years > 0 else 0
            
            # 波动率（根据实际调仓频率年化）
            returns_array = np.array(daily_returns)
            periods_per_year = len(daily_returns) / years if years > 0 else 252
            annual_factor = np.sqrt(max(periods_per_year, 1))
            volatility = np.std(returns_array) * annual_factor
            
            # 夏普比率 (假设无风险利率为3%)
            risk_free_rate = 0.03
            sharpe_ratio = (annualized_return - risk_free_rate) / volatility if volatility > 0 else 0
            
            # 最大回撤
            values = [pv['total_value'] for pv in portfolio_values]
            peak = values[0]
            max_drawdown = 0
            for value in values:
                if value > peak:
                    peak = value
                drawdown = (peak - value) / peak
                if drawdown > max_drawdown:
                    max_drawdown = drawdown
            
            # 胜率
            positive_returns = [r for r in daily_returns if r > 0]
            win_rate = len(positive_returns) / len(daily_returns) if daily_returns else 0
            
            # 卡尔玛比率
            calmar_ratio = annualized_return / max_drawdown if max_drawdown > 0 else 0
            
            rebalance_periods = len(daily_returns)
            return {
                'total_return': total_return,
                'annualized_return': annualized_return,
                'volatility': volatility,
                'sharpe_ratio': sharpe_ratio,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'calmar_ratio': calmar_ratio,
                # 调仓间隔数（非单笔成交笔数）；保留 total_trades 兼容旧前端
                'rebalance_periods': rebalance_periods,
                'total_trades': rebalance_periods,
                'avg_daily_return': np.mean(daily_returns) if daily_returns else 0,
                'std_daily_return': np.std(daily_returns) if daily_returns else 0
            }
            
        except Exception as e:
            logger.error(f"计算回测指标失败: {e}")
            return {}
    
    def _get_benchmark_returns(self, start_date: str, end_date: str,
                               portfolio_values: List[Dict[str, Any]] = None) -> Dict[str, Any]:
        """获取沪深300基准收益率，与策略调仓日对齐。"""
        try:
            query = db.session.query(
                StockDailyHistory.trade_date, StockDailyHistory.close
            ).filter(
                StockDailyHistory.ts_code == '000300.SH',
                StockDailyHistory.trade_date >= start_date,
                StockDailyHistory.trade_date <= end_date
            ).order_by(StockDailyHistory.trade_date)

            rows = query.all()
            if not rows:
                return {}

            bench_dates = [r[0] for r in rows]
            bench_closes = [float(r[1]) for r in rows]
            bench_start = bench_closes[0]

            daily_data = [
                {'date': str(d), 'close': c, 'return': (c - bench_start) / bench_start}
                for d, c in zip(bench_dates, bench_closes)
            ]

            # 与策略调仓日对齐
            aligned_returns = []
            if portfolio_values:
                for pv in portfolio_values:
                    pv_date_str = str(pv['date'])[:10]
                    match = bench_closes[-1]
                    for i, d in enumerate(bench_dates):
                        if str(d) == pv_date_str:
                            match = bench_closes[i]
                            break
                        elif str(d) < pv_date_str:
                            match = bench_closes[i]
                    aligned_returns.append({
                        'date': pv_date_str,
                        'value': (match - bench_start) / bench_start
                    })

            # 基准指标
            if len(bench_closes) >= 2:
                total_ret = (bench_closes[-1] - bench_start) / bench_start
                days = (pd.to_datetime(end_date) - pd.to_datetime(start_date)).days
                years = max(days / 365.25, 0.01)
                annual_ret = (1 + total_ret) ** (1 / years) - 1
                daily_rets = [(bench_closes[i] - bench_closes[i-1]) / bench_closes[i-1]
                              for i in range(1, len(bench_closes))]
                vol = float(np.std(daily_rets) * np.sqrt(252)) if daily_rets else 0.0
                peak = bench_closes[0]
                mdd = 0.0
                for c in bench_closes:
                    if c > peak: peak = c
                    dd = (peak - c) / peak
                    if dd > mdd: mdd = dd
            else:
                total_ret = annual_ret = vol = mdd = 0.0

            return {
                'name': '沪深300',
                'total_return': total_ret,
                'annualized_return': annual_ret,
                'volatility': vol,
                'max_drawdown': mdd,
                'aligned_returns': aligned_returns,
                'daily_data': daily_data[:500],
            }

        except Exception as e:
            logger.error(f"获取基准收益率失败: {e}")
            return {}
    
    def compare_strategies(self, strategies: List[Dict[str, Any]], 
                         start_date: str, end_date: str) -> Dict[str, Any]:
        """比较多个策略"""
        try:
            results = []
            
            for i, strategy in enumerate(strategies):
                logger.info(f"回测策略 {i+1}: {strategy.get('name', f'Strategy_{i+1}')}")
                
                result = self.run_backtest(
                    strategy['config'], start_date, end_date,
                    strategy.get('initial_capital', 1000000.0),
                    strategy.get('rebalance_frequency', 'monthly')
                )
                
                if result.get('success'):
                    results.append({
                        'strategy_name': strategy.get('name', f'Strategy_{i+1}'),
                        'result': result
                    })
            
            # 生成比较报告
            comparison = self._generate_comparison_report(results)
            
            return {
                'success': True,
                'strategies': results,
                'comparison': comparison
            }
            
        except Exception as e:
            logger.error(f"策略比较失败: {e}")
            return {'error': str(e)}
    
    def _generate_comparison_report(self, results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """生成策略比较报告"""
        try:
            if not results:
                return {}
            
            comparison_metrics = {}
            
            for result in results:
                strategy_name = result['strategy_name']
                metrics = result['result']['performance_metrics']
                
                comparison_metrics[strategy_name] = {
                    'total_return': metrics.get('total_return', 0),
                    'annualized_return': metrics.get('annualized_return', 0),
                    'volatility': metrics.get('volatility', 0),
                    'sharpe_ratio': metrics.get('sharpe_ratio', 0),
                    'max_drawdown': metrics.get('max_drawdown', 0),
                    'win_rate': metrics.get('win_rate', 0),
                    'calmar_ratio': metrics.get('calmar_ratio', 0)
                }
            
            # 找出最佳策略
            best_strategy = {
                'highest_return': max(comparison_metrics.items(), 
                                    key=lambda x: x[1]['total_return'])[0],
                'highest_sharpe': max(comparison_metrics.items(), 
                                    key=lambda x: x[1]['sharpe_ratio'])[0],
                'lowest_drawdown': min(comparison_metrics.items(), 
                                     key=lambda x: x[1]['max_drawdown'])[0],
                'highest_win_rate': max(comparison_metrics.items(), 
                                      key=lambda x: x[1]['win_rate'])[0]
            }
            
            return {
                'metrics_comparison': comparison_metrics,
                'best_strategy': best_strategy,
                'summary': {
                    'total_strategies': len(results),
                    'avg_return': np.mean([m['total_return'] for m in comparison_metrics.values()]),
                    'avg_sharpe': np.mean([m['sharpe_ratio'] for m in comparison_metrics.values()]),
                    'avg_drawdown': np.mean([m['max_drawdown'] for m in comparison_metrics.values()])
                }
            }
            
        except Exception as e:
            logger.error(f"生成比较报告失败: {e}")
            return {} 
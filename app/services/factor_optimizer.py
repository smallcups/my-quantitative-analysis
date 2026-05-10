import pandas as pd
import numpy as np
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from scipy.stats import spearmanr
from loguru import logger

from app.extensions import db
from app.models import (
    FactorDefinition, FactorValues, FactorEffectiveness,
    StockDailyHistory, StockBasic
)
from app.services.factor_engine import FactorEngine


class FactorOptimizer:
    """因子优化引擎 - 自动分析因子有效性、筛选最佳因子、计算最优权重"""

    def __init__(self):
        self.factor_engine = FactorEngine()
        self.DEFAULT_PERIODS = [1, 5, 20]
        self.MIN_SAMPLES = 30

    # ============================================================
    # Rank IC 计算 (核心统计方法)
    # ============================================================

    def compute_rank_ic(
        self,
        factor_id: str,
        trade_date: str,
        forward_period: int = 5,
        ts_codes: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        计算单个因子在某一天的 Rank IC。
        Rank IC = 因子值与未来N日收益率的 Spearman 秩相关系数。
        """
        try:
            factor_df = self.factor_engine.get_factor_exposure(factor_id, trade_date)
            if factor_df.empty:
                return {'error': f'No factor data for {factor_id} on {trade_date}'}

            if ts_codes is None:
                stocks = StockBasic.query.all()
                ts_codes_list = [s.ts_code for s in stocks]
            else:
                ts_codes_list = ts_codes

            trade_dt = pd.to_datetime(trade_date).date()

            price_query = StockDailyHistory.query.filter(
                StockDailyHistory.ts_code.in_(ts_codes_list),
                StockDailyHistory.trade_date > trade_dt
            ).order_by(StockDailyHistory.ts_code, StockDailyHistory.trade_date)

            price_data = pd.read_sql(price_query.statement, db.engine)

            if price_data.empty:
                return {'error': f'No price data after {trade_date}'}

            # 读取当前日收盘价（向量化查询）
            current_query = StockDailyHistory.query.filter(
                StockDailyHistory.ts_code.in_(ts_codes_list),
                StockDailyHistory.trade_date == trade_dt
            )
            current_data = pd.read_sql(current_query.statement, db.engine)
            if current_data.empty:
                return {'error': f'No current price data for {trade_date}'}

            current_prices = dict(zip(current_data['ts_code'], current_data['close']))

            # 向量化：对每只股票，按日期排序后取第 forward_period 个未来价
            price_data['trade_date'] = pd.to_datetime(price_data['trade_date'])
            price_data = price_data.sort_values(['ts_code', 'trade_date'])
            # 每只股票第N行 = 该股票未来第N天的价格
            position_counts = price_data.groupby('ts_code').cumcount()
            future_prices = price_data[position_counts == (forward_period - 1)][['ts_code', 'close']].rename(
                columns={'close': 'future_close'}
            )

            # 构建合并表：ts_code + current_close + future_close
            merged = current_data[['ts_code', 'close']].copy()
            merged = merged.rename(columns={'close': 'current_close'})
            merged = pd.merge(merged, future_prices, on='ts_code', how='inner')
            merged['forward_return'] = (merged['future_close'] - merged['current_close']) / merged['current_close']

            # 合并因子值
            merged = pd.merge(
                factor_df[['ts_code', 'factor_value']],
                merged[['ts_code', 'forward_return']],
                on='ts_code', how='inner'
            )
            merged = merged.dropna()

            if len(merged) < self.MIN_SAMPLES:
                return {
                    'error': f'Insufficient valid pairs: {len(merged)} < {self.MIN_SAMPLES}',
                    'sample_count': len(merged)
                }

            ic, p_value = spearmanr(merged['factor_value'].values, merged['forward_return'].values)
            if np.isnan(ic):
                return {'error': 'IC is NaN'}

            return {
                'ic_value': float(ic),
                'p_value': float(p_value) if not np.isnan(p_value) else None,
                'sample_count': len(merged),
                'factor_id': factor_id,
                'trade_date': trade_date,
                'forward_period': forward_period,
                'success': True
            }

        except Exception as e:
            logger.error(f'compute_rank_ic failed: {factor_id}@{trade_date}, error: {e}')
            return {'error': str(e)}

    # ============================================================
    # 滚动 IC 统计
    # ============================================================

    def compute_rolling_ic_statistics(
        self,
        factor_id: str,
        start_date: str,
        end_date: str,
        forward_period: int = 5
    ) -> Dict[str, Any]:
        """
        计算历史窗口内的滚动 IC 统计指标：IC均值、标准差、IR、胜率。
        """
        try:
            date_query = db.session.query(FactorValues.trade_date).filter(
                FactorValues.factor_id == factor_id,
                FactorValues.trade_date >= start_date,
                FactorValues.trade_date <= end_date
            ).distinct().order_by(FactorValues.trade_date)

            trade_dates = [row[0] for row in date_query.all()]

            ic_series = []
            valid_dates = []

            for single_date in trade_dates:
                date_str = single_date.strftime('%Y-%m-%d') if hasattr(single_date, 'strftime') else str(single_date)
                result = self.compute_rank_ic(factor_id, date_str, forward_period)
                if result.get('success'):
                    ic_series.append(result['ic_value'])
                    valid_dates.append(single_date)

            if len(ic_series) < 3:
                return {
                    'error': f'Too few valid IC observations: {len(ic_series)} < 3',
                    'factor_id': factor_id,
                    'forward_period': forward_period,
                    'ic_values': ic_series,
                    'dates': [str(d) for d in valid_dates]
                }

            ic_array = np.array(ic_series)
            ic_mean = float(np.mean(ic_array))
            ic_std = float(np.std(ic_array, ddof=1))
            ic_ir = float(ic_mean / ic_std) if ic_std > 0 else 0.0
            ic_win_rate = float(np.sum(ic_array > 0) / len(ic_array))
            direction = 'positive' if ic_mean > 0 else 'negative'

            return {
                'factor_id': factor_id,
                'forward_period': forward_period,
                'evaluation_date': end_date,
                'ic_mean': ic_mean,
                'ic_std': ic_std,
                'ic_ir': ic_ir,
                'ic_win_rate': ic_win_rate,
                'latest_ic': ic_series[-1] if ic_series else 0.0,
                'sample_count': len(ic_series),
                'factor_direction': direction,
                'ic_series': ic_series,
                'dates': [str(d) for d in valid_dates],
                'success': True
            }

        except Exception as e:
            logger.error(f'compute_rolling_ic_statistics failed: {factor_id}, error: {e}')
            return {'error': str(e)}

    # ============================================================
    # 全量因子分析
    # ============================================================

    def analyze_all_factors(
        self,
        start_date: str,
        end_date: str,
        forward_periods: Optional[List[int]] = None
    ) -> Dict[str, Any]:
        """对所有因子运行多周期 IC 分析并持久化。"""
        periods = forward_periods or self.DEFAULT_PERIODS

        # 只分析在 factor_values 表中有数据的因子
        from app.models import FactorValues
        active_query = db.session.query(FactorValues.factor_id).distinct()
        factor_ids = sorted([row[0] for row in active_query.all()])

        results_by_period = {}

        for period in periods:
            factor_results = []
            for factor_id in factor_ids:
                try:
                    stats = self.compute_rolling_ic_statistics(factor_id, start_date, end_date, forward_period=period)
                    factor_results.append(stats)
                    self._persist_effectiveness(stats)
                except Exception as e:
                    logger.error(f'analyze factor {factor_id} failed: {e}')
                    factor_results.append({'factor_id': factor_id, 'error': str(e)})

            results_by_period[str(period)] = {
                'factors': factor_results,
                'total': len(factor_results),
                'valid_count': sum(1 for r in factor_results if r.get('success'))
            }

        return {
            'start_date': start_date,
            'end_date': end_date,
            'forward_periods': periods,
            'results': results_by_period
        }

    def _persist_effectiveness(self, stats: Dict[str, Any]) -> None:
        """将 IC 统计结果持久化到 factor_effectiveness 表。"""
        if not stats.get('success'):
            return

        try:
            eval_date = pd.to_datetime(stats['evaluation_date']).date()

            record = FactorEffectiveness.query.filter_by(
                factor_id=stats['factor_id'],
                evaluation_date=eval_date,
                forward_period=stats['forward_period']
            ).first()

            if record is None:
                record = FactorEffectiveness(
                    factor_id=stats['factor_id'],
                    evaluation_date=eval_date,
                    forward_period=stats['forward_period']
                )
                db.session.add(record)

            record.ic_mean = stats['ic_mean']
            record.ic_std = stats['ic_std']
            record.ic_ir = stats['ic_ir']
            record.ic_win_rate = stats['ic_win_rate']
            record.latest_ic = stats.get('latest_ic')
            record.sample_count = stats['sample_count']
            record.factor_direction = stats['factor_direction']
            record.extra_info = {
                'ic_series': stats.get('ic_series', []),
                'dates': stats.get('dates', [])
            }
            record.updated_at = datetime.utcnow()

            db.session.commit()

        except Exception as e:
            db.session.rollback()
            logger.error(f'persist effectiveness failed: {e}')

    # ============================================================
    # 因子筛选
    # ============================================================

    def select_factors(
        self,
        effectiveness_data: List[Dict[str, Any]],
        ic_ir_threshold: float = 0.3,
        max_correlation: float = 0.7,
        min_factors: int = 3,
        max_factors: int = 10
    ) -> Dict[str, Any]:
        """
        基于IC分析筛选最佳因子集合。
        1. 按 |IC_IR| 阈值过滤
        2. 去除高相关性冗余因子
        3. 控制因子数量上下限
        """
        try:
            valid_factors = [
                f for f in effectiveness_data
                if f.get('success') and abs(f.get('ic_ir', 0)) > ic_ir_threshold
            ]

            if len(valid_factors) < min_factors:
                logger.warning(f'Only {len(valid_factors)} pass IC_IR > {ic_ir_threshold}, relaxing')
                valid_factors = sorted(
                    [f for f in effectiveness_data if f.get('success')],
                    key=lambda x: abs(x.get('ic_ir', 0)),
                    reverse=True
                )[:max(max_factors, min_factors)]

            valid_factors.sort(key=lambda x: abs(x.get('ic_ir', 0)), reverse=True)

            selected = []
            factor_ids_to_check = [f['factor_id'] for f in valid_factors]

            if len(factor_ids_to_check) > 1:
                correlation_matrix = self._compute_factor_correlation_matrix(factor_ids_to_check)
                selected_ids = set()

                for f in valid_factors:
                    fid = f['factor_id']
                    if fid in selected_ids:
                        continue

                    too_correlated = False
                    for selected_id in selected_ids:
                        if (selected_id in correlation_matrix.index
                                and fid in correlation_matrix.columns):
                            rho = abs(correlation_matrix.loc[selected_id, fid])
                            if rho > max_correlation:
                                too_correlated = True
                                break

                    if not too_correlated:
                        selected_ids.add(fid)
                        selected.append(f)

                if len(selected) > max_factors:
                    selected = selected[:max_factors]
            else:
                selected = valid_factors[:max_factors]

            weights = self._compute_weights(selected)

            return {
                'selected_factors': selected,
                'weights': weights,
                'total_input': len(effectiveness_data),
                'total_after_threshold': len(valid_factors),
                'total_selected': len(selected),
                'selection_summary': {
                    f['factor_id']: {
                        'ic_ir': f.get('ic_ir'),
                        'ic_mean': f.get('ic_mean'),
                        'weight': weights.get(f['factor_id'], 0)
                    }
                    for f in selected
                }
            }

        except Exception as e:
            logger.error(f'select_factors failed: {e}')
            return {'error': str(e)}

    def _compute_factor_correlation_matrix(self, factor_ids: List[str]) -> pd.DataFrame:
        """计算因子间截面相关性矩阵。"""
        try:
            latest_date_query = db.session.query(FactorValues.trade_date).filter(
                FactorValues.factor_id.in_(factor_ids)
            ).order_by(FactorValues.trade_date.desc()).first()

            if not latest_date_query:
                return pd.DataFrame(index=factor_ids, columns=factor_ids).fillna(0)

            latest_date = latest_date_query[0]

            query = FactorValues.query.filter(
                FactorValues.trade_date == latest_date,
                FactorValues.factor_id.in_(factor_ids)
            )
            data = pd.read_sql(query.statement, db.engine)

            if data.empty:
                return pd.DataFrame(index=factor_ids, columns=factor_ids).fillna(0)

            pivot = data.pivot_table(
                index='ts_code', columns='factor_id',
                values='factor_value', aggfunc='first'
            ).dropna()

            if pivot.empty or pivot.shape[1] < 2:
                return pd.DataFrame(index=factor_ids, columns=factor_ids).fillna(0)

            return pivot.corr(method='spearman')

        except Exception as e:
            logger.error(f'compute correlation matrix failed: {e}')
            return pd.DataFrame(index=factor_ids, columns=factor_ids).fillna(0)

    # ============================================================
    # 权重计算
    # ============================================================

    def _compute_weights(
        self,
        selected_factors: List[Dict[str, Any]],
        method: str = 'ic_ir_weighted'
    ) -> Dict[str, float]:
        """
        计算因子权重。
        - ic_ir_weighted: 权重 ∝ |IC_IR|
        - ic_mean_weighted: 权重 ∝ |IC_mean|
        - equal_weight: 等权
        """
        factor_ids = [f['factor_id'] for f in selected_factors]
        n = len(factor_ids)

        if n == 0:
            return {}

        if method == 'equal_weight':
            return {fid: round(1.0 / n, 6) for fid in factor_ids}

        if method == 'ic_mean_weighted':
            ic_values = np.array([abs(f.get('ic_mean', 0)) for f in selected_factors])
            total = ic_values.sum()
            if total <= 0:
                return {fid: round(1.0 / n, 6) for fid in factor_ids}
            weights = ic_values / total
            return {fid: round(float(w), 6) for fid, w in zip(factor_ids, weights)}

        # Default: ic_ir_weighted
        ic_irs = np.array([abs(f.get('ic_ir', 0)) for f in selected_factors])
        total = ic_irs.sum()
        if total <= 0:
            return {fid: round(1.0 / n, 6) for fid in factor_ids}
        weights = ic_irs / total
        return {fid: round(float(w), 6) for fid, w in zip(factor_ids, weights)}

    # ============================================================
    # 公开接口
    # ============================================================

    def get_effectiveness_report(
        self,
        factor_id: Optional[str] = None,
        forward_period: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """获取已持久化的因子有效性报告。"""
        query = FactorEffectiveness.query.order_by(FactorEffectiveness.evaluation_date.desc())
        if factor_id:
            query = query.filter(FactorEffectiveness.factor_id == factor_id)
        if forward_period:
            query = query.filter(FactorEffectiveness.forward_period == forward_period)
        records = query.limit(limit).all()
        return [r.to_dict() for r in records]

    def get_optimized_weights(
        self,
        evaluation_date: str,
        start_date: str = None,
        forward_period: int = 5,
        method: str = 'ic_ir_weighted',
        ic_ir_threshold: float = 0.3,
        max_correlation: float = 0.7,
        min_factors: int = 3,
        max_factors: int = 10
    ) -> Dict[str, Any]:
        """端到端获取优化后的因子权重。优先持久化数据，其次直接运行分析。"""
        latest_records = self._get_latest_effectiveness(forward_period)

        if not latest_records:
            if start_date is None:
                dt = pd.to_datetime(evaluation_date)
                start_date = (dt - timedelta(days=252)).strftime('%Y-%m-%d')
            analysis = self.analyze_all_factors(start_date, evaluation_date, [forward_period])
            # 直接从分析结果提取有效性数据
            for period_str, period_data in analysis.get('results', {}).items():
                if int(period_str) == forward_period:
                    latest_records = [
                        f for f in period_data.get('factors', [])
                        if f.get('success')
                    ]
                    break
            # 如果持久化成功了，重试从 DB 读取
            if not latest_records:
                latest_records = self._get_latest_effectiveness(forward_period)

        if not latest_records:
            return {'error': 'No effectiveness data available', 'weights': {}}

        selection_result = self.select_factors(
            latest_records,
            ic_ir_threshold=ic_ir_threshold,
            max_correlation=max_correlation,
            min_factors=min_factors,
            max_factors=max_factors
        )

        if 'error' in selection_result:
            return selection_result

        weights = self._compute_weights(selection_result['selected_factors'], method=method)

        return {
            'evaluation_date': evaluation_date,
            'start_date': start_date,
            'forward_period': forward_period,
            'weight_method': method,
            'weights': weights,
            'selected_factors': selection_result['selection_summary'],
            'selection_metadata': {
                k: v for k, v in selection_result.items()
                if k not in ('selected_factors', 'weights', 'selection_summary')
            }
        }

    def _get_latest_effectiveness(self, forward_period: int = 5) -> List[Dict[str, Any]]:
        """获取每个因子最新一期有效性评估数据。"""
        try:
            subq = db.session.query(
                FactorEffectiveness.factor_id,
                db.func.max(FactorEffectiveness.evaluation_date).label('max_date')
            ).filter(
                FactorEffectiveness.forward_period == forward_period
            ).group_by(FactorEffectiveness.factor_id).subquery()

            query = db.session.query(FactorEffectiveness).join(
                subq,
                db.and_(
                    FactorEffectiveness.factor_id == subq.c.factor_id,
                    FactorEffectiveness.evaluation_date == subq.c.max_date,
                    FactorEffectiveness.forward_period == forward_period
                )
            )

            records = query.all()
            return [
                {
                    'factor_id': r.factor_id,
                    'evaluation_date': str(r.evaluation_date),
                    'forward_period': r.forward_period,
                    'ic_mean': float(r.ic_mean) if r.ic_mean else 0.0,
                    'ic_std': float(r.ic_std) if r.ic_std else 0.0,
                    'ic_ir': float(r.ic_ir) if r.ic_ir else 0.0,
                    'ic_win_rate': float(r.ic_win_rate) if r.ic_win_rate else 0.0,
                    'latest_ic': float(r.latest_ic) if r.latest_ic else 0.0,
                    'sample_count': r.sample_count or 0,
                    'factor_direction': r.factor_direction or 'unknown',
                    'success': True
                }
                for r in records
            ]
        except Exception as e:
            logger.error(f'_get_latest_effectiveness failed: {e}')
            return []

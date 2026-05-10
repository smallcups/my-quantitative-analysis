"""
生成仿真测试数据，用于验证因子优化流水线。
创建因子值 + 股价数据，使部分因子有已知的 IC 值。
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from app.extensions import db
from app import create_app

app = create_app('default')

STOCK_COUNT = 200
DATE_COUNT = 120  # 约半年交易日

def seed():
    with app.app_context():
        print(">>> 生成股票基本信息...")
        db.session.execute(db.text('DELETE FROM stock_basic'))

        from app.models import StockBasic
        stocks = []
        for i in range(STOCK_COUNT):
            s = StockBasic(
                ts_code=f'{600000+i:06d}.SH' if i < 100 else f'{300000+i-100:06d}.SZ',
                symbol=f'{600000+i:06d}' if i < 100 else f'{300000+i-100:06d}',
                name=f'测试股票{i+1}',
                area='测试',
                industry='测试行业',
                list_date='2020-01-01'
            )
            stocks.append(s)
        db.session.add_all(stocks)
        db.session.commit()
        print(f'    {STOCK_COUNT} 只有')

        # 交易日序列
        print(">>> 生成交易日数据...")
        base_date = datetime(2025, 9, 1)
        dates = []
        d = base_date
        while len(dates) < DATE_COUNT:
            if d.weekday() < 5:  # 工作日
                dates.append(d.strftime('%Y-%m-%d'))
            d += timedelta(days=1)

        ts_codes = [s.ts_code for s in stocks]
        np.random.seed(42)

        # 生成股价数据 (stock_daily_history)
        print(">>> 生成股价数据...")
        db.session.execute(db.text('DELETE FROM stock_daily_history'))
        from app.models import StockDailyHistory

        price_rows = []
        # 为每只股票生成随机游走价格
        base_prices = np.random.uniform(5, 50, STOCK_COUNT)
        for i, ts_code in enumerate(ts_codes):
            price = base_prices[i]
            for date_str in dates:
                # 随机游走：日波动 ~2%
                ret = np.random.normal(0.0005, 0.02)
                price *= (1 + ret)
                pre_close = price / (1 + ret)
                vol = np.random.randint(10000, 1000000)
                high = price * (1 + abs(np.random.normal(0, 0.01)))
                low = price * (1 - abs(np.random.normal(0, 0.01)))
                price_rows.append({
                    'ts_code': ts_code, 'trade_date': date_str,
                    'open': pre_close, 'high': high, 'low': low,
                    'close': price, 'pre_close': pre_close,
                    'change_c': price - pre_close,
                    'pct_chg': (price - pre_close) / pre_close * 100,
                    'vol': vol, 'amount': vol * price
                })

        # 批量插入
        batch_size = 500
        for j in range(0, len(price_rows), batch_size):
            batch = price_rows[j:j+batch_size]
            db.session.execute(
                db.text(
                    'INSERT INTO stock_daily_history '
                    '(ts_code, trade_date, open, high, low, close, pre_close, '
                    'change_c, pct_chg, vol, amount) '
                    'VALUES (:ts_code, :trade_date, :open, :high, :low, :close, '
                    ':pre_close, :change_c, :pct_chg, :vol, :amount)'
                ),
                batch
            )
        db.session.commit()
        print(f'    {len(price_rows)} 条股价记录')

        # 生成因子值 (factor_values) - 核心：构造已知 IC 的因子
        print(">>> 生成因子值...")

        # 先定义未来 N 日收益率（作为 ground truth）
        print("    计算未来收益率...")
        close_pivot = pd.DataFrame(price_rows).pivot(
            index='trade_date', columns='ts_code', values='close'
        )
        # 按日期排序
        close_pivot = close_pivot.sort_index()

        # 5日未来收益
        future_ret_5d = close_pivot.pct_change(5).shift(-5)  # T 日因子 → T+5 日收益
        # 20日未来收益
        future_ret_20d = close_pivot.pct_change(20).shift(-20)

        # 构建因子：3个"有效因子" + 2个"噪声因子"
        print("    构建有效因子和噪声因子...")
        db.session.execute(db.text('DELETE FROM factor_values'))
        from app.models import FactorValues

        factor_rows = []
        for idx, date_str in enumerate(dates[:-20]):  # 留 20 天余量算未来收益
            for i, ts_code in enumerate(ts_codes):
                # 有效因子 A: IC ~ 0.35 (与5日收益强相关)
                if ts_code in future_ret_5d.columns and date_str in future_ret_5d.index:
                    fwd = future_ret_5d.loc[date_str, ts_code]
                    if pd.notna(fwd):
                        factor_a = fwd * 5 + np.random.normal(0, 0.02)  # 信号 + 噪声
                    else:
                        factor_a = np.random.normal(0, 0.05)
                else:
                    factor_a = np.random.normal(0, 0.05)

                # 有效因子 B: IC ~ 0.25 (与20日收益中等相关)
                if ts_code in future_ret_20d.columns and date_str in future_ret_20d.index:
                    fwd = future_ret_20d.loc[date_str, ts_code]
                    if pd.notna(fwd):
                        factor_b = fwd * 8 + np.random.normal(0, 0.025)
                    else:
                        factor_b = np.random.normal(0, 0.04)
                else:
                    factor_b = np.random.normal(0, 0.04)

                # 逆向因子 C: IC ~ -0.20 (负相关 = 有方向性的有效信号)
                if ts_code in future_ret_5d.columns and date_str in future_ret_5d.index:
                    fwd = future_ret_5d.loc[date_str, ts_code]
                    if pd.notna(fwd):
                        factor_c = -fwd * 3 + np.random.normal(0, 0.02)
                    else:
                        factor_c = np.random.normal(0, 0.04)
                else:
                    factor_c = np.random.normal(0, 0.04)

                # 噪声因子 D: IC ~ 0.0 (纯随机)
                factor_d = np.random.normal(0, 0.05)

                # 噪声因子 E: IC ~ 0.0 (纯随机)
                factor_e = np.random.normal(0, 0.05)

                for fid, fv in [
                    ('factor_a', factor_a), ('factor_b', factor_b),
                    ('factor_c', factor_c), ('factor_d', factor_d),
                    ('factor_e', factor_e)
                ]:
                    factor_rows.append({
                        'ts_code': ts_code, 'trade_date': date_str,
                        'factor_id': fid, 'factor_value': float(fv),
                        'percentile_rank': 50.0, 'z_score': 0.0
                    })

        # 批量插入因子值
        print(f"    插入 {len(factor_rows)} 条因子值...")
        for j in range(0, len(factor_rows), 500):
            batch = factor_rows[j:j+500]
            db.session.execute(
                db.text(
                    'INSERT INTO factor_values '
                    '(ts_code, trade_date, factor_id, factor_value, percentile_rank, z_score) '
                    'VALUES (:ts_code, :trade_date, :factor_id, :factor_value, '
                    ':percentile_rank, :z_score)'
                ),
                batch
            )
        db.session.commit()

        # 计算百分位和 Z 分数
        print("    计算因子统计...")
        for fid in ['factor_a', 'factor_b', 'factor_c', 'factor_d', 'factor_e']:
            rows = db.session.execute(
                db.text(
                    'SELECT ts_code, trade_date, factor_value FROM factor_values '
                    'WHERE factor_id=:fid'
                ),
                {'fid': fid}
            ).fetchall()

            values = [r[2] for r in rows]
            if not values:
                continue
            arr = np.array(values)
            mean = arr.mean()
            std = arr.std()
            if std == 0:
                std = 1

            for r in rows:
                z = (r[2] - mean) / std
                percentile = sum(1 for v in values if v < r[2]) / len(values) * 100
                db.session.execute(
                    db.text(
                        'UPDATE factor_values SET z_score=:z, percentile_rank=:p '
                        'WHERE ts_code=:c AND trade_date=:d AND factor_id=:f'
                    ),
                    {'z': float(z), 'p': float(percentile),
                     'c': r[0], 'd': r[1], 'f': fid}
                )
        db.session.commit()

        # 注册因子定义和 daily_basic 填充
        print(">>> 注册因子定义...")
        db.session.execute(db.text('DELETE FROM factor_definition'))
        for fid, fname in [
            ('factor_a', '有效因子A(IC~0.35)'),
            ('factor_b', '有效因子B(IC~0.25)'),
            ('factor_c', '逆向因子C(IC~-0.20)'),
            ('factor_d', '噪声因子D(IC~0)'),
            ('factor_e', '噪声因子E(IC~0)')
        ]:
            db.session.execute(
                db.text(
                    'INSERT INTO factor_definition '
                    '(factor_id, factor_name, factor_formula, factor_type, is_active) '
                    'VALUES (:fid, :fname, "", "technical", 1)'
                ),
                {'fid': fid, 'fname': fname}
            )
        db.session.commit()

        print(">>> 填充 daily_basic...")
        db.session.execute(db.text('DELETE FROM stock_daily_basic'))
        db.session.execute(
            db.text(
                'INSERT IGNORE INTO stock_daily_basic (ts_code, trade_date, close) '
                'SELECT ts_code, trade_date, close FROM stock_daily_history'
            )
        )
        db.session.commit()

        # 验证
        print("\n>>> 验证...")
        counts = {}
        for fid in ['factor_a', 'factor_b', 'factor_c', 'factor_d', 'factor_e']:
            c = db.session.execute(
                db.text('SELECT COUNT(*) FROM factor_values WHERE factor_id=:fid'),
                {'fid': fid}
            ).scalar()
            counts[fid] = c
            print(f'    {fid}: {c} 条')

        print('\n>>> 预期 IC 验证:')
        print('    因子优化应该能识别:')
        print('    - factor_a (|IC_IR| 最高) → 权重最大')
        print('    - factor_b (|IC_IR| 次之)  → '+ '权重居中')
        print('    - factor_c (负IC, |IC_IR|)  → '+'有效但方向相反')
        print('    - factor_d, factor_e (IC≈0) → 被过滤掉')


if __name__ == '__main__':
    seed()

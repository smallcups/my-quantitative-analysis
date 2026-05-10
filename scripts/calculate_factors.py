"""
优化版因子计算：一次拉数据，一次性算完所有技术面因子
每个日期从 6次DB查询 → 1次，速度提升约 6 倍
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
import numpy as np
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app('default')


def _save_batch(batch):
    """批量写入 factor_values"""
    sql = (
        'INSERT INTO factor_values '
        '(ts_code, trade_date, factor_id, factor_value, percentile_rank, z_score) '
        'VALUES (%s,%s,%s,%s,50.0,0.0) '
        'ON DUPLICATE KEY UPDATE factor_value=VALUES(factor_value)'
    )
    conn = db.engine.raw_connection()
    cursor = conn.cursor()
    cursor.executemany(sql, batch)
    conn.commit()
    cursor.close()


def __searchsorted_percentile(sorted_arr, value):
    idx = np.searchsorted(sorted_arr, value)
    return min(99.99, max(0.01, idx / len(sorted_arr) * 100))


with app.app_context():
    # 获取所有交易日
    dates = db.session.execute(
        text('SELECT DISTINCT trade_date FROM stock_daily_history ORDER BY trade_date')
    ).fetchall()
    all_dates = [d[0].strftime('%Y-%m-%d') for d in dates]
    print(f'总交易日: {len(all_dates)} ({all_dates[0]} ~ {all_dates[-1]})')

    # 只看还没算过的日期
    existing = db.session.execute(
        text('SELECT DISTINCT trade_date FROM factor_values')
    ).fetchall()
    existing_dates = {d[0].strftime('%Y-%m-%d') for d in existing}
    todo_dates = [d for d in all_dates if d not in existing_dates]

    print(f'已算: {len(existing_dates)} 天, 待算: {len(todo_dates)} 天')
    if not todo_dates:
        print('全部已算完！')
        exit()

    # 只需要最近一部分日期？不，全算
    print(f'预计耗时: {len(todo_dates) * 0.5:.0f} 分钟 ({len(todo_dates)*0.5/60:.1f} 小时)')
    print()

    # ---- 核心优化：一次性预加载全部股价数据（147万行）到内存 ----
    print('>>> 预加载股价数据...')
    price_df = pd.read_sql(
        text('SELECT ts_code, trade_date, close, pre_close, vol '
             'FROM stock_daily_history ORDER BY ts_code, trade_date'),
        db.engine
    )
    price_df['trade_date'] = pd.to_datetime(price_df['trade_date'])
    print(f'    加载了 {len(price_df):,} 条股价记录')

    # 获取股票列表
    stocks_df = pd.read_sql(text('SELECT ts_code FROM stock_basic'), db.engine)
    all_stocks = stocks_df['ts_code'].tolist()
    print(f'    共 {len(all_stocks):,} 只股票')

    # ---- 批量计算 ----
    total_saved = 0
    batch = []

    for i, date_str in enumerate(todo_dates):
        try:
            trade_dt = pd.to_datetime(date_str)

            # 取当天有交易的股票
            day_data = price_df[price_df['trade_date'] == trade_dt]
            if day_data.empty:
                continue
            active_stocks = day_data['ts_code'].tolist()

            # 取每只股票的完整历史
            hist = price_df[price_df['ts_code'].isin(active_stocks) & (price_df['trade_date'] <= trade_dt)]

            # === 所有因子一次算完 ===
            records = []

            # --- momentum_1d ---
            ret_1d = day_data.set_index('ts_code')['close'] / day_data.set_index('ts_code')['pre_close'] - 1
            for ts_code, val in ret_1d.items():
                records.append((ts_code, date_str, 'momentum_1d', float(val)))

            # --- momentum_5d ---
            close_series = hist.pivot_table(index='trade_date', columns='ts_code', values='close')
            if len(close_series) >= 5:
                ret_5d = close_series.iloc[-1] / close_series.iloc[-5] - 1
                for ts_code in active_stocks:
                    if ts_code in ret_5d.index and not pd.isna(ret_5d[ts_code]):
                        records.append((ts_code, date_str, 'momentum_5d', float(ret_5d[ts_code])))

            # --- momentum_20d ---
            if len(close_series) >= 20:
                ret_20d = close_series.iloc[-1] / close_series.iloc[-20] - 1
                for ts_code in active_stocks:
                    if ts_code in ret_20d.index and not pd.isna(ret_20d[ts_code]):
                        records.append((ts_code, date_str, 'momentum_20d', float(ret_20d[ts_code])))

            # --- volatility_20d ---
            if len(close_series) >= 20:
                daily_ret = close_series.pct_change().iloc[-20:]
                vol = daily_ret.std()
                for ts_code in active_stocks:
                    if ts_code in vol.index and not pd.isna(vol[ts_code]):
                        records.append((ts_code, date_str, 'volatility_20d', float(vol[ts_code])))

            # --- volume_ratio_20d ---
            vol_data = hist.pivot_table(index='trade_date', columns='ts_code', values='vol')
            if len(vol_data) >= 20:
                avg_vol_20d = vol_data.iloc[-20:].mean()
                today_vol = day_data.set_index('ts_code')['vol']
                for ts_code in active_stocks:
                    if ts_code in avg_vol_20d.index and ts_code in today_vol.index:
                        if avg_vol_20d[ts_code] > 0:
                            ratio = float(today_vol[ts_code] / avg_vol_20d[ts_code])
                            records.append((ts_code, date_str, 'volume_ratio_20d', ratio))

            # --- price_to_ma20 ---
            if len(close_series) >= 20:
                ma20 = close_series.iloc[-20:].mean()
                today_close = day_data.set_index('ts_code')['close']
                for ts_code in active_stocks:
                    if ts_code in ma20.index and ts_code in today_close.index:
                        if ma20[ts_code] > 0:
                            ratio = float(today_close[ts_code] / ma20[ts_code])
                            records.append((ts_code, date_str, 'price_to_ma20', ratio))

            batch.extend(records)

        except Exception as e:
            if i % 50 == 0:
                print(f'  [{i+1}] {date_str} ERROR: {e}')
            continue

        # 每 10 个日期批量写入一次
        if i % 10 == 9 and batch:
            try:
                _save_batch(batch)
                total_saved += len(batch)
                print(f'  [{i+1}/{len(todo_dates)}] {date_str}: +{len(batch)} 条, 累计 {total_saved:,}')
                batch = []
            except Exception as e:
                print(f'  save error: {e}')

    # 最后一批
    if batch:
        _save_batch(batch)
        total_saved += len(batch)
        print(f'  [FINAL] +{len(batch)} 条, 累计 {total_saved:,}')

    # 计算 Z-score 和百分位
    print()
    print('>>> 计算因子统计 (Z分数/百分位)...')
    for fid in ['momentum_1d', 'momentum_5d', 'momentum_20d',
                'volatility_20d', 'volume_ratio_20d', 'price_to_ma20']:
        # 读取该因子所有值
        vals = db.session.execute(
            text('SELECT factor_value FROM factor_values WHERE factor_id=:fid'),
            {'fid': fid}
        ).fetchall()
        if not vals:
            continue

        arr = np.array([v[0] for v in vals if v[0] is not None])
        if len(arr) < 2:
            continue

        mean, std = arr.mean(), arr.std()
        if std == 0:
            std = 1

        # 批量更新 Z-score
        z = (arr - mean) / std
        # 百分位
        sorted_arr = np.sort(arr)
        percentiles = np.searchsorted(sorted_arr, arr) / len(arr) * 100

        # 逐条更新（简化，大批量可用 executemany）
        # 这里用临时表方式：先读 ts_code+trade_date，再批量更新
        rows = db.session.execute(
            text('SELECT ts_code, trade_date, factor_value FROM factor_values WHERE factor_id=:fid'),
            {'fid': fid}
        ).fetchall()

        updates = []
        for row in rows:
            if row[2] is not None:
                z_val = (float(row[2]) - mean) / std
                pct = _searchsorted_percentile(sorted_arr, float(row[2]))
                updates.append({'z': round(z_val, 4), 'p': round(pct, 2),
                               'c': row[0], 'd': row[1], 'f': fid})

        # 分批更新
        for j in range(0, len(updates), 500):
            batch = updates[j:j+500]
            db.session.execute(
                text('UPDATE factor_values SET z_score=:z, percentile_rank=:p '
                     'WHERE ts_code=:c AND trade_date=:d AND factor_id=:f'),
                batch
            )
        db.session.commit()
        print(f'  {fid}: {len(updates):,} 条统计已更新')

    # 最终统计
    r = db.session.execute(
        text('SELECT COUNT(*), COUNT(DISTINCT factor_id), COUNT(DISTINCT trade_date) FROM factor_values')
    ).fetchone()
    print(f'\n>>> 完成！共 {r[0]:,} 条, {r[1]} 因子, {r[2]} 天')

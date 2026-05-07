"""
stock_business 大宽表数据生成脚本

将 stock_daily_basic、stock_factor、stock_basic、stock_moneyflow 等源表数据
聚合生成 stock_business 股票业务大宽表。

使用方式:
    cd app/utils && python stock_business_generator.py
    或指定日期范围: python stock_business_generator.py --start 2025-01-01 --end 2025-05-23
"""
import sys
import os
import argparse
from datetime import datetime

# 支持从项目根目录或 app/utils 目录运行
_project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

try:
    from app.utils.db_utils import DatabaseUtils
except ImportError:
    from db_utils import DatabaseUtils
import pandas as pd
import numpy as np


def ensure_stock_business_table(cursor):
    """确保 stock_business 表存在"""
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS `stock_business` (
      `ts_code` varchar(20) NOT NULL COMMENT 'TS股票代码',
      `trade_date` date NOT NULL COMMENT '交易日期',
      `stock_name` varchar(100) DEFAULT NULL COMMENT '股票名称',
      `daily_close` decimal(10,2) DEFAULT NULL COMMENT '当日收盘价',
      `turnover_rate` decimal(10,2) DEFAULT NULL COMMENT '换手率（%）',
      `turnover_rate_f` decimal(10,2) DEFAULT NULL COMMENT '换手率（自由流通股）',
      `volume_ratio` decimal(10,2) DEFAULT NULL COMMENT '量比',
      `pe` decimal(10,2) DEFAULT NULL COMMENT '市盈率',
      `pe_ttm` decimal(10,2) DEFAULT NULL COMMENT '市盈率（TTM）',
      `pb` decimal(10,2) DEFAULT NULL COMMENT '市净率',
      `ps` decimal(10,2) DEFAULT NULL COMMENT '市销率',
      `ps_ttm` decimal(10,2) DEFAULT NULL COMMENT '市销率（TTM）',
      `dv_ratio` decimal(10,2) DEFAULT NULL COMMENT '股息率（%）',
      `dv_ttm` decimal(10,2) DEFAULT NULL COMMENT '股息率（TTM）（%）',
      `total_share` decimal(20,2) DEFAULT NULL COMMENT '总股本（万股）',
      `float_share` decimal(20,2) DEFAULT NULL COMMENT '流通股本（万股）',
      `free_share` decimal(20,2) DEFAULT NULL COMMENT '自由流通股本（万）',
      `total_mv` decimal(20,2) DEFAULT NULL COMMENT '总市值（万元）',
      `circ_mv` decimal(20,2) DEFAULT NULL COMMENT '流通市值（万元）',
      `factor_open` decimal(10,2) DEFAULT NULL COMMENT '开盘价',
      `factor_high` decimal(10,2) DEFAULT NULL COMMENT '最高价',
      `factor_low` decimal(10,2) DEFAULT NULL COMMENT '最低价',
      `factor_pre_close` decimal(10,2) DEFAULT NULL COMMENT '昨收价',
      `factor_change` decimal(10,2) DEFAULT NULL COMMENT '涨跌额',
      `factor_pct_change` decimal(10,2) DEFAULT NULL COMMENT '涨跌幅',
      `factor_vol` decimal(20,2) DEFAULT NULL COMMENT '成交量',
      `factor_amount` decimal(20,2) DEFAULT NULL COMMENT '成交额',
      `factor_adj_factor` decimal(10,2) DEFAULT NULL COMMENT '复权因子',
      `factor_open_hfq` decimal(10,2) DEFAULT NULL COMMENT '后复权开盘价',
      `factor_open_qfq` decimal(10,2) DEFAULT NULL COMMENT '前复权开盘价',
      `factor_close_hfq` decimal(10,2) DEFAULT NULL COMMENT '后复权收盘价',
      `factor_close_qfq` decimal(10,2) DEFAULT NULL COMMENT '前复权收盘价',
      `factor_high_hfq` decimal(10,2) DEFAULT NULL COMMENT '后复权最高价',
      `factor_high_qfq` decimal(10,2) DEFAULT NULL COMMENT '前复权最高价',
      `factor_low_hfq` decimal(10,2) DEFAULT NULL COMMENT '后复权最低价',
      `factor_low_qfq` decimal(10,2) DEFAULT NULL COMMENT '前复权最低价',
      `factor_pre_close_hfq` decimal(10,2) DEFAULT NULL COMMENT '后复权昨收价',
      `factor_pre_close_qfq` decimal(10,2) DEFAULT NULL COMMENT '前复权昨收价',
      `factor_macd_dif` decimal(10,2) DEFAULT NULL COMMENT 'MACD DIF值',
      `factor_macd_dea` decimal(10,2) DEFAULT NULL COMMENT 'MACD DEA值',
      `factor_macd` decimal(10,2) DEFAULT NULL COMMENT 'MACD值',
      `factor_kdj_k` decimal(10,2) DEFAULT NULL COMMENT 'KDJ K值',
      `factor_kdj_d` decimal(10,2) DEFAULT NULL COMMENT 'KDJ D值',
      `factor_kdj_j` decimal(10,2) DEFAULT NULL COMMENT 'KDJ J值',
      `factor_rsi_6` decimal(10,2) DEFAULT NULL COMMENT 'RSI 6日',
      `factor_rsi_12` decimal(10,2) DEFAULT NULL COMMENT 'RSI 12日',
      `factor_rsi_24` decimal(10,2) DEFAULT NULL COMMENT 'RSI 24日',
      `factor_boll_upper` decimal(10,2) DEFAULT NULL COMMENT '布林上轨',
      `factor_boll_mid` decimal(10,2) DEFAULT NULL COMMENT '布林中轨',
      `factor_boll_lower` decimal(10,2) DEFAULT NULL COMMENT '布林下轨',
      `factor_cci` decimal(10,2) DEFAULT NULL COMMENT 'CCI指标',
      `moneyflow_pct_change` decimal(10,2) DEFAULT NULL COMMENT '涨跌幅',
      `moneyflow_latest` decimal(10,2) DEFAULT NULL COMMENT '最新价',
      `moneyflow_net_amount` decimal(20,2) DEFAULT NULL COMMENT '净流入额',
      `moneyflow_net_d5_amount` decimal(20,2) DEFAULT NULL COMMENT '5日净流入额',
      `moneyflow_buy_lg_amount` decimal(20,2) DEFAULT NULL COMMENT '大单买入额',
      `moneyflow_buy_lg_amount_rate` decimal(10,2) DEFAULT NULL COMMENT '大单买入额占比',
      `moneyflow_buy_md_amount` decimal(20,2) DEFAULT NULL COMMENT '中单买入额',
      `moneyflow_buy_md_amount_rate` decimal(10,2) DEFAULT NULL COMMENT '中单买入额占比',
      `moneyflow_buy_sm_amount` decimal(20,2) DEFAULT NULL COMMENT '小单买入额',
      `moneyflow_buy_sm_amount_rate` decimal(10,2) DEFAULT NULL COMMENT '小单买入额占比',
      `ma5` decimal(10,3) DEFAULT NULL COMMENT '5日移动平均线',
      `ma10` decimal(10,3) DEFAULT NULL COMMENT '10日移动平均线',
      `ma20` decimal(10,3) DEFAULT NULL COMMENT '20日移动平均线',
      `ma30` decimal(10,3) DEFAULT NULL COMMENT '30日移动平均线',
      `ma60` decimal(10,3) DEFAULT NULL COMMENT '60日移动平均线',
      `ma120` decimal(10,3) DEFAULT NULL COMMENT '120日移动平均线',
      PRIMARY KEY (`ts_code`,`trade_date`)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='股票业务大宽表';
    ''')


def generate_stock_business(conn, cursor, start_date=None, end_date=None, truncate=False):
    """
    生成 stock_business 数据
    
    :param conn: 数据库连接
    :param cursor: 游标
    :param start_date: 开始日期 YYYY-MM-DD
    :param end_date: 结束日期 YYYY-MM-DD
    :param truncate: 是否先清空表再生成
    """
    # 确定日期范围
    date_cond = ""
    params = []
    if start_date or end_date:
        conds = []
        if start_date:
            conds.append("db.trade_date >= %s")
            params.append(start_date)
        if end_date:
            conds.append("db.trade_date <= %s")
            params.append(end_date)
        date_cond = " AND " + " AND ".join(conds)

    ensure_stock_business_table(cursor)

    if truncate:
        cursor.execute("TRUNCATE TABLE stock_business")
        conn.commit()
        print("已清空 stock_business 表")

    # 1. 获取基础数据：以 stock_daily_basic 为主表
    base_sql = f"""
    SELECT 
        db.ts_code,
        db.trade_date,
        sb.name AS stock_name,
        db.close AS daily_close,
        db.turnover_rate,
        db.turnover_rate_f,
        db.volume_ratio,
        db.pe,
        db.pe_ttm,
        db.pb,
        db.ps,
        db.ps_ttm,
        db.dv_ratio,
        db.dv_ttm,
        db.total_share,
        db.float_share,
        db.free_share,
        db.total_mv,
        db.circ_mv,
        sf.open AS factor_open,
        sf.high AS factor_high,
        sf.low AS factor_low,
        sf.pre_close AS factor_pre_close,
        sf.`change` AS factor_change,
        sf.pct_change AS factor_pct_change,
        sf.vol AS factor_vol,
        sf.amount AS factor_amount,
        sf.adj_factor AS factor_adj_factor,
        sf.open_hfq AS factor_open_hfq,
        sf.open_qfq AS factor_open_qfq,
        sf.close_hfq AS factor_close_hfq,
        sf.close_qfq AS factor_close_qfq,
        sf.high_hfq AS factor_high_hfq,
        sf.high_qfq AS factor_high_qfq,
        sf.low_hfq AS factor_low_hfq,
        sf.low_qfq AS factor_low_qfq,
        sf.pre_close_hfq AS factor_pre_close_hfq,
        sf.pre_close_qfq AS factor_pre_close_qfq,
        sf.macd_dif AS factor_macd_dif,
        sf.macd_dea AS factor_macd_dea,
        sf.macd AS factor_macd,
        sf.kdj_k AS factor_kdj_k,
        sf.kdj_d AS factor_kdj_d,
        sf.kdj_j AS factor_kdj_j,
        sf.rsi_6 AS factor_rsi_6,
        sf.rsi_12 AS factor_rsi_12,
        sf.rsi_24 AS factor_rsi_24,
        sf.boll_upper AS factor_boll_upper,
        sf.boll_mid AS factor_boll_mid,
        sf.boll_lower AS factor_boll_lower,
        sf.cci AS factor_cci,
        mf.net_mf_amount AS moneyflow_net_amount,
        mf.buy_sm_amount AS moneyflow_buy_sm_amount,
        mf.buy_md_amount AS moneyflow_buy_md_amount,
        mf.buy_lg_amount AS moneyflow_buy_lg_amount,
        mf.buy_elg_amount AS moneyflow_buy_elg_amount
    FROM stock_daily_basic db
    LEFT JOIN stock_basic sb ON db.ts_code = sb.ts_code
    LEFT JOIN stock_factor sf ON db.ts_code = sf.ts_code AND db.trade_date = sf.trade_date
    LEFT JOIN stock_moneyflow mf ON db.ts_code = mf.ts_code AND db.trade_date = mf.trade_date
    WHERE 1=1 {date_cond}
    ORDER BY db.ts_code, db.trade_date
    """
    print("正在加载源表数据...")
    df = pd.read_sql(base_sql, conn, params=params if params else None)
    if df.empty:
        print("未找到符合条件的数据，请检查 stock_daily_basic、stock_factor、stock_basic 等源表是否有数据")
        return 0

    # 2. 计算资金流向衍生字段
    # 大单 = buy_lg + buy_elg, 总买入额 = sm + md + lg + elg
    df['buy_total'] = (
        df['moneyflow_buy_sm_amount'].fillna(0) +
        df['moneyflow_buy_md_amount'].fillna(0) +
        df['moneyflow_buy_lg_amount'].fillna(0) +
        df['moneyflow_buy_elg_amount'].fillna(0)
    )
    df['moneyflow_buy_lg_amount'] = df['moneyflow_buy_lg_amount'].fillna(0) + df['moneyflow_buy_elg_amount'].fillna(0)
    df['moneyflow_buy_lg_amount_rate'] = np.where(
        df['buy_total'] > 0,
        df['moneyflow_buy_lg_amount'] / df['buy_total'] * 100,
        None
    )
    df['moneyflow_buy_md_amount_rate'] = np.where(
        df['buy_total'] > 0,
        df['moneyflow_buy_md_amount'].fillna(0) / df['buy_total'] * 100,
        None
    )
    df['moneyflow_buy_sm_amount_rate'] = np.where(
        df['buy_total'] > 0,
        df['moneyflow_buy_sm_amount'].fillna(0) / df['buy_total'] * 100,
        None
    )
    # 大单买入额 = 大单 + 特大单（已在上方合并到 moneyflow_buy_lg_amount）
    df.drop(columns=['buy_total', 'moneyflow_buy_elg_amount'], inplace=True, errors='ignore')
    df['moneyflow_pct_change'] = df['factor_pct_change']
    df['moneyflow_latest'] = df['daily_close']

    # 3. 计算 5 日净流入额
    df = df.sort_values(['ts_code', 'trade_date'])
    df['moneyflow_net_d5_amount'] = df.groupby('ts_code')['moneyflow_net_amount'].transform(
        lambda x: x.rolling(5, min_periods=1).sum()
    )

    # 4. 计算均线（基于 daily_close）
    df['ma5'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(5, min_periods=1).mean()
    )
    df['ma10'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(10, min_periods=1).mean()
    )
    df['ma20'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(20, min_periods=1).mean()
    )
    df['ma30'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(30, min_periods=1).mean()
    )
    df['ma60'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(60, min_periods=1).mean()
    )
    df['ma120'] = df.groupby('ts_code')['daily_close'].transform(
        lambda x: x.rolling(120, min_periods=1).mean()
    )
    # 5. 准备插入的列
    insert_columns = [
        'ts_code', 'trade_date', 'stock_name', 'daily_close', 'turnover_rate', 'turnover_rate_f',
        'volume_ratio', 'pe', 'pe_ttm', 'pb', 'ps', 'ps_ttm', 'dv_ratio', 'dv_ttm',
        'total_share', 'float_share', 'free_share', 'total_mv', 'circ_mv',
        'factor_open', 'factor_high', 'factor_low', 'factor_pre_close', 'factor_change',
        'factor_pct_change', 'factor_vol', 'factor_amount', 'factor_adj_factor',
        'factor_open_hfq', 'factor_open_qfq', 'factor_close_hfq', 'factor_close_qfq',
        'factor_high_hfq', 'factor_high_qfq', 'factor_low_hfq', 'factor_low_qfq',
        'factor_pre_close_hfq', 'factor_pre_close_qfq',
        'factor_macd_dif', 'factor_macd_dea', 'factor_macd',
        'factor_kdj_k', 'factor_kdj_d', 'factor_kdj_j',
        'factor_rsi_6', 'factor_rsi_12', 'factor_rsi_24',
        'factor_boll_upper', 'factor_boll_mid', 'factor_boll_lower', 'factor_cci',
        'moneyflow_pct_change', 'moneyflow_latest', 'moneyflow_net_amount', 'moneyflow_net_d5_amount',
        'moneyflow_buy_lg_amount', 'moneyflow_buy_lg_amount_rate',
        'moneyflow_buy_md_amount', 'moneyflow_buy_md_amount_rate',
        'moneyflow_buy_sm_amount', 'moneyflow_buy_sm_amount_rate',
        'ma5', 'ma10', 'ma20', 'ma30', 'ma60', 'ma120'
    ]
    cols_to_insert = [c for c in insert_columns if c in df.columns]
    df_insert = df[cols_to_insert].copy()
    df_insert = df_insert.replace([np.inf, -np.inf], np.nan)

    # 6. 批量插入（使用 ON DUPLICATE KEY UPDATE 实现 upsert）
    placeholders = ', '.join(['%s'] * len(cols_to_insert))
    cols_str = ', '.join([f'`{c}`' for c in cols_to_insert])
    update_set = ', '.join([f"`{c}` = VALUES(`{c}`)" for c in cols_to_insert if c not in ('ts_code', 'trade_date')])
    sql = f"""
    INSERT INTO stock_business ({cols_str})
    VALUES ({placeholders})
    ON DUPLICATE KEY UPDATE {update_set}
    """
    batch_size = 1000
    total = 0
    for i in range(0, len(df_insert), batch_size):
        batch = df_insert.iloc[i:i + batch_size]
        rows = [tuple(
            None if (isinstance(v, float) and np.isnan(v)) else v
            for v in row
        ) for row in batch.values]
        cursor.executemany(sql, rows)
        total += len(batch)
        conn.commit()
        if (i // batch_size + 1) % 10 == 0:
            print(f"  已写入 {total} 条...")
    print(f"stock_business 生成完成，共写入 {total} 条记录")
    return total


def main():
    parser = argparse.ArgumentParser(description='生成 stock_business 大宽表数据')
    parser.add_argument('--start', type=str, help='开始日期 YYYY-MM-DD')
    parser.add_argument('--end', type=str, help='结束日期 YYYY-MM-DD')
    parser.add_argument('--truncate', action='store_true', help='先清空表再生成（默认追加/更新）')
    parser.add_argument('--full', action='store_true', help='全量生成，等同于 --truncate 且无日期限制')
    args = parser.parse_args()

    if args.full:
        args.truncate = True
        args.start = None
        args.end = None

    conn, cursor = DatabaseUtils.connect_to_mysql()
    try:
        generate_stock_business(
            conn, cursor,
            start_date=args.start,
            end_date=args.end,
            truncate=args.truncate
        )
    finally:
        cursor.close()
        conn.close()


if __name__ == '__main__':
    main()

"""
基于 Baostock 的 A 股数据下载脚本（Python 3.13 兼容）
"""
import time
import baostock as bs
import pymysql
from datetime import datetime


class BaostockDownloader:

    def __init__(self):
        self.conn = pymysql.connect(
            host='localhost', user='root', password='123456',
            database='stock_cursor', charset='utf8mb4'
        )

    # ============================================================
    # 1. 股票基本信息
    # ============================================================

    def download_stock_basic(self):
        print('>>> 下载股票基本信息...')
        bs.login()
        rs = bs.query_stock_basic()
        cursor = self.conn.cursor()
        records = []
        while (rs.error_code == '0') and rs.next():
            row = rs.get_row_data()
            code, name, ipo_date = row[0], row[1], row[2]
            ts_code = f"{code}.{'SH' if code.startswith('sh') else 'SZ'}"
            symbol = code.replace('sh.', '').replace('sz.', '')
            records.append((ts_code, symbol, name, None, None, ipo_date if ipo_date else None))

        cursor.execute('TRUNCATE TABLE stock_basic')
        sql = ('REPLACE INTO stock_basic '
               '(ts_code, symbol, name, area, industry, list_date) '
               'VALUES (%s,%s,%s,%s,%s,%s)')
        cursor.executemany(sql, records)
        self.conn.commit()
        cursor.close()
        bs.logout()
        print(f'    写入 {len(records)} 条')
        return len(records)

    # ============================================================
    # 2. 日线行情
    # ============================================================

    def download_daily_history(self, start_date: str, end_date: str,
                                sleep: float = 0.2, batch_size: int = 500):
        print(f'>>> 下载日线: {start_date} ~ {end_date}')

        cursor = self.conn.cursor()
        cursor.execute('SELECT ts_code FROM stock_basic')
        stocks = [row[0] for row in cursor.fetchall()]
        total_stocks = len(stocks)
        print(f'    共 {total_stocks} 只股票')

        bs.login()
        total = 0

        for i, ts_code in enumerate(stocks):
            try:
                symbol = ts_code.split('.')[0]
                prefix = 'sh' if ts_code.endswith('SH') else 'sz'
                baostock_code = f'{prefix}.{symbol}'

                rs = bs.query_history_k_data_plus(
                    baostock_code,
                    'date,open,high,low,close,preclose,volume,amount,pctChg',
                    start_date=start_date, end_date=end_date,
                    frequency='d', adjustflag='3'
                )

                records = []
                while (rs.error_code == '0') and rs.next():
                    row = rs.get_row_data()
                    if not row[0]:
                        continue
                    records.append((
                        ts_code, row[0],
                        float(row[1]), float(row[2]), float(row[3]),
                        float(row[4]), float(row[5]),
                        None, float(row[8]),
                        float(row[6]), float(row[7])
                    ))

                if records:
                    sql = (
                        'INSERT INTO stock_daily_history '
                        '(ts_code, trade_date, open, high, low, close, pre_close, '
                        '`change`, pct_chg, vol, amount) '
                        'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s) '
                        'ON DUPLICATE KEY UPDATE open=VALUES(open), high=VALUES(high), '
                        'low=VALUES(low), close=VALUES(close), pre_close=VALUES(pre_close), '
                        'vol=VALUES(vol), amount=VALUES(amount)'
                    )
                    cursor.executemany(sql, records)
                    self.conn.commit()
                    total += len(records)

                if i % 500 == 0:
                    pct = (i + 1) / total_stocks * 100
                    print(f'    [{i+1}/{total_stocks} {pct:.1f}%] {ts_code}: {len(records)} 条, total={total}')

                time.sleep(sleep)

            except Exception as e:
                if i % 200 == 0:
                    print(f'    [{i+1}] {ts_code} skip: {type(e).__name__}')
                continue

        bs.logout()
        cursor.close()
        print(f'    日线完成，共 {total} 条')
        return total

    # ============================================================
    # 3. 填充 daily_basic
    # ============================================================

    def fill_daily_basic(self):
        print('>>> 填充 daily_basic...')
        cursor = self.conn.cursor()
        cursor.execute(
            'INSERT IGNORE INTO stock_daily_basic (ts_code, trade_date, close) '
            'SELECT ts_code, trade_date, close FROM stock_daily_history'
        )
        n = cursor.rowcount
        self.conn.commit()
        cursor.close()
        print(f'    填补 {n} 条')
        return n

    # ============================================================
    # 批量运行
    # ============================================================

    def run_all(self, start_date: str = '2025-01-01', end_date: str = None):
        if end_date is None:
            end_date = datetime.now().strftime('%Y-%m-%d')

        print('=' * 60)
        print(f'Baostock 数据下载: {start_date} ~ {end_date}')
        print('=' * 60)

        self.download_stock_basic()
        self.download_daily_history(start_date, end_date)
        self.fill_daily_basic()

        print('=' * 60)
        print('完成')
        print('=' * 60)


if __name__ == '__main__':
    d = BaostockDownloader()
    # 下载约 1 年数据
    d.run_all(start_date='2025-05-01', end_date='2026-05-09')

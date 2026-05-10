"""
基于 akshare 的数据下载脚本
"""
import time
import akshare as ak
import pymysql
from datetime import datetime, timedelta


class AkshareDownloader:

    def __init__(self):
        self.conn = pymysql.connect(
            host='localhost', user='root', password='123456',
            database='stock_cursor', charset='utf8mb4'
        )

    def _retry(self, fn, name, max_retries=3, delay=2):
        for attempt in range(max_retries):
            try:
                return fn()
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f'    {name} retry {attempt+1}/{max_retries}: {type(e).__name__}')
                    time.sleep(delay)
                else:
                    raise

    # ============================================================
    # 1. 股票基本信息
    # ============================================================

    def download_stock_basic(self):
        print('>>> 下载股票基本信息...')
        cursor = self.conn.cursor()

        df = self._retry(lambda: ak.stock_info_a_code_name(), 'stock_info_a_code_name')
        df.columns = ['symbol', 'name']

        records = []
        for _, row in df.iterrows():
            code = row['symbol']
            name = row['name']
            ts_code = f"{code}.{'SH' if code.startswith('6') else 'SZ'}"
            records.append((ts_code, code, name, None, None, None))

        cursor.execute('TRUNCATE TABLE stock_basic')
        sql = ('REPLACE INTO stock_basic '
               '(ts_code, symbol, name, area, industry, list_date) '
               'VALUES (%s,%s,%s,%s,%s,%s)')
        cursor.executemany(sql, records)
        self.conn.commit()
        cursor.close()
        print(f'    写入 {len(records)} 条')
        return len(records)

    # ============================================================
    # 2. 日线行情（逐只股票下载）
    # ============================================================

    def download_daily_history(self, start_date: str, end_date: str,
                                sleep: float = 0.3, batch_size: int = 200):
        print(f'>>> 下载日线行情: {start_date} ~ {end_date}')

        # 获取股票列表
        cursor = self.conn.cursor()
        cursor.execute('SELECT ts_code FROM stock_basic')
        stocks = [row[0] for row in cursor.fetchall()]
        print(f'    共 {len(stocks)} 只股票')

        start_fmt = f'{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}'
        end_fmt = f'{end_date[:4]}-{end_date[4:6]}-{end_date[6:8]}'
        total = 0

        for i, ts_code in enumerate(stocks):
            try:
                symbol = ts_code.split('.')[0]

                def fetch():
                    return ak.stock_zh_a_hist(
                        symbol=symbol, period='daily',
                        start_date=start_fmt, end_date=end_fmt, adjust='qfq'
                    )

                df = self._retry(fetch, f'{symbol}', max_retries=2, delay=1)

                if df is None or df.empty:
                    continue

                records = []
                for _, row in df.iterrows():
                    records.append((
                        ts_code, row['日期'],
                        float(row['开盘']), float(row['最高']), float(row['最低']),
                        float(row['收盘']), float(row.get('昨收', 0)),
                        float(row.get('涨跌额', 0)), float(row.get('涨跌幅', 0)),
                        float(row['成交量']), float(row['成交额'])
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
                    pct = (i + 1) / len(stocks) * 100
                    print(f'    [{i+1}/{len(stocks)} {pct:.1f}%] {ts_code}: {len(records)} 条, total={total}')

                time.sleep(sleep)

            except Exception as e:
                if i % 200 == 0:
                    print(f'    [{i+1}/{len(stocks)}] {ts_code} skip: {type(e).__name__}')
                continue

        cursor.close()
        print(f'    日线完成，共 {total} 条')
        return total

    # ============================================================
    # 3. 填充 daily_basic
    # ============================================================

    def extract_daily_basic_from_history(self):
        print('>>> 从日线数据填充 daily_basic...')
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

    def run_all(self, start_date: str = '20250101', end_date: str = None):
        if end_date is None:
            end_date = datetime.now().strftime('%Y%m%d')

        print('=' * 60)
        print(f'Akshare 数据下载: {start_date} ~ {end_date}')
        print('=' * 60)

        self.download_stock_basic()
        self.download_daily_history(start_date, end_date)
        self.extract_daily_basic_from_history()

        print('=' * 60)
        print('完成')
        print('=' * 60)


if __name__ == '__main__':
    downloader = AkshareDownloader()
    # 默认下载最近 60 个交易日
    start = (datetime.now() - timedelta(days=90)).strftime('%Y%m%d')
    end = datetime.now().strftime('%Y%m%d')
    downloader.run_all(start, end)

"""
快速导入 SQL dump — 用 Python 批量 INSERT 替代逐条写入
"""
import re
import pymysql

SQL_FILE = 'D:/quantitative_analysis/stock_data/stock_daily_history.sql'
BATCH_SIZE = 10000
TARGET_TABLE = None

# 列定义映射，从 SQL 文件结构推断
COLUMNS = [
    'ts_code', 'trade_date', 'open', 'high', 'low', 'close',
    'pre_close', 'change_c', 'pct_chg', 'vol', 'amount'
]

conn = pymysql.connect(
    host='localhost', user='root', password='123456',
    database='stock_cursor', charset='utf8mb4'
)
cursor = conn.cursor()

# 先执行 DDL（CREATE TABLE）
print('>>> 执行 DDL...')
ddl_lines = []
with open(SQL_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        if line.strip().startswith('INSERT INTO'):
            break
        ddl_lines.append(line)

ddl = ''.join(ddl_lines)
for stmt in ddl.split(';'):
    stmt = stmt.strip()
    if stmt:
        try:
            cursor.execute(stmt)
        except Exception as e:
            if 'already exists' not in str(e) and 'Duplicate' not in str(e):
                print(f'  DDL skip: {e}')
conn.commit()
print('>>> DDL 完成，开始导入数据...')

# 解析 INSERT 行并批量写入
batch = []
total = 0
line_count = 0

with open(SQL_FILE, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        if not line.startswith('INSERT INTO'):
            continue

        line_count += 1
        # 解析 VALUES 子句: VALUES ('000001.SZ','2025-01-02',11.73,...);
        m = re.search(r"VALUES\s*\((.+)\);?\s*$", line, re.IGNORECASE)
        if not m:
            continue

        raw = m.group(1)
        # 按逗号分割，但要处理引号内的逗号
        # 简单处理：按 ',' 分割后用 strip("'") 去掉引号
        parts = raw.split(',')
        values = []
        for p in parts:
            p = p.strip().strip("'")
            values.append(p)

        if len(values) != len(COLUMNS):
            continue  # 跳过格式异常的行

        batch.append(values)

        if len(batch) >= BATCH_SIZE:
            placeholders = ', '.join(['(' + ', '.join(['%s'] * len(COLUMNS)) + ')'] * len(batch))
            flat = [item for row in batch for item in row]
            sql = f'INSERT INTO stock_daily_history ({", ".join(COLUMNS)}) VALUES {placeholders}'
            cursor.execute(sql, flat)
            conn.commit()
            total += len(batch)
            print(f'  {total:,} / {line_count:,} lines parsed', end='\r')
            batch = []

# 处理最后一批
if batch:
    placeholders = ', '.join(['(' + ', '.join(['%s'] * len(COLUMNS)) + ')'] * len(batch))
    flat = [item for row in batch for item in row]
    sql = f'INSERT INTO stock_daily_history ({", ".join(COLUMNS)}) VALUES {placeholders}'
    cursor.execute(sql, flat)
    conn.commit()
    total += len(batch)

cursor.close()
conn.close()
print(f'\n>>> 完成！共 {total:,} 行')

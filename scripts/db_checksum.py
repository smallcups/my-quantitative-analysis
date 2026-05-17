"""快速检测两台设备 MySQL 数据是否一致。在两台设备上分别运行，对比输出即可。"""
from app import create_app
from app.extensions import db
from sqlalchemy import text, inspect

app = create_app('default')
with app.app_context():
    inspector = inspect(db.engine)
    tables = sorted(inspector.get_table_names())
    for t in tables:
        try:
            cnt = db.session.execute(text(f'SELECT COUNT(*) FROM `{t}`')).scalar()
            row = db.session.execute(text(f'CHECKSUM TABLE `{t}`')).fetchone()
            cksum = row[1] if row else 'N/A'
            print(f'{t:<30}  rows={cnt:>10}  checksum={cksum:>12}')
        except Exception as e:
            print(f'{t:<30}  ERR: {e}')

import sys
from app import create_app
print('1. Starting...', flush=True)

app = create_app('default')
print('2. App created', flush=True)

with app.app_context():
    print('3. Importing...', flush=True)
    from app.services.factor_optimizer import FactorOptimizer

    print('4. Creating optimizer...', flush=True)
    opt = FactorOptimizer()
    print(f'5. Optimizer ready, builtin factors loaded', flush=True)

    # 只用最近一个日期快速测试
    from app.extensions import db
    from sqlalchemy import text
    r = db.session.execute(text(
        'SELECT DISTINCT trade_date FROM factor_values WHERE factor_id="momentum_1d" ORDER BY trade_date DESC LIMIT 5'
    )).fetchall()
    dates = [row[0].strftime('%Y-%m-%d') for row in r]
    print(f'6. Available dates: {dates}', flush=True)

    # 只测一个日期一个因子
    test_date = dates[0]
    print(f'7. Testing single IC: momentum_1d @ {test_date}...', flush=True)

    result = opt.compute_rank_ic('momentum_1d', test_date, forward_period=5)
    print(f'8. Result: {result.get("ic_value", result.get("error"))}', flush=True)

    # 如果单日 OK，跑 5 个日期的滚动 IC
    print(f'9. Testing rolling IC over 5 dates...', flush=True)
    start = dates[-1]
    end = dates[0]

    stats = opt.compute_rolling_ic_statistics('momentum_1d', start, end, forward_period=5)
    if stats.get('success'):
        print(f'10. IC_mean={stats["ic_mean"]:.4f}, IC_IR={stats["ic_ir"]:.2f}', flush=True)
    else:
        print(f'10. Error: {stats.get("error")}', flush=True)

    print('DONE', flush=True)

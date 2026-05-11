from app import create_app
import json

app = create_app('default')
with app.app_context():
    from app.services.factor_optimizer import FactorOptimizer
    from app.extensions import db
    from sqlalchemy import text

    opt = FactorOptimizer()

    # 获取有因子值的日期范围
    r = db.session.execute(text(
        'SELECT MIN(trade_date), MAX(trade_date), COUNT(DISTINCT trade_date) FROM factor_values'
    )).fetchone()

    print(f'数据范围: {r[0]} ~ {r[1]}, {r[2]} 个日期')
    print()

    # 跑分析 + 筛选 + 权重
    result = opt.get_optimized_weights(
        evaluation_date=str(r[1]),
        forward_period=5,
        ic_ir_threshold=0.1,
        max_correlation=0.7,
        min_factors=2,
        max_factors=5
    )

    if 'error' in result:
        print(f'ERROR: {result["error"]}')
    else:
        print(f'=== 选中 {len(result["selected_factors"])} 个因子 ===')
        for fid, info in result['selected_factors'].items():
            print(f'  {fid:20s}: IC_IR={info["ic_ir"]:7.2f}  IC_mean={info["ic_mean"]:+.4f}  weight={info["weight"]:.3f}')

        print()
        print('=== 最终权重 ===')
        print(json.dumps(result['weights'], indent=2))

        # 验证
        w = result['weights']
        print(f'\n权重和: {sum(w.values()):.6f}')

        # 查看所有因子的IC
        print(f'\n=== 全部因子IC统计 ===')
        latest = opt._get_latest_effectiveness(5)
        for f in sorted(latest, key=lambda x: abs(x['ic_ir']), reverse=True):
            if f.get('success'):
                sign = '+' if f['ic_mean'] > 0 else ''
                selected = ' *' if f['factor_id'] in w else ''
                print(f'  {f["factor_id"]:20s}: IC_mean={sign}{f["ic_mean"]:.4f}  IC_IR={f["ic_ir"]:.2f}  WinRate={f["ic_win_rate"]:.0%}{selected}')

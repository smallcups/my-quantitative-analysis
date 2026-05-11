from app import create_app
app = create_app('default')
with app.app_context():
    from app.services.factor_optimizer import FactorOptimizer
    import json

    opt = FactorOptimizer()
    result = opt.get_optimized_weights('2025-03-17', forward_period=5, ic_ir_threshold=0.1)

    print('=== 滚动IC统计 ===')
    latest = opt._get_latest_effectiveness(5)
    for f in sorted(latest, key=lambda x: abs(x['ic_ir']), reverse=True):
        if f.get('success'):
            sign = '+' if f['ic_mean'] > 0 else ''
            print(f'  {f["factor_id"]:25s}: IC_mean={sign}{f["ic_mean"]:.4f}  IC_IR={f["ic_ir"]:.2f}  WinRate={f["ic_win_rate"]:.0%}')

    if 'error' in result:
        print(f'\nERROR: {result["error"]}')
    else:
        print(f'\n=== 筛选结果 ({len(result["selected_factors"])}个因子) ===')
        for fid, info in result['selected_factors'].items():
            print(f'  {fid:25s}: IC_IR={info["ic_ir"]:7.2f}  weight={info["weight"]:.3f}')

        print(f'\n=== 最终权重 ===')
        print(json.dumps(result['weights'], indent=2))

        print(f'\n=== 验证 ===')
        w = result['weights']
        print(f'  权重和: {sum(w.values()):.6f}')
        # 被过滤的因子
        selected = set(w.keys())
        all_factors = {f['factor_id'] for f in latest if f.get('success')}
        rejected = all_factors - selected
        if rejected:
            print(f'  被过滤: {rejected}')

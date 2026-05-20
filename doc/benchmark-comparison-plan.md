# 回测基准对比（沪深300）开发计划

## 当前状态
- CSI 300 日线数据已下载并写入 `stock_daily_history` 表（000300.SH，5909行）
- `_get_benchmark_returns` 是空函数，返回 `[]`
- 前端 `benchmark_returns` 字段未被使用

## 后端改动（backtest_engine.py）

### 1. 重写 `_get_benchmark_returns`（行784）
**现状**：return []
**改为**：
- 查询 stock_daily_history WHERE ts_code='000300.SH' AND trade_date BETWEEN start AND end
- 计算基准累计收益率曲线
- 按 portfolio_values 调仓日对齐基准收益率
- 计算基准指标：total_return, annualized_return, volatility, max_drawdown
- 返回 dict：{name, total_return, annualized_return, volatility, max_drawdown, aligned_returns, daily_data}

### 2. 更新 `run_backtest`（行229-244）
- 传 portfolio_values 给 _get_benchmark_returns
- 计算超额收益、跟踪误差、信息比率
- 将对比指标合并到 performance_metrics
- benchmark_returns 从 [] 改为 {}

## 前端改动（backtest.html）

### 3. 指标区新增基准对照行（HTML，在回测结果区）
```
BM Return | BM Annual | BM Drawdown | Excess Return | Info Ratio | Tracking Err
```
默认隐藏（display:none），有基准数据时显示。

### 4. JS 填充基准指标（在 renderBacktestResult 函数内，不碰 calcAutoWeights）
- 读取 data.benchmark_returns
- 填充基准指标行
- 超额收益正绿色负红色

### 5. JS 图表双线（drawReturnsChart 函数）
- 新增第二个参数 benchmarkData
- 基准线：灰色虚线
- 策略线：蓝色实线
- Tooltip 显示两条线

## 不改动的部分（避免上次的 JS 报错）
- calcAutoWeights 及周边 override 逻辑完全不动
- updateHybridModelList 不动
- 其他 JS 函数不动

## 改动量
- 后端：~100 行
- 前端：~50 行 HTML + ~40 行 JS

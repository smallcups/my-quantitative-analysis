# 自动因子选择与权重优化原理

## 1. 核心问题

多因子选股系统面临两个基本问题：

- **哪些因子真的能预测股票收益？**（因子有效性）
- **每个因子应该占多大权重？**（权重分配）

没有自动化方法时，这两件事只能靠人工拍板，主观、无法适应市场变化、不可复现。

本文介绍的 Rank IC 方法是量化投资中评估因子有效性的标准方法，能自动筛选最优因子并根据历史表现分配数据驱动权重。

## 2. 核心指标：Rank IC

### 2.1 定义

**Rank IC**（Rank Information Coefficient）衡量一个因子的预测能力。它定义为：

```
Rank IC(T, f, N) = SpearmanRho( factor_value(T), forward_return(T, T+N) )
```

其中：
- `factor_value(T)` = T 日所有股票的因子值（横截面）
- `forward_return(T, T+N)` = 从 T 日到 T+N 日的股票收益率
- `SpearmanRho` = 斯皮尔曼秩相关系数

### 2.2 为什么用 Spearman 而不是 Pearson？

股票因子值和收益率通常不服从正态分布，有肥尾特征。Pearson 相关系数假设正态分布且对异常值敏感。Spearman 秩相关只看排名不看绝对值，对金融数据中常见的极端值天然鲁棒。

### 2.3 IC 值是什么意思？

| IC 值 | 含义 |
|-------|------|
| +0.10 | 因子值高的股票未来确实涨得多，正向预测 |
| -0.10 | 因子值高的股票未来反而跌得多，反向预测（均值回归） |
| ~0.00 | 因子值和未来收益无关，没有预测能力 |

## 3. 滚动 IC 统计

单日 IC 只是一个快照。要评价一个因子在整段时间的表现，需要在每个交易日都算一次 IC，得到 IC 时间序列，然后计算四个聚合指标：

```
IC_mean      = (1/N) * Σ IC_i                   平均预测能力
IC_std       = √( (1/(N-1)) * Σ (IC_i - IC_mean)² )  稳定性
IC_IR        = IC_mean / IC_std                  信息比率（核心）
IC_win_rate  = COUNT(IC_i > 0) / N               胜率（IC>0 的天数占比）
```

### 3.1 为什么 IC_IR 是核心？

IC_IR 同时衡量预测能力和稳定性。看两个因子的对比：

| 因子 | IC 均值 | IC 标准差 | IC_IR |
|------|---------|----------|-------|
| A | 0.05 | 0.02 | **2.5** |
| B | 0.10 | 0.10 | 1.0 |

因子 B 的平均 IC 更高，但波动极大（周一预测很准、周二完全随机）。因子 A 虽然平均 IC 只有 B 的一半，但非常稳定。**因子 A 优于 B**，因为交易策略需要的是可靠的预测，不是忽好忽坏的运气。

## 4. 单日 IC 计算（算法流程）

```
1. 获取 T 日所有股票的因子值
   → factor_df: ts_code, factor_value

2. 获取 T 日所有股票的收盘价
   → current_close per stock

3. 获取 T+N 日所有股票的收盘价
   → future_close per stock

4. 配对计算未来收益率
   forward_return = (future_close - current_close) / current_close

5. 合并因子值和收益率，计算 Spearman 秩相关
   ic, p_value = spearmanr(factor_values, forward_returns)
```

## 5. 因子筛选（两步法）

### 5.1 第一步：IC_IR 阈值过滤

所有 |IC_IR| < 阈值的因子直接淘汰。|IC_IR| 接近零意味着没有统计学意义的预测能力。

```
valid = [f for f in all_factors if abs(f.ic_ir) > threshold]

如果通过数不足 min_factors，自动放宽阈值
  取 |IC_IR| 最高的 N 个因子作为保底
```

### 5.2 第二步：相关性去冗余

高度相关的因子提供的是重复信息。比如 momentum_5d 和 momentum_20d 都是动量类因子，同时选入等于给动量信号双倍权重却没有增加新信息。

使用贪心算法去冗余：

```
1. 计算所有因子的 Spearman 相关性矩阵
2. 按 |IC_IR| 从高到低排序
3. 遍历排序后的因子：
   如果新因子与已选中的某个因子相关系数 > max_correlation（默认 0.7）
     跳过（冗余）
   否则
     加入已选集合
```

## 6. 权重计算

选定因子后，权重按 |IC_IR| 比例分配，归一化到和为 1：

```
weight_i = |IC_IR_i| / Σ |IC_IR_j|
```

三种可选方法：

| 方法 | 公式 | 适用场景 |
|------|------|---------|
| ic_ir_weighted（默认） | ∝ |IC_IR| | 综合最优 |
| ic_mean_weighted | ∝ |IC_mean| | 强调原始信号强度 |
| equal_weight | 1/N | 基准对比 |

## 7. 端到端流程

```
真实行情数据 (stock_daily_history, 147万行)
    ↓
因子计算 (scripts/calculate_factors.py)
  → 6个技术面因子 × 272个交易日 → factor_values 837万行
    ↓
IC 分析 (FactorOptimizer.analyze_all_factors)
  → 每个因子×每个交易日 算单日IC
  → 滚动统计: IC_mean, IC_IR, IC_win_rate
    ↓
因子筛选 (FactorOptimizer.select_factors)
  → IC_IR 阈值过滤 + 相关性去冗余
  → 6个候选中选出4个
    ↓
权重计算 (FactorOptimizer._compute_weights)
  → |IC_IR| 归一化
  → {volatility_20d: 0.423, momentum_5d: 0.301, ...}
    ↓
股票打分 (StockScoringEngine._rank_ic_scoring)
  → 因子值 × 权重 → 综合得分 → 排名 → Top N 选股
    ↓
回测验证 (BacktestEngine)
  → 每月调仓 → 绩效指标
```

## 8. 真实数据结果

分析区间：2025-01-03 ~ 2025-04-15，6 个技术面因子，66 个交易日：

| 因子 | IC均值 | IC_IR | 胜率 | 选中？ | 权重 |
|------|--------|-------|------|--------|------|
| volatility_20d | -0.1566 | -0.64 | 29% | ✅ | 42.3% |
| momentum_5d | -0.0533 | -0.45 | 26% | ✅ | 30.1% |
| momentum_20d | -0.0376 | -0.24 | 39% | ✅ | 15.7% |
| momentum_1d | -0.0289 | -0.18 | 40% | ✅ | 12.0% |
| volume_ratio_20d | -0.0015 | -0.02 | 50% | ❌ | IC_IR 过低 |
| price_to_ma20 | -0.0115 | -0.16 | 47% | ❌ | 冗余 |

**关键发现**：

1. 该时段所有因子 IC 均为负值 → A股 Q1 处于**均值回归**行情
2. volatility_20d 权重最高（42.3%），因为它的 |IC_IR| 最大
3. volume_ratio_20d 被过滤：IC 接近零，没有预测力
4. price_to_ma20 被去冗余：与已选动量因子高度相关
5. 权重精确归一化，和 = 1.0

## 9. 与手动权重的对比

| | 手动/等权重 | 自动 Rank IC |
|------|------------|-------------|
| 权重来源 | 主观判断 | 历史数据 |
| 噪声因子 | 同样参与 | 自动过滤 |
| 冗余因子 | 可能重复计入 | 自动去重 |
| 适应性 | 写死不变化 | 换区间重新算即更新 |
| 可复现性 | 差 | 好（输入相同输出相同） |

## 10. 使用方式

**方式一：API 直接调用**
```
POST /api/ml-factor/factors/auto-weight
{ "evaluation_date": "2025-04-01", "forward_period": 5, ... }
→ 返回最优权重
```

**方式二：前端优化页面**
```
/ml-factor/optimization
→ 配置参数 → 分析 → 权重柱状图 → 一键回测对比
```

**方式三：回测页面集成**
```
/ml-factor/backtest
→ 评分方法选"自动 IC 权重" → 计算最优权重 → 开始回测
```

**方式四：代码直接调用**
```python
from app.services.factor_optimizer import FactorOptimizer
result = FactorOptimizer().get_optimized_weights('2025-04-01', forward_period=5)
# result = {'weights': {...}, 'selected_factors': {...}}
```

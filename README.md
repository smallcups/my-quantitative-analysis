 一个基于 Python/Flask 的 A 股量化选股 Web                                                                             
  系统，整合因子计算、机器学习、组合优化与回测全流程。项目处于学习/演示阶段，作者声明"未完成开发"。                     
                                                                                                                        
  技术栈                                                                                                                
                                                                                                                        
  - 后端：Python 3.8+ / Flask / SQLAlchemy / WebSocket（eventlet）                                                      
  - 数据：MySQL（推荐）或 SQLite；通过 tushare 和 baostock 拉取行情/基本面/分钟线/资金流/筹码分布                       
  - 算法：Pandas / NumPy / Scikit-learn / XGBoost / LightGBM / CVXPY                                                    
  - 前端：Bootstrap 5 + Jinja 模板（另有 Vue 新版演示站 http://223.4.156.201:5173/）                                    
                                                                                                                        
  目录结构                                                                                                              
                                                                                                                        
  app/            
    api/         # REST + WebSocket 接口（ml_factor、实时监控、text2sql 等）
    services/    # 核心引擎：factor_engine、ml_models、stock_scoring、                                                  
                 # portfolio_optimizer、backtest_engine、实时模块、LLM/NLP                                              
    utils/       # tushare/baostock 数据下载脚本、MA/CYQ 计算器、缓存、DB                                               
    routes/ main/ websocket/ templates/ static/                                                                         
  init/          # 数据库初始化（因子系统、实时库、text2sql、交易信号）                                                 
  docs/          # 财务报表/ML 因子文档与分析报告                                                                       
  config.py      # 配置（DB、日志等）                                                                                   
  run.py / run_system.py / quick_start.py  # 启动入口                                                                   
  start.sh / start.bat                                                                                                  
                                                                                                                        
  核心功能模块                                                                                                          
   
  1. 因子引擎：12 个内置因子（动量、波动率、RSI、换手率、PE/PB/ROE 等），支持自定义公式                                 
  2. ML 管理器：随机森林 / XGBoost / LightGBM 训练与预测
  3. 打分引擎：因子打分 + ML 打分 + 综合评分                                                                            
  4. 组合优化器：等权重 / 均值-方差 / 风险平价（CVXPY）                                                                 
  5. 回测引擎：收益、年化波动、夏普、最大回撤、胜率、卡尔玛                                                             
  6. 实时模块：实时数据/指标/信号/风险/监控/报告（WebSocket 推送）                                                      
  7. Text2SQL + LLM：自然语言查询股票数据                                                                               
                                                                                                                        
  启动方式                                                                                                              
                                                                                                                        
  pip install -r requirements.txt
  python run_system.py   # 交互式启动器：依赖检查 / 初始化 DB / 启动 Web / 演示
  # Web: http://localhost:5000     

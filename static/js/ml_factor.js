// 多因子选股系统前端JavaScript

// 全局变量
let currentSection = 'dashboard';
let selectedStocks = [];
let optimizationResults = null;

// API基础URL
const API_BASE_URL = '/api/ml-factor';

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    initializePage();
    loadDashboardData();
    setupEventListeners();
    setDefaultDate();
});

// 初始化页面
function initializePage() {
    // 设置侧边栏导航
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.addEventListener('click', function(e) {
            e.preventDefault();
            const section = this.getAttribute('data-section');
            showSection(section);
        });
    });
}

// 设置事件监听器
function setupEventListeners() {
    // 选股方法切换
    document.getElementById('selection-method').addEventListener('change', function() {
        toggleSelectionMethod(this.value);
    });

    // 选股表单提交
    document.getElementById('selection-form').addEventListener('submit', function(e) {
        e.preventDefault();
        performStockSelection();
    });

    // 组合优化表单提交
    document.getElementById('optimization-form').addEventListener('submit', function(e) {
        e.preventDefault();
        performPortfolioOptimization();
    });
}

// 设置默认日期
function setDefaultDate() {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    
    const dateString = yesterday.toISOString().split('T')[0];
    document.getElementById('trade-date').value = dateString;
}

// 显示指定页面
function showSection(sectionName) {
    // 隐藏所有内容区域
    const sections = document.querySelectorAll('.content-section');
    sections.forEach(section => {
        section.classList.remove('active');
    });

    // 显示指定区域
    const targetSection = document.getElementById(sectionName);
    if (targetSection) {
        targetSection.classList.add('active');
    }

    // 更新导航状态
    const navLinks = document.querySelectorAll('.sidebar .nav-link');
    navLinks.forEach(link => {
        link.classList.remove('active');
        if (link.getAttribute('data-section') === sectionName) {
            link.classList.add('active');
        }
    });

    // Update page title
    const titles = {
        'dashboard': 'Dashboard',
        'factor-management': 'Factor Management',
        'model-management': 'Model Management',
        'stock-selection': 'Stock Selection',
        'portfolio-optimization': 'Portfolio Optimization',
        'analysis': 'Analysis Report',
        'backtest': 'Backtest Validation'
    };
    document.getElementById('page-title').textContent = titles[sectionName] || 'Multi-Factor Stock Selection System';

    currentSection = sectionName;

    // 加载对应页面数据
    switch(sectionName) {
        case 'factor-management':
            loadFactorList();
            break;
        case 'model-management':
            loadModelList();
            break;
        case 'stock-selection':
            loadFactorCheckboxes();
            loadModelOptions();
            break;
    }
}

// 加载仪表盘数据
async function loadDashboardData() {
    try {
        // 加载因子统计
        const factorsResponse = await fetch(`${API_BASE_URL}/factors/list`);
        const factorsData = await factorsResponse.json();
        if (factorsData.success) {
            document.getElementById('active-factors-count').textContent = factorsData.total_count;
        }

        // 加载模型统计
        const modelsResponse = await fetch(`${API_BASE_URL}/models/list`);
        const modelsData = await modelsResponse.json();
        if (modelsData.success) {
            document.getElementById('trained-models-count').textContent = modelsData.total_count;
        }

        // 更新最后更新时间
        document.getElementById('last-update-time').textContent = new Date().toLocaleString();

    } catch (error) {
        console.error('加载仪表盘数据失败:', error);
    }
}

// 加载因子列表
async function loadFactorList() {
    try {
        const response = await fetch(`${API_BASE_URL}/factors/list`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.querySelector('#factors-table tbody');
            tbody.innerHTML = '';
            
            data.factors.forEach(factor => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${factor.factor_id}</td>
                    <td>${factor.factor_name}</td>
                    <td><span class="badge bg-primary">${factor.factor_type}</span></td>
                    <td><span class="badge ${factor.is_active ? 'bg-success' : 'bg-secondary'}">${factor.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>${new Date(factor.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="editFactor('${factor.factor_id}')">Edit</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteFactor('${factor.factor_id}')">Delete</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('加载因子列表失败:', error);
        showAlert('Failed to load factor list', 'danger');
    }
}

// 加载模型列表
async function loadModelList() {
    try {
        const response = await fetch(`${API_BASE_URL}/models/list`);
        const data = await response.json();
        
        if (data.success) {
            const tbody = document.querySelector('#models-table tbody');
            tbody.innerHTML = '';
            
            data.models.forEach(model => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${model.model_id}</td>
                    <td>${model.model_name}</td>
                    <td><span class="badge bg-info">${model.model_type}</span></td>
                    <td><span class="badge ${model.is_active ? 'bg-success' : 'bg-secondary'}">${model.is_active ? 'Active' : 'Inactive'}</span></td>
                    <td>${new Date(model.created_at).toLocaleDateString()}</td>
                    <td>
                        <button class="btn btn-sm btn-outline-primary" onclick="trainModel('${model.model_id}')">Train</button>
                        <button class="btn btn-sm btn-outline-success" onclick="predictModel('${model.model_id}')">Predict</button>
                        <button class="btn btn-sm btn-outline-danger" onclick="deleteModel('${model.model_id}')">Delete</button>
                    </td>
                `;
                tbody.appendChild(row);
            });
        }
    } catch (error) {
        console.error('加载模型列表失败:', error);
        showAlert('Failed to load model list', 'danger');
    }
}

// 加载因子复选框
async function loadFactorCheckboxes() {
    try {
        const response = await fetch(`${API_BASE_URL}/factors/list`);
        const data = await response.json();
        
        if (data.success) {
            const container = document.getElementById('factor-checkboxes');
            const modelContainer = document.getElementById('model-factor-checkboxes');
            
            container.innerHTML = '';
            modelContainer.innerHTML = '';
            
            data.factors.forEach(factor => {
                if (factor.is_active) {
                    const checkbox = `
                        <div class="form-check">
                            <input class="form-check-input" type="checkbox" value="${factor.factor_id}" id="factor-${factor.factor_id}">
                            <label class="form-check-label" for="factor-${factor.factor_id}">
                                ${factor.factor_name} (${factor.factor_type})
                            </label>
                        </div>
                    `;
                    container.innerHTML += checkbox;
                    modelContainer.innerHTML += checkbox.replace(`factor-${factor.factor_id}`, `model-factor-${factor.factor_id}`);
                }
            });
        }
    } catch (error) {
        console.error('加载因子复选框失败:', error);
    }
}

// 加载模型选项
async function loadModelOptions() {
    try {
        const response = await fetch(`${API_BASE_URL}/models/list`);
        const data = await response.json();
        
        if (data.success) {
            const select = document.getElementById('model-ids');
            select.innerHTML = '';
            
            data.models.forEach(model => {
                if (model.is_active) {
                    const option = document.createElement('option');
                    option.value = model.model_id;
                    option.textContent = `${model.model_name} (${model.model_type})`;
                    select.appendChild(option);
                }
            });
        }
    } catch (error) {
        console.error('加载模型选项失败:', error);
    }
}

// 切换选股方法
function toggleSelectionMethod(method) {
    const factorSelection = document.getElementById('factor-selection');
    const modelSelection = document.getElementById('model-selection');
    
    if (method === 'ml_based') {
        factorSelection.style.display = 'none';
        modelSelection.style.display = 'block';
    } else {
        factorSelection.style.display = 'block';
        modelSelection.style.display = 'none';
    }
}

// 执行股票选择
async function performStockSelection() {
    const form = document.getElementById('selection-form');
    const formData = new FormData(form);
    
    const tradeDate = document.getElementById('trade-date').value;
    const selectionMethod = document.getElementById('selection-method').value;
    const topN = parseInt(document.getElementById('top-n').value);
    
    // 显示加载状态
    document.getElementById('selection-loading').style.display = 'block';
    document.getElementById('selection-results').innerHTML = '';
    
    try {
        let requestData = {
            trade_date: tradeDate,
            top_n: topN
        };
        
        let endpoint = '';
        
        if (selectionMethod === 'ml_based') {
            // 基于模型选股
            const modelSelect = document.getElementById('model-ids');
            const selectedModels = Array.from(modelSelect.selectedOptions).map(option => option.value);
            
            if (selectedModels.length === 0) {
                throw new Error('Please select at least one model');
            }
            
            requestData.model_ids = selectedModels;
            endpoint = '/scoring/ml-based';
        } else {
            // 基于因子选股
            const factorCheckboxes = document.querySelectorAll('#factor-checkboxes input[type="checkbox"]:checked');
            const selectedFactors = Array.from(factorCheckboxes).map(cb => cb.value);
            
            if (selectedFactors.length === 0) {
                throw new Error('Please select at least one factor');
            }
            
            requestData.factor_list = selectedFactors;
            requestData.method = 'equal_weight';
            endpoint = '/scoring/factor-based';
        }
        
        const response = await fetch(`${API_BASE_URL}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            selectedStocks = data.top_stocks || [];
            displaySelectionResults(data);
            showAlert('Stock selection completed', 'success');
        } else {
            throw new Error(data.error || 'Stock selection failed');
        }
        
    } catch (error) {
        console.error('股票选择失败:', error);
        showAlert(error.message, 'danger');
    } finally {
        document.getElementById('selection-loading').style.display = 'none';
    }
}

// 显示选股结果
function displaySelectionResults(data) {
    const container = document.getElementById('selection-results');
    
    let html = `
        <div class="mb-3">
            <h6>Selection Summary</h6>
            <p>Selection Method: ${data.selection_method === 'ml_based' ? 'Model-based' : 'Factor-based'}</p>
            <p>Selected Stocks: ${data.selected_stocks}</p>
        </div>
        <div class="table-responsive">
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th>Stock Code</th>
                        <th>Stock Name</th>
                        <th>Score</th>
                        <th>Rank</th>
                        <th>Sector</th>
                        <th>Actions</th>
                    </tr>
                </thead>
                <tbody>
    `;
    
    data.top_stocks.forEach(stock => {
        const score = stock.composite_score || stock.ensemble_score || 0;
        html += `
            <tr>
                <td>${stock.ts_code}</td>
                <td>${stock.name || '-'}</td>
                <td>${score.toFixed(4)}</td>
                <td>${stock.rank}</td>
                <td>${stock.industry || '-'}</td>
                <td>
                    <button class="btn btn-sm btn-outline-info" onclick="showStockDetail('${stock.ts_code}')">Details</button>
                </td>
            </tr>
        `;
    });
    
    html += `
                </tbody>
            </table>
        </div>
        <div class="mt-3">
            <button class="btn btn-primary" onclick="showSection('portfolio-optimization')">
                <i class="bi bi-pie-chart"></i> Portfolio Optimization
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// 执行组合优化
async function performPortfolioOptimization() {
    if (selectedStocks.length === 0) {
        showAlert('Please perform stock selection first', 'warning');
        return;
    }
    
    // 显示加载状态
    document.getElementById('optimization-loading').style.display = 'block';
    document.getElementById('optimization-results').innerHTML = '';
    
    try {
        const optimizationMethod = document.getElementById('optimization-method').value;
        const maxWeight = parseFloat(document.getElementById('max-weight').value) / 100;
        const riskAversion = parseFloat(document.getElementById('risk-aversion').value);
        
        // 构建预期收益率数据
        const expectedReturns = {};
        selectedStocks.forEach(stock => {
            const score = stock.composite_score || stock.ensemble_score || 0;
            expectedReturns[stock.ts_code] = score;
        });
        
        const requestData = {
            expected_returns: expectedReturns,
            method: optimizationMethod,
            constraints: {
                max_weight: maxWeight,
                risk_aversion: riskAversion
            }
        };
        
        const response = await fetch(`${API_BASE_URL}/portfolio/optimize`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });
        
        const data = await response.json();
        
        if (data.success) {
            optimizationResults = data;
            displayOptimizationResults(data);
            showAlert('Portfolio optimization completed', 'success');
        } else {
            throw new Error(data.error || 'Portfolio optimization failed');
        }
        
    } catch (error) {
        console.error('组合优化失败:', error);
        showAlert(error.message, 'danger');
    } finally {
        document.getElementById('optimization-loading').style.display = 'none';
    }
}

// 显示组合优化结果
function displayOptimizationResults(data) {
    const container = document.getElementById('optimization-results');
    
    let html = `
        <div class="row mb-3">
            <div class="col-md-6">
                <h6>Portfolio Statistics</h6>
                <table class="table table-sm">
                    <tr><td>Optimization Method</td><td>${data.method}</td></tr>
                    <tr><td>Expected Return</td><td>${(data.portfolio_stats.expected_return * 100).toFixed(2)}%</td></tr>
                    <tr><td>Expected Risk</td><td>${(data.portfolio_stats.expected_risk * 100).toFixed(2)}%</td></tr>
                    <tr><td>Sharpe Ratio</td><td>${data.portfolio_stats.sharpe_ratio.toFixed(3)}</td></tr>
                    <tr><td>Effective Stocks</td><td>${data.portfolio_stats.effective_stocks.toFixed(1)}</td></tr>
                </table>
            </div>
            <div class="col-md-6">
                <h6>Weight Distribution</h6>
                <div style="max-height: 200px; overflow-y: auto;">
                    <table class="table table-sm">
                        <thead><tr><th>Stock Code</th><th>Weight</th></tr></thead>
                        <tbody>
    `;
    
    // 按权重排序
    const sortedWeights = Object.entries(data.weights)
        .sort(([,a], [,b]) => b - a)
        .filter(([,weight]) => weight > 0.001);
    
    sortedWeights.forEach(([tsCode, weight]) => {
        html += `<tr><td>${tsCode}</td><td>${(weight * 100).toFixed(2)}%</td></tr>`;
    });
    
    html += `
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="mt-3">
            <button class="btn btn-success" onclick="exportPortfolio()">
                <i class="bi bi-download"></i> Export Portfolio
            </button>
            <button class="btn btn-info" onclick="generateAnalysisReport()">
                <i class="bi bi-file-text"></i> Generate Report
            </button>
        </div>
    `;
    
    container.innerHTML = html;
}

// 显示创建因子模态框
function showCreateFactorModal() {
    const modal = new bootstrap.Modal(document.getElementById('createFactorModal'));
    modal.show();
}

// 显示创建模型模态框
function showCreateModelModal() {
    loadFactorCheckboxes(); // 确保因子列表是最新的
    const modal = new bootstrap.Modal(document.getElementById('createModelModal'));
    modal.show();
}

// 创建因子
async function createFactor() {
    const factorId = document.getElementById('factor-id').value;
    const factorName = document.getElementById('factor-name').value;
    const factorType = document.getElementById('factor-type').value;
    const factorFormula = document.getElementById('factor-formula').value;
    const factorDescription = document.getElementById('factor-description').value;
    
    if (!factorId || !factorName || !factorType || !factorFormula) {
        showAlert('Please fill in all required fields', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/factors/custom`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                factor_id: factorId,
                factor_name: factorName,
                factor_type: factorType,
                factor_formula: factorFormula,
                description: factorDescription
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Factor created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createFactorModal')).hide();
            document.getElementById('create-factor-form').reset();
            if (currentSection === 'factor-management') {
                loadFactorList();
            }
        } else {
            throw new Error(data.error || 'Failed to create factor');
        }
        
    } catch (error) {
        console.error('创建因子失败:', error);
        showAlert(error.message, 'danger');
    }
}

// 创建模型
async function createModel() {
    const modelId = document.getElementById('model-id').value;
    const modelName = document.getElementById('model-name').value;
    const modelType = document.getElementById('model-type').value;
    const targetType = document.getElementById('target-type').value;
    
    // 获取选中的因子
    const factorCheckboxes = document.querySelectorAll('#model-factor-checkboxes input[type="checkbox"]:checked');
    const selectedFactors = Array.from(factorCheckboxes).map(cb => cb.value);
    
    if (!modelId || !modelName || !modelType || !targetType || selectedFactors.length === 0) {
        showAlert('Please fill in all required fields and select factors', 'warning');
        return;
    }
    
    try {
        const response = await fetch(`${API_BASE_URL}/models/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_id: modelId,
                model_name: modelName,
                model_type: modelType,
                target_type: targetType,
                factor_list: selectedFactors
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Model created successfully', 'success');
            bootstrap.Modal.getInstance(document.getElementById('createModelModal')).hide();
            document.getElementById('create-model-form').reset();
            if (currentSection === 'model-management') {
                loadModelList();
            }
        } else {
            throw new Error(data.error || 'Failed to create model');
        }
        
    } catch (error) {
        console.error('创建模型失败:', error);
        showAlert(error.message, 'danger');
    }
}

// 训练模型
async function trainModel(modelId) {
    if (!confirm('Are you sure you want to train this model? This may take several minutes.')) {
        return;
    }
    
    try {
        showAlert('Model training has started, please wait...', 'info');
        
        const response = await fetch(`${API_BASE_URL}/models/train`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                model_id: modelId,
                start_date: '2023-01-01',
                end_date: '2023-12-31'
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            showAlert('Model training completed', 'success');
            console.log('训练指标:', data.metrics);
        } else {
            throw new Error(data.error || 'Model training failed');
        }
        
    } catch (error) {
        console.error('模型训练失败:', error);
        showAlert(error.message, 'danger');
    }
}

// 生成因子分析报告
async function generateFactorAnalysis() {
    const tradeDate = document.getElementById('trade-date')?.value || new Date().toISOString().split('T')[0];
    
    try {
        const response = await fetch(`${API_BASE_URL}/analysis/sector`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                trade_date: tradeDate,
                top_n: 10
            })
        });
        
        const data = await response.json();
        
        if (data.success) {
            displayAnalysisResults('Factor Analysis Report', data.analysis);
        } else {
            throw new Error(data.error || 'Failed to generate analysis report');
        }
        
    } catch (error) {
        console.error('生成分析报告失败:', error);
        showAlert(error.message, 'danger');
    }
}

// 显示分析结果
function displayAnalysisResults(title, analysis) {
    const container = document.getElementById('analysis-results');
    
    let html = `<h6>${title}</h6>`;
    
    if (analysis.industry_summary) {
        html += `
            <div class="table-responsive">
                <table class="table table-sm">
                    <thead>
                        <tr>
                            <th>Sector</th>
                            <th>Average Score</th>
                            <th>Stock Count</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        analysis.industry_summary.slice(0, 10).forEach(industry => {
            html += `
                <tr>
                    <td>${industry.industry}</td>
                    <td>${industry.composite_score_mean.toFixed(4)}</td>
                    <td>${industry.composite_score_count}</td>
                </tr>
            `;
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// 显示警告消息
function showAlert(message, type = 'info') {
    // 创建警告元素
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show position-fixed`;
    alertDiv.style.cssText = 'top: 20px; right: 20px; z-index: 9999; min-width: 300px;';
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.appendChild(alertDiv);
    
    // 3秒后自动消失
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.parentNode.removeChild(alertDiv);
        }
    }, 3000);
}

// 刷新数据
function refreshData() {
    switch(currentSection) {
        case 'dashboard':
            loadDashboardData();
            break;
        case 'factor-management':
            loadFactorList();
            break;
        case 'model-management':
            loadModelList();
            break;
        case 'stock-selection':
            loadFactorCheckboxes();
            loadModelOptions();
            break;
    }
    showAlert('Data refreshed', 'success');
}

// 显示设置（占位符）
function showSettings() {
    showAlert('Settings feature is under development', 'info');
}

// 导出组合（占位符）
function exportPortfolio() {
    if (!optimizationResults) {
        showAlert('No portfolio data to export', 'warning');
        return;
    }
    
    // 简单的CSV导出
    let csv = 'Stock Code,Weight\n';
    Object.entries(optimizationResults.weights).forEach(([code, weight]) => {
        if (weight > 0.001) {
            csv += `${code},${(weight * 100).toFixed(2)}%\n`;
        }
    });
    
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'portfolio_weights.csv';
    a.click();
    window.URL.revokeObjectURL(url);
    
    showAlert('Portfolio exported', 'success');
}

// 生成分析报告（占位符）
function generateAnalysisReport() {
    showAlert('Analysis report generation feature is under development', 'info');
}

// 显示股票详情（占位符）
function showStockDetail(tsCode) {
    showAlert(`Stock ${tsCode} details feature is under development`, 'info');
}

// 编辑因子（占位符）
function editFactor(factorId) {
    showAlert(`Edit factor ${factorId} feature is under development`, 'info');
}

// 删除因子（占位符）
function deleteFactor(factorId) {
    if (confirm(`Are you sure you want to delete factor ${factorId}?`)) {
        showAlert(`Delete factor ${factorId} feature is under development`, 'info');
    }
}

// 删除模型（占位符）
function deleteModel(modelId) {
    if (confirm(`Are you sure you want to delete model ${modelId}?`)) {
        showAlert(`Delete model ${modelId} feature is under development`, 'info');
    }
}

// 模型预测（占位符）
function predictModel(modelId) {
    showAlert(`Model ${modelId} prediction feature is under development`, 'info');
}

// 生成行业分析
function generateSectorAnalysis() {
    generateFactorAnalysis(); // 复用因子分析功能
} 
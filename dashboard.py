"""
量化选股实时监控面板
"""
from flask import Flask, render_template_string, jsonify
import os
import json
from datetime import datetime

app = Flask(__name__)

REPORTS_DIR = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7\reports"
DB_PATH = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7\data\stocks.db"

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>quant-24x7 实时监控</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body { 
            font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            min-height: 100vh;
            color: #fff;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 30px 0;
            border-bottom: 2px solid #0f3460;
            margin-bottom: 30px;
        }
        .header h1 {
            font-size: 2.5rem;
            color: #e94560;
            text-shadow: 0 0 20px rgba(233, 69, 96, 0.5);
        }
        .header .subtitle {
            color: #888;
            margin-top: 10px;
        }
        .stats {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 20px;
            text-align: center;
            border: 1px solid rgba(255,255,255,0.1);
        }
        .stat-card .value {
            font-size: 2rem;
            font-weight: bold;
            color: #00d9ff;
        }
        .stat-card .label {
            color: #888;
            margin-top: 5px;
        }
        .picks-section {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
            margin-bottom: 30px;
        }
        .picks-section h2 {
            color: #e94560;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        .stock-card {
            display: grid;
            grid-template-columns: repeat(5, 1fr);
            gap: 15px;
            margin-bottom: 20px;
        }
        .stock {
            background: linear-gradient(145deg, #1e3a5f, #16213e);
            border-radius: 12px;
            padding: 20px;
            text-align: center;
            border: 1px solid #0f3460;
            transition: transform 0.3s, box-shadow 0.3s;
        }
        .stock:hover {
            transform: translateY(-5px);
            box-shadow: 0 10px 30px rgba(0, 217, 255, 0.2);
        }
        .stock .rank {
            background: #e94560;
            width: 30px;
            height: 30px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
            margin: 0 auto 10px;
            font-weight: bold;
        }
        .stock .code {
            font-size: 1.2rem;
            font-weight: bold;
            color: #00d9ff;
        }
        .stock .name {
            color: #888;
            font-size: 0.9rem;
            margin: 5px 0;
        }
        .stock .price {
            font-size: 1.5rem;
            font-weight: bold;
            color: #4ecca3;
        }
        .stock .change {
            font-size: 1.1rem;
            margin: 10px 0;
        }
        .stock .change.up { color: #4ecca3; }
        .stock .change.down { color: #e94560; }
        .stock .metrics {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 5px;
            font-size: 0.8rem;
            color: #666;
            margin-top: 10px;
        }
        .stock .score {
            background: linear-gradient(90deg, #e94560, #ff6b6b);
            padding: 5px 15px;
            border-radius: 20px;
            display: inline-block;
            margin-top: 10px;
        }
        .log-section {
            background: rgba(255,255,255,0.05);
            border-radius: 15px;
            padding: 25px;
        }
        .log-section h2 {
            color: #e94560;
            margin-bottom: 20px;
        }
        .log-list {
            max-height: 300px;
            overflow-y: auto;
        }
        .log-item {
            padding: 10px;
            border-bottom: 1px solid rgba(255,255,255,0.1);
            font-family: monospace;
            font-size: 0.9rem;
        }
        .log-item .time { color: #00d9ff; }
        .log-item .msg { color: #aaa; }
        .refresh-btn {
            position: fixed;
            bottom: 30px;
            right: 30px;
            background: #e94560;
            color: #fff;
            border: none;
            padding: 15px 30px;
            border-radius: 30px;
            cursor: pointer;
            font-size: 1rem;
            box-shadow: 0 5px 20px rgba(233, 69, 96, 0.4);
            transition: transform 0.3s;
        }
        .refresh-btn:hover {
            transform: scale(1.1);
        }
        @media (max-width: 768px) {
            .stats { grid-template-columns: repeat(2, 1fr); }
            .stock-card { grid-template-columns: 1fr; }
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 quant-24x7 实时监控</h1>
        <div class="subtitle">A股量化选股系统 | 实时数据</div>
    </div>
    
    <div class="stats">
        <div class="stat-card">
            <div class="value">{{ stocks_count }}</div>
            <div class="label">📈 监控股票</div>
        </div>
        <div class="stat-card">
            <div class="value">{{ picks_count }}</div>
            <div class="label">🎯 今日选出</div>
        </div>
        <div class="stat-card">
            <div class="value">{{ avg_score }}</div>
            <div class="label">⭐ 平均评分</div>
        </div>
        <div class="stat-card">
            <div class="value">{{ last_update }}</div>
            <div class="label">🕐 更新时间</div>
            <div class="label" id="refresh-status" style="color: #4ecca3; margin-top: 5px;"></div>
        </div>
    </div>
    
    <div class="filter-info">
        <h3>📋 选股条件</h3>
        <div class="filter-tags">
            <span class="tag">市值: 30亿-150亿</span>
            <span class="tag">股价: &lt;30元</span>
            <span class="tag">排除: 创业板/科创板/北交所/ST股</span>
        </div>
    </div>
    
    <div class="picks-section">
        <h2>🏆 今日精选 TOP 5</h2>
        {% if picks %}
        <div class="stock-card">
            {% for pick in picks %}
            <div class="stock">
                <div class="rank">{{ loop.index }}</div>
                <div class="code">{{ pick.code }}</div>
                <div class="name">{{ pick.name }}</div>
                <div class="price">¥{{ pick.price }}</div>
                <div class="change {% if pick.change_pct > 0 %}up{% else %}down{% endif %}">
                    {% if pick.change_pct > 0 %}+{% endif %}{{ pick.change_pct }}%
                </div>
                <div class="metrics">
                    <span>量比: {{ pick.vr }}</span>
                    <span>换手: {{ pick.turnover }}%</span>
                    <span>PE: {{ pick.pe }}</span>
                    <span>PB: {{ pick.pb }}</span>
                </div>
                <div class="score">评分: {{ pick.score }}</div>
            </div>
            {% endfor %}
        </div>
        {% else %}
        <p style="text-align: center; color: #666; padding: 40px;">暂无选股结果，请先运行选股系统</p>
        {% endif %}
    </div>
    
    <div class="log-section">
        <h2>📋 运行日志</h2>
        <div class="log-list">
            {% for log in logs %}
            <div class="log-item">
                <span class="time">{{ log.time }}</span>
                <span class="msg">{{ log.msg }}</span>
            </div>
            {% endfor %}
        </div>
    </div>
    
    <button class="refresh-btn" onclick="location.reload()">🔄 刷新数据</button>
    
    <script>
        // 开盘时段 (9:30-15:00) 每10秒刷新，非开盘时段每60秒
        function getRefreshInterval() {
            const now = new Date();
            const hour = now.getHours();
            const minute = now.getMinutes();
            const time = hour * 60 + minute;
            const isWeekday = now.getDay() >= 1 && now.getDay() <= 5;
            const isMarketHours = time >= 570 && time <= 900; // 9:30 - 15:00
            return (isWeekday && isMarketHours) ? 30000 : 60000;
        }
        
        function autoRefresh() {
            const interval = getRefreshInterval();
            const status = document.getElementById('refresh-status');
            if(status) {
                const now = new Date().toLocaleTimeString();
                status.textContent = '自动刷新: ' + (interval/1000) + '秒';
            }
            setTimeout(() => location.reload(), interval);
        }
        
        // 页面加载后立即刷新一次
        window.onload = function() {
            autoRefresh();
        };
    </script>
</body>
</html>
"""

def get_latest_report():
    """获取最新报告"""
    if not os.path.exists(REPORTS_DIR):
        return None
    
    files = [f for f in os.listdir(REPORTS_DIR) if f.startswith('pick_') and f.endswith('.json')]
    if not files:
        return None
    
    latest = sorted(files)[-1]
    with open(os.path.join(REPORTS_DIR, latest), 'r', encoding='utf-8') as f:
        return json.load(f)

def get_logs():
    """获取运行日志"""
    logs = []
    log_file = r"C:\Users\Administrator\.qclaw\workspace\quant-24x7\logs\auto_runner.log"
    if os.path.exists(log_file):
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            for line in lines[-20:]:
                if '|' in line:
                    parts = line.split('|')
                    if len(parts) >= 3:
                        logs.append({
                            'time': parts[0].strip()[:19],
                            'msg': '|'.join(parts[2:]).strip()
                        })
    return logs

@app.route('/')
def index():
    """主页"""
    # 获取最新报告
    report = get_latest_report()
    
    if report:
        picks = report.get('picks', [])[:5]
        stocks_count = 100  # 每次采集100只
        picks_count = len(picks)
        avg_score = sum(p['score'] for p in picks) / len(picks) if picks else 0
        last_update = report.get('time', 'N/A')
    else:
        picks = []
        stocks_count = 0
        picks_count = 0
        avg_score = 0
        last_update = 'N/A'
    
    logs = get_logs()
    
    return render_template_string(HTML_TEMPLATE,
        stocks_count=stocks_count,
        picks_count=picks_count,
        avg_score=round(avg_score, 1),
        last_update=last_update,
        picks=picks,
        logs=logs
    )

@app.route('/api/data')
def api_data():
    """API数据接口"""
    report = get_latest_report()
    logs = get_logs()
    return jsonify({
        'report': report,
        'logs': logs,
        'timestamp': datetime.now().isoformat()
    })

if __name__ == '__main__':
    print("=" * 50)
    print("quant-24x7 Monitor Dashboard")
    print("Access: http://localhost:5000")
    print("=" * 50)
    app.run(host='0.0.0.0', port=5000, debug=False)
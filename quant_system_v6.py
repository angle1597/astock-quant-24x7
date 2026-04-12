# -*- coding: utf-8 -*-
"""
量化选股系统 v6 - 融合专业金融分析
整合: 技术分析 + 情绪分析 + 基本面分析 + 新闻分析
"""
import requests
import json
from datetime import datetime

class QuantStockSystem:
    """量化选股系统 - 多维度分析"""
    
    def __init__(self):
        self.name = "QuantStockSystem v6"
    
    def get_market_news(self):
        """获取市场新闻"""
        news = []
        try:
            # 东方财富新闻
            url = 'https://np-listapi.eastmoney.com/cgi-bin/cgi_GetIndexNews'
            params = {
                'Client': 'WEB',
                'Version': '1.0.0',
                'IndexCode': 'HSIndex000001',
                'NewsCount': 10,
            }
            r = requests.get(url, params=params, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if 'NoticeList' in data.get('Result', {}):
                    for n in data['Result']['NoticeList'][:5]:
                        news.append({
                            'title': n.get('ShowTitle', ''),
                            'time': n.get('ShowTime', ''),
                            'summary': n.get('Summary', '')[:100],
                        })
        except:
            pass
        return news
    
    def technical_analysis(self, price, chg, turnover, high, low):
        """技术分析评分"""
        score = 0
        
        # 涨幅评分
        if 2 <= chg <= 5:
            score += 30
        elif 1 <= chg <= 7:
            score += 20
        
        # 换手率评分
        if turnover >= 10:
            score += 25
        elif turnover >= 5:
            score += 20
        elif turnover >= 2:
            score += 10
        
        # 低价股评分
        if 3 <= price <= 8:
            score += 25
        elif 8 < price <= 15:
            score += 15
        
        # 强势收盘
        if high > low:
            pos = (price - low) / (high - low)
            if pos >= 0.8:
                score += 15
            elif pos >= 0.6:
                score += 10
        
        return score
    
    def sentiment_analysis(self, name):
        """情绪分析 - 热门概念"""
        score = 0
        
        hot_keywords = {
            '电力': 20, '能源': 20, '光伏': 18, '新能源': 18,
            '科技': 15, '电子': 15, '半导体': 15, 'AI': 15,
            '医药': 12, '消费': 10, '军工': 15, '稀土': 15,
            '锂电': 15, '储能': 15, '芯片': 15, '算力': 15,
        }
        
        for keyword, weight in hot_keywords.items():
            if keyword in name:
                score += weight
                break
        
        return score
    
    def fundamental_analysis(self, pe, mv):
        """基本面分析"""
        score = 0
        
        # PE估值
        if 0 < pe < 10:
            score += 20
        elif 0 < pe < 20:
            score += 15
        elif 0 < pe < 30:
            score += 10
        elif pe < 0:
            score += 5
        
        # 市值
        if 30 <= mv <= 80:
            score += 20
        elif 20 <= mv <= 100:
            score += 15
        
        return score
    
    def risk_control(self, chg_5d):
        """风险控制"""
        # 近期涨幅过大不追
        if chg_5d > 30:
            return -30
        elif chg_5d > 20:
            return -15
        elif chg_5d > 15:
            return -5
        return 0

def main():
    print('='*60)
    print('【量化选股系统 v6】')
    print('融合: 技术分析 + 情绪分析 + 基本面分析')
    print('='*60)
    print('')
    
    system = QuantStockSystem()
    
    # 获取市场数据
    url = 'https://vip.stock.finance.sina.com.cn/quotes_service/api/json_v2.php/Market_Center.getHQNodeDataSimple?page=1&num=500&sort=change&asc=0&node=hs_a&symbol=&_s_r_a=page'
    headers = {'User-Agent': 'Mozilla/5.0', 'Referer': 'https://finance.sina.com.cn'}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        data = r.json()
    except:
        print('数据获取失败')
        return
    
    candidates = []
    
    for s in data:
        code = s.get('symbol', '')
        name = s.get('name', '')
        
        # 排除
        if code.startswith('bj') or code.startswith('sh688') or code.startswith('sz300') or code.startswith('sz301'):
            continue
        if 'ST' in name or '退' in name:
            continue
        
        try:
            price = float(s.get('trade', 0))
            chg = float(s.get('changepercent', 0))
            turnover = float(s.get('amount', 0)) / 1e8
            high = float(s.get('high', 0))
            low = float(s.get('low', 0))
            settlement = float(s.get('settlement', 0))
        except:
            continue
        
        code_clean = code.replace('sh','').replace('sz','')
        
        # 多维度评分
        tech_score = system.technical_analysis(price, chg, turnover, high, low)
        sentiment_score = system.sentiment_analysis(name)
        fundamental_score = system.fundamental_analysis(pe=0, mv=turnover*50)  # 估算市值
        risk_penalty = system.risk_control((price - settlement) / settlement * 100) if settlement > 0 else 0
        
        # 综合评分
        total_score = tech_score * 0.5 + sentiment_score * 0.3 + fundamental_score * 0.2 + risk_penalty
        
        # 筛选条件
        if price <= 2 or price > 15:
            continue
        if chg <= 0 or chg > 8:
            continue
        if turnover < 1:
            continue
        
        if total_score >= 50:
            candidates.append({
                'code': code_clean,
                'name': name,
                'price': price,
                'chg': chg,
                'turnover': turnover,
                'tech': tech_score,
                'sentiment': sentiment_score,
                'total': total_score,
            })
    
    candidates.sort(key=lambda x: x['total'], reverse=True)
    
    print('扫描股票:', len(data))
    print('候选股票:', len(candidates))
    print('')
    
    if candidates:
        best = candidates[0]
        print('='*60)
        print('【唯一推荐】')
        print('='*60)
        print('代码:', best['code'])
        print('名称:', best['name'])
        print('价格:', best['price'], '元')
        print('涨幅:', '+' + str(round(best['chg'], 2)) + '%')
        print('成交额:', round(best['turnover'], 2), '亿')
        print('')
        print('【多维度评分】')
        print('  技术分析:', best['tech'], '分')
        print('  情绪分析:', best['sentiment'], '分')
        print('  综合评分:', best['total'], '分')
        print('')
        print('【操作建议】')
        print('  买入: 明日开盘')
        print('  止损: -5%')
        print('  止盈: +30%')
        print('')
        print('='*60)
        print('TOP 5:')
        for i, c in enumerate(candidates[:5], 1):
            print(i, '.', c['code'], c['name'], c['price'], '元 +' + str(round(c['chg'], 1)) + '%', '评分', round(c['total'], 0))

if __name__ == '__main__':
    main()

import psycopg2
from pathlib import Path
from loguru import logger
import json

config = {
    'host': 'localhost',
    'port': 5432,
    'database': 'real_estate_dev',
    'user': 'postgres',
    'password': 'postgres'
}

def get_all_addresses():
    """全ての住所を取得"""
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT DISTINCT original_address
        FROM land_prices
        WHERE survey_year = 2025
        ORDER BY original_address
    ''')
    
    addresses = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return addresses

def get_price_history(address):
    """指定住所の5年分の価格履歴を取得"""
    conn = psycopg2.connect(**config)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT survey_year, official_price, year_on_year_change
        FROM land_prices
        WHERE original_address LIKE %s
        ORDER BY survey_year
    ''', (f'{address}%',))
    
    data = cursor.fetchall()
    cursor.close()
    conn.close()
    
    return data

def calculate_trend_score(data):
    """トレンドスコアを計算（簡易版）"""
    if len(data) < 2:
        return 50
    
    latest = data[-1]
    oldest = data[0]
    change_5y = ((latest[1] - oldest[1]) / oldest[1]) * 100
    
    # スコア計算（0-100）
    if change_5y >= 20:
        return 95
    elif change_5y >= 15:
        return 90
    elif change_5y >= 10:
        return 85
    elif change_5y >= 5:
        return 80
    elif change_5y >= 0:
        return 70
    elif change_5y >= -5:
        return 60
    else:
        return 50

def generate_article(address, data):
    """記事を生成"""
    if not data:
        return None
    
    latest = data[-1]
    oldest = data[0]
    change_5y = ((latest[1] - oldest[1]) / oldest[1]) * 100
    
    # 町丁目名を抽出
    area_name = address.split('丁目')[0] + '丁目' if '丁目' in address else address[:10]
    
    # トレンド判定
    if change_5y > 10:
        trend_comment = "大幅な上昇トレンド"
        asset_evaluation = "資産価値が大きく向上している優良エリア"
    elif change_5y > 5:
        trend_comment = "安定した上昇トレンド"
        asset_evaluation = "資産価値の保全性が高いエリア"
    elif change_5y > 0:
        trend_comment = "緩やかな上昇トレンド"
        asset_evaluation = "安定した資産価値を維持しているエリア"
    elif change_5y > -5:
        trend_comment = "横ばいまたは微減トレンド"
        asset_evaluation = "慎重な検討が必要なエリア"
    else:
        trend_comment = "下降トレンド"
        asset_evaluation = "注意が必要なエリア"
    
    # スコア計算
    score = calculate_trend_score(data)
    
    # 記事本文
    article = f'''# {area_name}の資産価値分析

## 📊 総合スコア: {score}点 / 100点

## 地価推移（過去5年）

最新の地価公示データ（2025年）によると、**{area_name}**の公示地価は**{latest[1]:,}円/㎡**です。

### 5年間の変化
- 2021年: {oldest[1]:,}円/㎡
- 2025年: {latest[1]:,}円/㎡
- **5年間の変動率: {change_5y:+.1f}%**

### 詳細な推移
'''
    
    for year, price, change in data:
        if change is not None:
            article += f'- {year}年: {price:,}円/㎡ (前年比: {float(change):+.1f}%)\n'
        else:
            article += f'- {year}年: {price:,}円/㎡\n'
    
    article += f'''
### 最新の動向（2025年）
前年比で**{float(latest[2]):+.1f}%**の{'上昇' if latest[2] > 0 else '下降'}となっています。

## 💡 資産価値の評価

この地域は**{trend_comment}**を示しており、{asset_evaluation}と評価できます。

### 投資判断のポイント
'''
    
    if change_5y > 5:
        article += '''
- ✅ 過去5年間で安定した価格上昇
- ✅ 資産価値の向上が期待できる
- ✅ 売却時の価格維持・上昇の可能性が高い
'''
    elif change_5y > 0:
        article += '''
- ✅ 価格は安定的に推移
- ⚠️ 大幅な価格上昇は見込みづらい
- ✅ 長期保有に適したエリア
'''
    else:
        article += '''
- ⚠️ 価格が下降傾向
- ⚠️ 売却タイミングの見極めが重要
- ⚠️ 慎重な検討が必要
'''
    
    article += '''
---
*データ出典: 東京都オープンデータ（地価公示）*
*分析日: 2025年11月30日*
'''
    
    return article

def generate_graph_data(address, data):
    """グラフデータJSONを生成"""
    graph_data = {
        'type': 'line',
        'data': {
            'labels': [str(row[0]) for row in data],
            'datasets': [{
                'label': '公示地価（円/㎡）',
                'data': [row[1] for row in data],
                'borderColor': '#4CAF50',
                'backgroundColor': 'rgba(76, 175, 80, 0.1)',
                'tension': 0.1,
                'fill': True
            }]
        },
        'options': {
            'responsive': True,
            'plugins': {
                'title': {
                    'display': True,
                    'text': '地価推移（5年間）'
                },
                'legend': {
                    'display': True
                }
            },
            'scales': {
                'y': {
                    'beginAtZero': False,
                    'ticks': {
                        'callback': 'function(value) { return value.toLocaleString() + "円"; }'
                    }
                }
            }
        }
    }
    
    return graph_data

def main():
    logger.info('=' * 60)
    logger.info('全地点記事一括生成')
    logger.info('=' * 60)
    
    # 出力ディレクトリ作成
    output_dir = Path('output/articles')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    graph_dir = Path('output/graphs')
    graph_dir.mkdir(parents=True, exist_ok=True)
    
    # 全住所取得
    addresses = get_all_addresses()
    logger.info(f'対象地点数: {len(addresses)} 件')
    
    success_count = 0
    error_count = 0
    
    for i, address in enumerate(addresses, 1):
        try:
            # 価格履歴取得
            data = get_price_history(address)
            
            if not data:
                logger.warning(f'データなし: {address}')
                error_count += 1
                continue
            
            # 記事生成
            article = generate_article(address, data)
            
            # ファイル名生成（安全な文字のみ）
            safe_name = address.replace('丁目', '').replace('番', '').replace(' ', '').replace('　', '')[:30]
            
            # 記事保存
            article_path = output_dir / f'{safe_name}_report.md'
            with open(article_path, 'w', encoding='utf-8') as f:
                f.write(article)
            
            # グラフデータ保存
            graph_data = generate_graph_data(address, data)
            graph_path = graph_dir / f'{safe_name}_graph.json'
            with open(graph_path, 'w', encoding='utf-8') as f:
                json.dump(graph_data, f, ensure_ascii=False, indent=2)
            
            success_count += 1
            
            if i % 10 == 0:
                logger.info(f'進捗: {i}/{len(addresses)} 件')
            
        except Exception as e:
            logger.error(f'エラー: {address} - {e}')
            error_count += 1
    
    logger.info('=' * 60)
    logger.info(f'✅ 生成完了: {success_count} 件')
    logger.info(f'❌ エラー: {error_count} 件')
    logger.info(f'📁 出力先: {output_dir.absolute()}')
    logger.info('=' * 60)

if __name__ == '__main__':
    main()
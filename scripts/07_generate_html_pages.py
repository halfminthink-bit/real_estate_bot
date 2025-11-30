import psycopg2
from pathlib import Path
from loguru import logger
import json
import markdown

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
        LIMIT 10
    ''')
    
    addresses = [row[0] for row in cursor.fetchall()]
    cursor.close()
    conn.close()
    
    return addresses

def generate_html_page(address, article_md, graph_data):
    """HTMLページを生成"""
    
    # MarkdownをHTMLに変換
    html_content = markdown.markdown(article_md)
    
    # Chart.jsのデータを埋め込み
    html = f'''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{address.split('丁目')[0] if '丁目' in address else address[:10]}丁目 - 資産価値分析</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Hiragino Sans', sans-serif;
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.8;
            color: #333;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 3px solid #4CAF50;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #34495e;
            margin-top: 30px;
            border-left: 4px solid #4CAF50;
            padding-left: 10px;
        }}
        .chart-container {{
            position: relative;
            height: 400px;
            margin: 30px 0;
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
        }}
        .score {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 1.5em;
            margin: 20px 0;
        }}
        .metadata {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-top: 30px;
            font-size: 0.9em;
            color: #666;
        }}
        ul {{
            line-height: 2;
        }}
        li {{
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="content">
        {html_content}
    </div>
    
    <div class="chart-container">
        <canvas id="priceChart"></canvas>
    </div>
    
    <script>
        const ctx = document.getElementById('priceChart').getContext('2d');
        const chartData = {json.dumps(graph_data, ensure_ascii=False)};
        
        new Chart(ctx, {{
            type: chartData.type,
            data: chartData.data,
            options: {{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {{
                    title: {{
                        display: true,
                        text: '地価推移（5年間）',
                        font: {{
                            size: 18
                        }}
                    }},
                    legend: {{
                        display: true
                    }}
                }},
                scales: {{
                    y: {{
                        beginAtZero: false,
                        ticks: {{
                            callback: function(value) {{
                                return value.toLocaleString() + '円';
                            }}
                        }}
                    }}
                }}
            }}
        }});
    </script>
</body>
</html>
'''
    
    return html

def main():
    logger.info('=' * 60)
    logger.info('HTMLページ生成（サンプル10件）')
    logger.info('=' * 60)
    
    # 出力ディレクトリ
    output_dir = Path('output/html')
    output_dir.mkdir(parents=True, exist_ok=True)
    
    articles_dir = Path('output/articles')
    graphs_dir = Path('output/graphs')
    
    if not articles_dir.exists():
        logger.error('記事が見つかりません。先に 06_batch_generate_articles.py を実行してください')
        return
    
    # 全記事ファイル取得
    article_files = list(articles_dir.glob('*_report.md'))
    logger.info(f'記事ファイル数: {len(article_files)} 件')
    
    success_count = 0
    
    for article_file in article_files[:10]:  # 最初の10件のみ
        try:
            # 対応するグラフファイルを探す
            graph_file = graphs_dir / article_file.name.replace('_report.md', '_graph.json')
            
            if not graph_file.exists():
                logger.warning(f'グラフファイルなし: {graph_file}')
                continue
            
            # 記事読み込み
            with open(article_file, 'r', encoding='utf-8') as f:
                article_md = f.read()
            
            # グラフデータ読み込み
            with open(graph_file, 'r', encoding='utf-8') as f:
                graph_data = json.load(f)
            
            # HTML生成
            address = article_file.stem.replace('_report', '')
            html = generate_html_page(address, article_md, graph_data)
            
            # HTML保存
            html_file = output_dir / f'{article_file.stem}.html'
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html)
            
            logger.info(f'✅ 生成: {html_file.name}')
            success_count += 1
            
        except Exception as e:
            logger.error(f'エラー: {article_file.name} - {e}')
    
    logger.info('=' * 60)
    logger.info(f'✅ HTML生成完了: {success_count} 件')
    logger.info(f'📁 出力先: {output_dir.absolute()}')
    logger.info('=' * 60)
    
    # インデックスページ生成
    index_html = '''<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <title>世田谷区 地価分析レポート一覧</title>
    <style>
        body { font-family: sans-serif; max-width: 1200px; margin: 0 auto; padding: 20px; }
        h1 { color: #2c3e50; }
        .report-list { list-style: none; padding: 0; }
        .report-list li { margin: 10px 0; }
        .report-list a { text-decoration: none; color: #3498db; font-size: 1.1em; }
        .report-list a:hover { text-decoration: underline; }
    </style>
</head>
<body>
    <h1>📊 世田谷区 地価分析レポート</h1>
    <p>過去5年間の地価推移を分析したレポートです。</p>
    <ul class="report-list">
'''
    
    for html_file in sorted(output_dir.glob('*_report.html')):
        index_html += f'        <li><a href="{html_file.name}">{html_file.stem.replace("_report", "")}</a></li>\n'
    
    index_html += '''    </ul>
</body>
</html>
'''
    
    with open(output_dir / 'index.html', 'w', encoding='utf-8') as f:
        f.write(index_html)
    
    logger.info(f'✅ インデックスページ: {output_dir / "index.html"}')

if __name__ == '__main__':
    main()
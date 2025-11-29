import markdown
import yaml
from pathlib import Path
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class HTMLBuilder:
    """Markdown → HTML変換 + アフィリエイト挿入"""

    def __init__(self, config):
        self.config = config
        self.template_path = config.templates_dir / 'article_template.html'
        self.affiliate_config_path = config.get_affiliate_config_path()

        # アフィリエイト設定を読み込み
        if self.affiliate_config_path.exists():
            with open(self.affiliate_config_path, 'r', encoding='utf-8') as f:
                self.affiliate_config = yaml.safe_load(f)
        else:
            logger.warning(f"Affiliate config not found at {self.affiliate_config_path}")
            self.affiliate_config = {}

        logger.info(f"Initialized HTMLBuilder with template={self.template_path}")

    def build(self, markdown_path: Path, chart_path: Path, output_path: Path):
        """
        Markdown → HTML変換

        Args:
            markdown_path: Markdownファイルパス
            chart_path: レーダーチャート画像パス
            output_path: 出力HTMLパス
        """
        logger.info(f"Building HTML: {markdown_path} -> {output_path}")

        # Markdown読み込み
        with open(markdown_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # チャート画像挿入
        chart_html = f'<div class="chart"><img src="{chart_path.name}" alt="レーダーチャート" style="max-width:100%; height:auto;"></div>'
        md_content = md_content.replace('<CHART>', chart_html)

        # アフィリエイトリンク挿入
        affiliate_html = self._build_affiliate_section()
        md_content = md_content.replace('<AFFILIATE>', affiliate_html)

        # Markdown → HTML
        html_content = markdown.markdown(md_content, extensions=['extra', 'nl2br'])

        # テンプレートに埋め込み
        if self.template_path.exists():
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            # テンプレートがない場合はシンプルなHTMLを生成
            template = self._get_default_template()

        # タイトルを抽出（最初のH1タグから）
        title = self._extract_title(md_content)

        html = template.format(
            title=title,
            content=html_content,
            button_color=self.affiliate_config.get('ieul', {}).get('button_color', '#FF6B35'),
            update_date=datetime.now().strftime('%Y年%m月%d日')
        )

        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML saved to {output_path}")

    def _build_affiliate_section(self) -> str:
        """アフィリエイトセクションHTML生成"""
        if not self.affiliate_config:
            return ''

        html = '<div class="affiliate-box">\n'
        html += '<h3>🔍 正確な査定は専門家へ</h3>\n'
        html += '<p>このデータはあくまで参考値です。正確な査定額を知りたい方は、複数の不動産会社に査定を依頼することをおすすめします。</p>\n'

        for key, config in self.affiliate_config.items():
            button_color = config.get('button_color', '#FF6B35')
            url = config.get('url', '#')
            text = config.get('text', '詳細を見る')
            html += f'<a href="{url}" class="affiliate-button" style="background-color:{button_color}" target="_blank" rel="nofollow noopener">{text}</a>\n'

        html += '</div>\n'
        return html

    def _extract_title(self, markdown_content: str) -> str:
        """Markdownから最初のH1タイトルを抽出"""
        lines = markdown_content.split('\n')
        for line in lines:
            if line.startswith('# '):
                return line[2:].strip()
        return 'Real Estate Article'

    def _get_default_template(self) -> str:
        """デフォルトHTMLテンプレート"""
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1 {{ color: #1E3A8A; border-bottom: 3px solid #FF6B35; padding-bottom: 10px; }}
        h2 {{ color: #1E3A8A; margin-top: 40px; }}
        .chart {{
            text-align: center;
            margin: 30px 0;
        }}
        .affiliate-box {{
            background: #FFF7ED;
            padding: 20px;
            border: 2px solid #FF6B35;
            border-radius: 8px;
            margin: 30px 0;
        }}
        .affiliate-button {{
            display: inline-block;
            padding: 15px 30px;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 10px 5px;
        }}
        .affiliate-button:hover {{
            opacity: 0.8;
        }}
    </style>
</head>
<body>
    {content}
    <div style="margin-top: 50px; font-size: 0.9em; color: #666;">
        <p>データ更新日: {update_date}</p>
        <p>※本サイトは情報提供のみを目的としており、不動産の査定・売買の仲介は行っておりません。</p>
    </div>
</body>
</html>"""

import markdown
import yaml
from pathlib import Path
from datetime import datetime
import logging
import re

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
            chart_path: レーダーチャート画像パス（None可、固定セクション方式では不要）
            output_path: 出力HTMLパス
        """
        logger.info(f"Building HTML: {markdown_path} -> {output_path}")

        # Markdown読み込み
        with open(markdown_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # チャート画像挿入（旧方式の<CHART>タグ対応）
        if '<CHART>' in md_content:
            if chart_path:
                chart_html = f'<div class="chart-container"><img src="{chart_path.name}" alt="レーダーチャート"></div>'
                md_content = md_content.replace('<CHART>', chart_html)
            else:
                # chart_pathがNoneの場合は<CHART>タグを削除
                md_content = md_content.replace('<CHART>', '')
        
        # 固定セクション方式では、Markdown内に画像が直接埋め込まれているため
        # 画像パスをHTMLから見た相対パスに調整
        # 画像ファイルはchartsディレクトリに、HTMLはhtmlディレクトリに保存される
        # 相対パス: html/ から charts/ へのパス
        import re
        # Markdownの画像記法 ![alt](filename) を検出してパスを調整
        def adjust_image_path(match):
            alt_text = match.group(1)
            image_filename = match.group(2)
            # HTMLから見た相対パス（html/ から charts/ へのパス）
            relative_path = f"../charts/{image_filename}"
            return f"![{alt_text}]({relative_path})"
        
        md_content = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', adjust_image_path, md_content)

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
        h1_title = title  # H1タイトルも同じ
        
        # メタディスクリプションを生成（最初の150文字程度）
        meta_description = self._extract_description(md_content)

        # テンプレート変数を置換（二重波括弧に対応）
        update_date = datetime.now().strftime('%Y年%m月%d日')
        
        html = template.replace('{{ title }}', title)
        html = html.replace('{{ h1_title }}', h1_title)
        html = html.replace('{{ meta_description }}', meta_description)
        html = html.replace('{{ content }}', html_content)
        html = html.replace('{{ update_date }}', update_date)

        # 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML saved to {output_path}")

    def _build_affiliate_section(self) -> str:
        """アフィリエイトセクションHTML生成"""
        if not self.affiliate_config:
            return ''

        html = '<div class="affiliate-box">\n'
        html += '<h3>💡 あなたの資産価値、無料で知れます</h3>\n'
        html += '<p>このデータは参考値です。あなたの物件の正確な価値は、立地や状態によって大きく異なります。無料査定で「今の価値」を知っておきませんか？売る・売らないは後で決めればOK。まずは知ることから始めましょう。</p>\n'

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

    def _extract_description(self, markdown_content: str) -> str:
        """
        Markdownから最初の段落を抽出してメタディスクリプション生成
        最大160文字
        """
        # Markdown記法を除去
        text = re.sub(r'#+ ', '', markdown_content)  # 見出し記号を除去
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)  # 太字を除去
        text = re.sub(r'\*(.+?)\*', r'\1', text)      # イタリックを除去
        text = re.sub(r'\[(.+?)\]\(.+?\)', r'\1', text)  # リンクを除去
        text = re.sub(r'<.+?>', '', text)             # HTMLタグを除去
        
        # 最初の段落を取得（改行2つまで）
        paragraphs = text.split('\n\n')
        first_paragraph = ''
        for p in paragraphs:
            p = p.strip()
            if p and not p.startswith('#'):
                first_paragraph = p
                break
        
        # 160文字に制限
        if len(first_paragraph) > 160:
            return first_paragraph[:157] + '...'
        return first_paragraph if first_paragraph else '世田谷区の町丁目レベルの資産価値と住環境をデータで分析。不動産の正確な価値を知りたい方へ。'

    def _get_default_template(self) -> str:
        """デフォルトHTMLテンプレート"""
        return """<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{{ title }}</title>
    <meta name="description" content="{{ meta_description }}">
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
            line-height: 1.8;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }
        h1 { color: #1E3A8A; border-bottom: 3px solid #FF6B35; padding-bottom: 10px; }
        h2 { color: #1E3A8A; margin-top: 40px; padding-left: 15px; border-left: 5px solid #FF6B35; }
        h3 { color: #2563EB; margin-top: 30px; }
        .chart-container {
            text-align: center;
            margin: 30px 0;
        }
        .chart-container img {
            max-width: 100%;
            height: auto;
        }
        .affiliate-box {
            background: linear-gradient(135deg, #FFF7ED 0%, #FFEDD5 100%);
            padding: 30px;
            border: 3px solid #FF6B35;
            border-radius: 12px;
            margin: 40px 0;
            box-shadow: 0 4px 6px rgba(255, 107, 53, 0.1);
        }
        .affiliate-box h3 {
            color: #1E3A8A;
            margin-top: 0;
        }
        .affiliate-button {
            display: inline-block;
            padding: 15px 30px;
            color: white;
            text-decoration: none;
            border-radius: 5px;
            font-weight: bold;
            margin: 10px 5px;
        }
        .affiliate-button:hover {
            opacity: 0.85;
            transform: translateY(-2px);
        }
    </style>
</head>
<body>
    {{ content }}
    <div style="margin-top: 50px; font-size: 0.9em; color: #666; border-top: 2px solid #E5E7EB; padding-top: 30px;">
        <p><strong>データ更新日:</strong> {{ update_date }}</p>
        <p><strong>データ出典:</strong> 警視庁（犯罪統計）、e-Stat（人口統計）、国土交通省（不動産価格）</p>
        <p><strong>免責事項:</strong> 本サイトは情報提供のみを目的としており、不動産の査定・売買の仲介は行っておりません。掲載されている情報は参考値であり、実際の査定額や取引価格とは異なる場合があります。正確な査定をご希望の方は、不動産会社にご相談ください。</p>
    </div>
</body>
</html>"""
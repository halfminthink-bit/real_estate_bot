import markdown
import yaml
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import re

logger = logging.getLogger(__name__)

try:
    from bs4 import BeautifulSoup
    HAS_BS4 = True
except ImportError:
    HAS_BS4 = False
    logger.warning("BeautifulSoup4 not installed. Inline styles will use regex fallback.")

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

    def build(
        self, 
        markdown_path: Path, 
        chart_path: Optional[Path], 
        output_path: Path,
        data: Optional[Dict[str, Any]] = None
    ):
        """
        Markdown → HTML変換
        
        Args:
            markdown_path: Markdownファイルパス
            chart_path: グラフ画像パス（相対パス: ../charts/xxx.png）
            output_path: 出力HTMLパス
            data: データ情報（テーブル生成用）
                {
                    'latest_price': int,        # 最新平均地価
                    'latest_price_min': int,    # 最新最低地価
                    'latest_price_max': int,    # 最新最高地価
                    'latest_point_count': int,  # 調査地点数
                    'price_change_26y': float,  # 26年変動率
                    'price_change_5y': float,   # 5年変動率（オプション）
                    'data_years': int,          # データ年数
                    'asset_value_score': int    # 資産価値スコア
                }
        """
        logger.info(f"Building HTML: {markdown_path} -> {output_path}")

        # Markdown読み込み
        with open(markdown_path, 'r', encoding='utf-8') as f:
            md_content = f.read()

        # 1. <CHART>置換（改善版）
        if '<CHART>' in md_content:
            if chart_path and chart_path.exists():
                chart_html = self._build_chart_html(chart_path)
                md_content = md_content.replace('<CHART>', chart_html)
            else:
                # chart_pathがない場合は削除
                md_content = md_content.replace('<CHART>', '')
                logger.warning("Chart path not found, <CHART> marker removed")
        
        # 2. <DATA_TABLE>置換（新規実装）
        if '<DATA_TABLE>' in md_content:
            if data:
                table_html = self._build_data_table(data)
                md_content = md_content.replace('<DATA_TABLE>', table_html)
            else:
                # dataがない場合は削除
                md_content = md_content.replace('<DATA_TABLE>', '')
                logger.warning("Data not provided, <DATA_TABLE> marker removed")
        
        # 3. 画像パス調整（既存のまま）
        md_content = self._adjust_image_paths(md_content)

        # 4. <AFFILIATE>置換
        # 注意: マーカーの前後のテキスト（安心要素、最後の一押し）はLLMが生成するため保持されます
        # マーカー部分のみを設定ファイルから取得したURLを含むボタンに置き換えます
        # タイトルから町丁目名を抽出
        title = self._extract_title(md_content)
        choume = self._extract_choume_from_title(title)
        affiliate_html = self._build_affiliate_section(choume)
        md_content = md_content.replace('<AFFILIATE>', affiliate_html)

        # 5. Markdown → HTML（既存のまま）
        html_content = markdown.markdown(md_content, extensions=['extra', 'nl2br'])

        # 5.5. インラインCSSを適用（WordPress対応）
        html_content = self._apply_inline_styles(html_content)

        # 6. テンプレート適用（既存のまま）
        if self.template_path.exists():
            with open(self.template_path, 'r', encoding='utf-8') as f:
                template = f.read()
        else:
            template = self._get_default_template()

        title = self._extract_title(md_content)
        h1_title = title
        meta_description = self._extract_description(md_content)
        update_date = datetime.now().strftime('%Y年%m月%d日')
        
        html = template.replace('{{ title }}', title)
        html = html.replace('{{ h1_title }}', h1_title)
        html = html.replace('{{ meta_description }}', meta_description)
        html = html.replace('{{ content }}', html_content)
        html = html.replace('{{ update_date }}', update_date)

        # 7. 保存
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        logger.info(f"HTML saved to {output_path}")

    def _adjust_image_paths(self, md_content: str) -> str:
        """画像パスを相対パスに調整（既存メソッド、そのまま使用）"""
        def adjust_image_path(match):
            alt_text = match.group(1)
            image_filename = match.group(2)
            relative_path = f"../charts/{image_filename}"
            return f"![{alt_text}]({relative_path})"
        
        return re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', adjust_image_path, md_content)

    def _build_chart_html(self, chart_path: Path) -> str:
        """
        グラフ画像のHTML生成
        
        Args:
            chart_path: グラフ画像のパス
        
        Returns:
            str: グラフのHTML
        
        Notes:
            - 画像サイズ: 2084×1036px（アスペクト比 2:1）
            - レスポンシブ対応: max-width 100%
            - PC: 最大800px幅
            - スマホ: 画面幅に合わせる
        """
        # chartsディレクトリからの相対パス
        # html/ から charts/ への参照
        relative_path = f"../charts/{chart_path.name}"
        
        return f'''<figure style="margin: 30px auto; text-align: center; max-width: 800px;">
  <img src="{relative_path}" 
       alt="地価推移グラフ" 
       style="width: 100%; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1); display: block;">
  <figcaption style="margin-top: 10px; font-size: 14px; color: #6b7280; text-align: center;">
    26年間の地価推移（国土交通省データより）
  </figcaption>
</figure>'''

    def _build_data_table(self, data: Dict[str, Any]) -> str:
        """
        データテーブルのHTML生成
        
        Args:
            data: データ情報
                {
                    'latest_price': int,        # 平均地価
                    'latest_price_min': int,    # 最低地価
                    'latest_price_max': int,    # 最高地価
                    'latest_point_count': int,  # 地点数
                    'price_change_26y': float,  # 26年変動率（または5年変動率）
                    'price_change_5y': float,    # 5年変動率（オプション）
                    'data_years': int          # データ年数
                }
        
        Returns:
            str: テーブルのHTML
        
        Notes:
            - シンプルなストライプデザイン
            - 変動率の色: プラス=緑、マイナス=赤
            - レスポンシブ対応: overflow-x: auto
        """
        # データ取得（デフォルト値あり）
        price_avg = data.get('latest_price', 0)
        price_min = data.get('latest_price_min', price_avg)
        price_max = data.get('latest_price_max', price_avg)
        point_count = data.get('latest_point_count', 1)
        
        # 変動率（26年 > 5年の優先順位）
        price_change = data.get('price_change_26y')
        if price_change is None:
            price_change = data.get('price_change_5y', 0)
        
        # データ年数
        data_years = data.get('data_years', 26)
        
        # 変動率の色とサイン
        if price_change > 0:
            change_color = '#16a34a'  # 緑
            change_sign = '+'
        elif price_change < 0:
            change_color = '#dc2626'  # 赤
            change_sign = ''
        else:
            change_color = '#6b7280'  # グレー
            change_sign = ''
        
        return f'''<div style="overflow-x: auto; margin: 30px 0;">
<table style="width: 100%; border-collapse: collapse; margin: 0 auto; max-width: 600px; font-size: 16px;">
  <thead>
    <tr style="background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);">
      <th style="padding: 15px; text-align: left; color: black; font-weight: bold; border-bottom: 2px solid #1e40af;">項目</th>
      <th style="padding: 15px; text-align: right; color: black; font-weight: bold; border-bottom: 2px solid #1e40af;">データ</th>
    </tr>
  </thead>
  <tbody>
    <tr style="background-color: #f8f9fa;">
      <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb;">平均地価</td>
      <td style="padding: 12px 15px; text-align: right; border-bottom: 1px solid #e5e7eb; font-weight: bold; color: #1e3a8a;">{price_avg:,}円/㎡</td>
    </tr>
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb;">価格帯</td>
      <td style="padding: 12px 15px; text-align: right; border-bottom: 1px solid #e5e7eb; font-weight: bold; color: #dc2626;">{price_min:,}〜{price_max:,}円/㎡</td>
    </tr>
    <tr style="background-color: #f8f9fa;">
      <td style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb;">調査地点数</td>
      <td style="padding: 12px 15px; text-align: right; border-bottom: 1px solid #e5e7eb;">{point_count}地点</td>
    </tr>
    <tr style="background-color: #ffffff;">
      <td style="padding: 12px 15px;">{data_years}年間の変動</td>
      <td style="padding: 12px 15px; text-align: right; font-weight: bold; color: {change_color};">{change_sign}{price_change:.1f}%</td>
    </tr>
  </tbody>
</table>
</div>'''

    def _extract_choume_from_title(self, title: str) -> str:
        """
        タイトルから町丁目名を抽出
        
        Args:
            title: タイトル（例: "世田谷区三軒茶屋2丁目の土地売却相場【27.0倍の価格差】"）
        
        Returns:
            str: 町丁目名（例: "三軒茶屋2丁目"）
        """
        # 「区」の後から「丁目」までを抽出
        match = re.search(r'区([^の]+丁目)', title)
        if match:
            return match.group(1)
        return ""
    
    def _build_affiliate_section(self, choume: str = "") -> str:
        """
        アフィリエイトセクションのHTML生成
        
        Args:
            choume: 町丁目名（例: "三軒茶屋2丁目"）
        """
        if not self.affiliate_config:
            return ''
        
        # ボタンテキスト（町丁目名を含める）
        button_text = f"【無料】60秒で{choume}の最高値を調べる" if choume else "【無料】60秒で最高値を調べる"
        
        # アフィリエイト設定からURLを取得（最初の1つ）
        url = '#'
        for key, config in self.affiliate_config.items():
            url = config.get('url', '#')
            break
        
        return f'''
<div style="background-color: #f8f9fa; padding: 30px; border-radius: 8px; margin: 40px 0; text-align: center;">
<h3 style="font-size: 20px; margin-bottom: 15px; color: #333;">💡 あなたの資産価値、無料で知れます</h3>
<p style="font-size: 15px; line-height: 1.8; color: #666; margin-bottom: 15px;">
このデータは参考値です。あなたの物件の正確な価値は、複数の不動産会社に査定してもらうことで分かります。<br/>
無料で査定できるので、今の資産価値を確認してみませんか？
</p>
<p style="font-size: 14px; line-height: 1.6; color: #888; margin-bottom: 25px;">
机上査定なら、電話なしでメールのみで結果を受け取れます
</p>
<div style="margin-bottom: 15px;">
<a href="{url}" rel="nofollow noopener" style="display: inline-block; background-color: #FF6B35; color: white; padding: 15px 30px; text-decoration: none; border-radius: 5px; font-weight: bold; font-size: 16px;" target="_blank">{button_text}</a>
</div>
</div>
'''

    def _apply_inline_styles(self, html: str) -> str:
        """
        最小限のインラインCSSを適用
        
        適用対象:
        - 画像（figure, img, figcaption）
        - 表（table, th, td）
        - 強調（strong）
        - CTAボックス
        
        適用しない:
        - h1, h2, h3（WordPressが管理）
        - p, hr（WordPressのデフォルトを使用）
        
        Args:
            html: 変換されたHTML
        
        Returns:
            インラインCSS付きHTML
        """
        if HAS_BS4:
            return self._apply_inline_styles_bs4(html)
        else:
            return self._apply_inline_styles_regex(html)
    
    def _apply_inline_styles_bs4(self, html: str) -> str:
        """
        BeautifulSoup4を使用して最小限のインラインCSSを適用
        
        適用対象:
        - 画像（figure, img, figcaption）
        - 表（table, th, td）
        - 強調（strong）- font-weightのみ
        - CTAボックス（既に_build_affiliate_sectionで適用済み）
        """
        soup = BeautifulSoup(html, 'html.parser')
        
        # 画像のスタイル
        for figure in soup.find_all('figure'):
            figure['style'] = 'margin: 30px auto; text-align: center;'
        
        for img in soup.find_all('img'):
            img['style'] = 'width: 100%; max-width: 800px; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);'
        
        for figcaption in soup.find_all('figcaption'):
            figcaption['style'] = 'margin-top: 10px; font-size: 14px; color: #6b7280;'
        
        # 表のスタイル
        for table in soup.find_all('table'):
            # テーブルラッパー
            if table.parent.name != 'div' or 'overflow-x' not in table.parent.get('style', ''):
                wrapper = soup.new_tag('div', style='overflow-x: auto; margin: 30px 0;')
                table.wrap(wrapper)
            
            table['style'] = 'width: 100%; border-collapse: collapse; max-width: 600px; margin: 0 auto;'
        
        for thead in soup.find_all('thead'):
            for tr in thead.find_all('tr'):
                tr['style'] = 'background: linear-gradient(135deg, #1e3a8a 0%, #3b82f6 100%);'
        
        for th in soup.find_all('th'):
            th['style'] = 'padding: 15px; color: black; font-weight: bold; border-bottom: 2px solid #1e40af;'
            if th.get('align') == 'right' or 'text-align: right' in th.get('style', ''):
                th['style'] += ' text-align: right;'
        
        for tr in soup.find_all('tr'):
            if tr.parent.name == 'tbody':
                # 偶数行・奇数行で背景色を変える
                tbody_children = [child for child in tr.parent.children if child.name == 'tr']
                row_index = tbody_children.index(tr) if tr in tbody_children else 0
                if row_index % 2 == 0:
                    tr['style'] = 'background-color: #f8f9fa;'
                else:
                    tr['style'] = 'background-color: #ffffff;'
        
        for td in soup.find_all('td'):
            td['style'] = 'padding: 12px 15px; border-bottom: 1px solid #e5e7eb;'
            if td.get('align') == 'right' or 'text-align: right' in td.get('style', ''):
                td['style'] += ' text-align: right; font-weight: bold;'
        
        # 強調（色なし、font-weightのみ）
        for strong in soup.find_all('strong'):
            strong['style'] = 'font-weight: bold;'
        
        # CTAボックス（<AFFILIATE>マーカーが置き換えられた後のdiv）
        # この部分は既にContentGeneratorで生成されているため、builder.pyでは特に処理不要
        
        return str(soup)
    
    def _apply_inline_styles_regex(self, html: str) -> str:
        """
        正規表現を使用して最小限のインラインCSSを適用（BeautifulSoup4がない場合のフォールバック）
        
        適用対象:
        - 画像（figure, img, figcaption）
        - 表（table, th, td）
        - 強調（strong）- font-weightのみ
        """
        # 画像のスタイル
        def add_figure_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; margin: 30px auto; text-align: center;"', tag)
            else:
                return re.sub(r'(<figure[^>]*)>', r'\1 style="margin: 30px auto; text-align: center;">', tag)
        
        html = re.sub(r'<figure[^>]*>', add_figure_style, html)
        
        def add_img_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; width: 100%; max-width: 800px; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);"', tag)
            else:
                return re.sub(r'(<img[^>]*)>', r'\1 style="width: 100%; max-width: 800px; height: auto; border-radius: 8px; box-shadow: 0 4px 12px rgba(0,0,0,0.1);">', tag)
        
        html = re.sub(r'<img[^>]*>', add_img_style, html)
        
        def add_figcaption_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; margin-top: 10px; font-size: 14px; color: #6b7280;"', tag)
            else:
                return re.sub(r'(<figcaption[^>]*)>', r'\1 style="margin-top: 10px; font-size: 14px; color: #6b7280;">', tag)
        
        html = re.sub(r'<figcaption[^>]*>', add_figcaption_style, html)
        
        # 表のスタイル（簡易版 - 複雑な処理はBeautifulSoup推奨）
        def add_table_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; width: 100%; border-collapse: collapse; max-width: 600px; margin: 0 auto;"', tag)
            else:
                return re.sub(r'(<table[^>]*)>', r'\1 style="width: 100%; border-collapse: collapse; max-width: 600px; margin: 0 auto;">', tag)
        
        html = re.sub(r'<table[^>]*>', add_table_style, html)
        
        def add_th_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; padding: 15px; color: black; font-weight: bold; border-bottom: 2px solid #1e40af;"', tag)
            else:
                return re.sub(r'(<th[^>]*)>', r'\1 style="padding: 15px; color: black; font-weight: bold; border-bottom: 2px solid #1e40af;">', tag)
        
        html = re.sub(r'<th[^>]*>', add_th_style, html)
        
        def add_td_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; padding: 12px 15px; border-bottom: 1px solid #e5e7eb;"', tag)
            else:
                return re.sub(r'(<td[^>]*)>', r'\1 style="padding: 12px 15px; border-bottom: 1px solid #e5e7eb;">', tag)
        
        html = re.sub(r'<td[^>]*>', add_td_style, html)
        
        # 強調（色なし、font-weightのみ）
        def add_strong_style(match):
            tag = match.group(0)
            if 'style=' in tag:
                return re.sub(r'style="([^"]*)"', r'style="\1; font-weight: bold;"', tag)
            else:
                return re.sub(r'(<strong[^>]*)>', r'\1 style="font-weight: bold;">', tag)
        
        html = re.sub(r'<strong[^>]*>', add_strong_style, html)
        
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
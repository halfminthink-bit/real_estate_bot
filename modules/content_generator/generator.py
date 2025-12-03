"""
Content Generator - 固定セクション方式
"""
from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from core.models import Area, ScoreResult
from .llm.base_client import BaseLLMClient
from modules.chart_generator.price_graph_generator import PriceGraphGenerator
import logging

logger = logging.getLogger(__name__)


class ContentGenerator:
    """記事生成（固定セクション方式）"""
    
    def __init__(self, config, llm_client: BaseLLMClient):
        self.config = config
        self.llm = llm_client
        self.prompts_dir = config.prompts_dir
        
        # グラフジェネレーター初期化
        self.graph_generator = PriceGraphGenerator(
            output_dir=str(config.charts_dir)
        )
        
        # 取引価格データCollector初期化
        from modules.data_aggregator.collectors.transaction_price_collector import TransactionPriceCollector
        self.transaction_collector = TransactionPriceCollector()
        
        logger.info(f"Initialized ContentGenerator with prompts_dir={self.prompts_dir}")
    
    def generate(
        self,
        area: Area,
        score: ScoreResult,
        data: Dict[str, Any]
    ) -> Tuple[str, Optional[Path]]:
        """
        記事生成（Phase 2対応：プロンプトファイル使用）
        
        Args:
            area: エリア情報
            score: スコア
            data: 収集データ
        
        Returns:
            Tuple[str, Optional[Path]]: (Markdown記事, グラフパス)
        """
        logger.info(f"Generating content for {area.ward}{area.choume}")
        
        # Step 1: グラフ生成
        chart_path = None
        area_name = f"{area.ward.replace('区', '')}_{area.choume.replace('丁目', '')}"
        if 'land_price_history' in data and data['land_price_history']:
            try:
                chart_path = self.graph_generator.generate_price_graph(
                    data['land_price_history'],
                    area_name
                )
                if chart_path:
                    logger.info(f"Generated price graph: {chart_path}")
                else:
                    logger.warning("Price graph generation returned None")
            except Exception as e:
                logger.error(f"Error generating price graph: {e}", exc_info=True)
        
        # Step 2: データ変数を準備（Phase 2対応）
        # プロンプトデータにはファイル名（文字列）を渡す
        price_graph_filename = chart_path.name if chart_path else ""
        prompt_data = self._prepare_prompt_data(area, score, data, price_graph_filename)
        
        # Step 3: プロンプトファイルを読み込んで変数展開
        # アウトライン生成
        outline = self._generate_outline(prompt_data)
        
        # 本文生成
        content = self._generate_content(prompt_data, outline)
        
        # <TRANSACTION_DATA>マーカーをコードで整形したHTMLに置き換え
        transaction_data = self._fetch_transaction_data(area)
        content = self._replace_transaction_marker(content, transaction_data)
        
        logger.info(f"Generated article: {len(content)} characters")
        return content, chart_path
    
    def _prepare_prompt_data(
        self,
        area: Area,
        score: ScoreResult,
        data: Dict[str, Any],
        chart_path: str = ""
    ) -> Dict[str, Any]:
        """
        プロンプトに渡すデータを準備（Phase 2対応）
        
        Args:
            area: エリア情報
            score: スコア
            data: 収集データ
            chart_path: グラフファイルパス
        
        Returns:
            Dict: プロンプトデータ
        """
        # ═══════════════════════════════════════
        # 取引価格データ取得
        # ═══════════════════════════════════════
        transaction_data = self._fetch_transaction_data(area)
        
        # 地価履歴データ
        price_history = data.get('land_price_history', [])
        
        # データ年数を計算
        data_years = len(price_history) if price_history else 0
        oldest_year = price_history[0]['year'] if price_history else 0
        latest_year = price_history[-1]['year'] if price_history else 0
        
        # 最古の価格
        oldest_price = price_history[0]['price'] if price_history else 0
        
        # 価格帯の計算
        point_count = data.get('latest_point_count', 1)
        price_min = data.get('latest_price_min', data.get('latest_price', 0))
        price_max = data.get('latest_price_max', data.get('latest_price', 0))
        price_avg = data.get('latest_price', 0)
        
        # 価格帯の幅（倍率）- land_price_collectorで計算済みの値を使用
        price_ratio = data.get('price_ratio', price_max / price_min if price_min > 0 else 1.0)
        has_wide_range = data.get('has_wide_range', False)
        
        # 長期変動率（26年 or 5年）
        price_change_long = data.get('price_change_26y', 
                                     data.get('price_change_5y', 0))
        
        # 【追加】タイトル候補生成
        title_candidates = self._generate_title_candidates(
            ward=area.ward,
            choume=area.choume,
            price_ratio=price_ratio,
            price_avg=price_avg,
            point_count=point_count,
            price_change_long=price_change_long,
            data_years=data_years,
            has_wide_range=has_wide_range
        )
        
        # 【追加】年次詳細データの整形
        # リーマンショック期の変動率（2008-2009年）
        lehman_change = None
        for i, history_data in enumerate(price_history):
            if history_data['year'] == 2009 and i > 0:
                lehman_change = history_data['change']
                break
        
        # コロナ禍期の変動率（2020-2021年）
        covid_change = None
        for i, history_data in enumerate(price_history):
            if history_data['year'] == 2021 and i > 0:
                covid_change = history_data['change']
                break
        
        # 年次データのサマリー（LLMが読みやすい形式）
        history_summary = []
        for history_data in price_history:
            history_summary.append(
                f"{history_data['year']}年: {history_data['price']:,}円/㎡ (前年比{history_data['change']:+.1f}%)"
            )
        
        # プロンプトデータ
        prompt_data = {
            # 基本情報
            'ward': area.ward,
            'choume': area.choume,
            'asset_value_score': score.asset_value_score,
            
            # データ期間情報
            'data_years': data_years,
            'oldest_year': oldest_year,
            'latest_year': latest_year,
            'oldest_price': oldest_price,
            
            # 価格情報
            'price_avg': price_avg,
            'price_min': price_min,
            'price_max': price_max,
            'price_ratio': price_ratio,
            'price_ratio_str': f"{price_ratio:.1f}",  # 文字列フォーマット
            'has_wide_range': has_wide_range,
            'point_count': point_count,
            
            # 変動率
            'price_change_long': price_change_long,
            
            # 【追加】タイトル候補
            'title_candidates': title_candidates,
            'price_change_5y': data.get('price_change_5y', 0),
            'price_change_1y': data.get('price_change_1y', 0),
            
            # 地価履歴（グラフ用）
            'land_price_history': price_history,
            
            # 【追加】年次詳細データ
            'land_price_history_detail': '\n'.join(history_summary),
            'lehman_change': f"{lehman_change:+.1f}%" if lehman_change is not None else "データなし",
            'covid_change': f"{covid_change:+.1f}%" if covid_change is not None else "データなし",
            
            # 国土数値情報
            'land_use': data.get('land_use', ''),
            'building_coverage_ratio': data.get('building_coverage_ratio', 0),
            'floor_area_ratio': data.get('floor_area_ratio', 0),
            'road_direction': data.get('road_direction', ''),
            'road_width': data.get('road_width', 0),
            'land_area': data.get('land_area', 0),
            'nearest_station': data.get('nearest_station', ''),
            'station_distance': data.get('station_distance', 0),
            
            # グラフパス
            'chart_path': chart_path,
            
            # 取引価格データ
            'area_name': transaction_data['area_name'],
            'transaction_period': transaction_data['transaction_period'],
            'transaction_years': transaction_data['transaction_years'],
            'transaction_count': transaction_data['transaction_count'],
            'transaction_avg': transaction_data['transaction_avg'],
            'transaction_min': transaction_data['transaction_min'],
            'transaction_max': transaction_data['transaction_max'],
            'has_transaction_data': transaction_data['has_transaction_data'],
            'transaction_samples': transaction_data['transaction_samples'],
        }
        
        # 【デバッグ用ログ】
        logger.info(f"Prompt data prepared for {area.choume}:")
        logger.info(f"  lehman_change: {prompt_data.get('lehman_change')}")
        logger.info(f"  covid_change: {prompt_data.get('covid_change')}")
        logger.info(f"  land_price_history_detail (first 3 years):")
        for line in history_summary[:3]:
            logger.info(f"    {line}")
        
        return prompt_data
    
    def _fetch_transaction_data(self, area: Area) -> Dict[str, Any]:
        """
        取引価格データを取得して整形（過去3年分）
        
        Args:
            area: エリア情報
        
        Returns:
            Dict: 取引価格データ（整形済み）
        """
        try:
            # 町丁目を正規化（"上用賀6丁目" → "上用賀"）
            import re
            match = re.search(r'^([^0-9]+)', area.choume)
            area_name = match.group(1) if match else area.choume
            
            # APIから取引データ取得（過去3年分）
            raw_data = self.transaction_collector.get_area_transactions(
                ward=area.ward,
                choume=area.choume,
                years=3  # 過去3年分（2022-2024年）
            )
            
            # データがない場合
            if not raw_data.get('has_transaction_data', False):
                logger.info(f"No transaction data for {area.choume} (past 3 years)")
                return {
                    'area_name': area_name,
                    'transaction_period': raw_data.get('transaction_period', '2022年〜2024年'),
                    'transaction_years': raw_data.get('transaction_years', 3),
                    'transaction_count': 0,
                    'transaction_avg': 0,
                    'transaction_min': 0,
                    'transaction_max': 0,
                    'has_transaction_data': False,
                    'transaction_samples': []
                }
            
            # 取引事例を整形（上位10件から代表例を3件）
            transaction_samples = []
            for tx in raw_data.get('transaction_samples', [])[:3]:
                transaction_samples.append({
                    'type': tx.get('Type', ''),
                    'price': tx.get('TradePrice', ''),
                    'building_year': tx.get('BuildingYear', ''),
                    'floor_plan': tx.get('FloorPlan', ''),
                    'city_planning': tx.get('CityPlanning', ''),
                    'coverage_ratio': tx.get('CoverageRatio', ''),
                    'floor_area_ratio': tx.get('FloorAreaRatio', ''),
                    'land_shape': tx.get('LandShape', ''),
                    'frontage': tx.get('Frontage', ''),
                    'year': tx.get('year', ''),
                    'quarter': tx.get('quarter', '')
                })
            
            logger.info(f"Fetched transaction data for {area.choume}: "
                       f"{raw_data['transaction_count']} transactions (past {raw_data['transaction_years']} years), "
                       f"avg={raw_data['transaction_avg']:,}円")
            
            return {
                'area_name': area_name,
                'transaction_period': raw_data.get('transaction_period', '2022年〜2024年'),
                'transaction_years': raw_data.get('transaction_years', 3),
                'transaction_count': raw_data['transaction_count'],
                'transaction_avg': raw_data['transaction_avg'],
                'transaction_min': raw_data['transaction_min'],
                'transaction_max': raw_data['transaction_max'],
                'has_transaction_data': True,
                'transaction_samples': transaction_samples
            }
            
        except Exception as e:
            logger.error(f"Error fetching transaction data for {area.choume}: {e}", exc_info=True)
            # エラー時は空データを返す
            return {
                'area_name': area.choume,
                'transaction_period': '2022年〜2024年',
                'transaction_years': 3,
                'transaction_count': 0,
                'transaction_avg': 0,
                'transaction_min': 0,
                'transaction_max': 0,
                'has_transaction_data': False,
                'transaction_samples': []
            }
    
    def _generate_title_candidates(
        self,
        ward: str,
        choume: str,
        price_ratio: float,
        price_avg: int,
        point_count: int,
        price_change_long: float,
        data_years: int,
        has_wide_range: bool
    ) -> str:
        """
        タイトル候補を生成（優先度順）
        
        【重要】キーワードは「土地売却相場」「土地価格」を使用
        「地価」は研究的すぎるため使用禁止
        
        Returns:
            str: フォーマット済みのタイトル候補文字列
        """
        candidates = []
        
        # 【優先度1】価格帯の幅 + 売却相場
        if has_wide_range:
            candidates.append(
                f"【候補1】 {ward}{choume}の土地売却相場【{price_ratio:.1f}倍の価格差】\n"
                f"理由: 同じエリアでも大きな価格差があることを強調し、査定の必要性を訴求します"
            )
        
        # 【優先度2】具体的金額 + 売却相場
        if price_avg > 1000000:
            price_man = int(price_avg / 10000)
            candidates.append(
                f"【候補2】 {ward}{choume}の土地売却相場【2025年：{price_man}万円/㎡】\n"
                f"理由: 最新の具体的な金額を提示し、売却を検討している人に刺さります"
            )
        
        # 【優先度3】変動率 + 土地価格
        if abs(price_change_long) > 5:
            sign = '+' if price_change_long > 0 else ''
            candidates.append(
                f"【候補3】 {ward}{choume}の土地価格【{data_years}年で{sign}{price_change_long:.1f}%】\n"
                f"理由: 長期的な価値の変動を示し、資産価値の変化を訴求します"
            )
        
        # 【優先度4】デフォルト（売却相場）
        if not candidates:
            candidates.append(
                f"【候補4】 {ward}{choume}の土地売却相場【{data_years}年分のデータで分析】\n"
                f"理由: 公的データの信頼性を強調しつつ、売却を意識させます"
            )
        
        return "\n\n".join(candidates)
    
    def _load_prompt_file(self, filename: str) -> str:
        """
        プロンプトファイルを読み込む
        
        Args:
            filename: プロンプトファイル名（例: 'persona.txt'）
        
        Returns:
            str: プロンプト内容
        """
        prompt_path = self.prompts_dir / filename
        if not prompt_path.exists():
            logger.warning(f"Prompt file not found: {prompt_path}")
            return ""
        
        with open(prompt_path, 'r', encoding='utf-8') as f:
            return f.read()
    
    def _expand_template(self, template: str, data: Dict[str, Any]) -> str:
        """
        テンプレート内の変数を展開
        
        Args:
            template: テンプレート文字列
            data: 変数データ
        
        Returns:
            str: 展開後の文字列
        """
        import re
        
        # 変数を展開（{変数名} または {変数名:フォーマット}形式）
        pattern = r'\{(\w+)(?::([^}]+))?\}'
        
        def replace_match(match):
            var_name = match.group(1)
            format_spec = match.group(2) if match.group(2) else None
            
            if var_name in data:
                value = data[var_name]
                
                # フォーマット指定がある場合
                if format_spec:
                    try:
                        # カスタムフォーマット（例: {price_avg:,}）
                        if format_spec == ',':
                            if isinstance(value, (int, float)):
                                return f"{value:,.0f}"
                        elif format_spec.startswith('+'):
                            # 変動率フォーマット（例: {price_change_long:+.1f}）
                            if isinstance(value, (int, float)):
                                return f"{value:+.1f}" if value >= 0 else f"{value:.1f}"
                        else:
                            # その他のフォーマット
                            return format_spec.format(value)
                    except Exception as e:
                        logger.warning(f"Format error for {var_name}: {e}")
                        return str(value)
                else:
                    # デフォルトフォーマット（変数名から推測）
                    if isinstance(value, (int, float)):
                        if 'price' in var_name.lower() and ('min' in var_name.lower() or 'max' in var_name.lower() or 'avg' in var_name.lower() or 'oldest' in var_name.lower()):
                            # 価格（カンマ区切り）
                            return f"{value:,.0f}"
                        elif 'change' in var_name.lower():
                            # 変動率（+/-記号付き）
                            return f"{value:+.1f}" if value >= 0 else f"{value:.1f}"
                        elif 'ratio' in var_name.lower():
                            # 倍率（小数点1桁）
                            return f"{value:.1f}"
                    return str(value)
            else:
                logger.warning(f"Variable not found in data: {var_name}")
                return match.group(0)
        
        result = re.sub(pattern, replace_match, template)
        
        return result
    
    def _generate_outline(self, prompt_data: Dict[str, Any]) -> str:
        """
        アウトライン生成（プロンプトファイル使用）
        
        Args:
            prompt_data: プロンプトデータ
        
        Returns:
            str: アウトライン
        """
        # プロンプトファイルを読み込み
        persona = self._load_prompt_file('persona.txt')
        outline_template = self._load_prompt_file('outline.txt')
        
        if not outline_template:
            logger.error("outline.txt not found")
            return ""
        
        # outline_template用のデータを準備
        # prompt_dataにpersonaを追加
        expanded_data = {
            **prompt_data,
            'persona': persona  # ペルソナテキスト全体
        }
        
        # テンプレートを一括展開
        prompt = self._expand_template(outline_template, expanded_data)
        
        # LLMで生成
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=2000,
            temperature=0.7
        )
        
        return response.strip()
    
    def _generate_content(self, prompt_data: Dict[str, Any], outline: str) -> str:
        """
        本文生成（プロンプトファイル使用）
        
        Args:
            prompt_data: プロンプトデータ
            outline: 生成されたアウトライン
        
        Returns:
            str: 本文
        """
        # プロンプトファイルを読み込み
        persona = self._load_prompt_file('persona.txt')
        content_template = self._load_prompt_file('content.txt')
        
        if not content_template:
            logger.error("content.txt not found")
            return ""
        
        # データ情報を文字列化（汎用的な変数展開）
        data_text = f"""- 期間: {prompt_data['data_years']}年分（{prompt_data['oldest_year']}-{prompt_data['latest_year']}年）
- 平均地価: {prompt_data['price_avg']:,}円/㎡
- 価格帯: {prompt_data['price_min']:,}〜{prompt_data['price_max']:,}円/㎡（{prompt_data['point_count']}地点）
- {prompt_data['data_years']}年変動: {prompt_data['price_change_long']:+.1f}%"""
        
        # 取引価格データを文字列化
        transaction_text = ""
        if prompt_data['has_transaction_data']:
            transaction_text = f"""- 対象エリア: {prompt_data['area_name']}エリア全体
- 取引期間: {prompt_data['transaction_period']}（過去{prompt_data['transaction_years']}年分）
- 取引件数: {prompt_data['transaction_count']}件
- 平均取引価格: {prompt_data['transaction_avg']:,}円
- 価格帯: {prompt_data['transaction_min']:,}〜{prompt_data['transaction_max']:,}円"""
        else:
            transaction_text = "取引データなし（地価公示データのみで記事を構成してください）"
        
        # content_template用のデータを準備
        # 既存のprompt_dataに、persona, outline, dataを追加
        expanded_data = {
            **prompt_data,              # 既存のデータ（ward, choume, 価格情報など）
            'persona': persona,         # ペルソナテキスト全体
            'outline': outline,         # 生成されたアウトライン全体
            'data': data_text,          # 地価公示データ情報（整形済み文字列）
            'transaction_data': transaction_text  # 取引価格データ情報（整形済み文字列）
        }
        
        # テンプレートを一括展開
        prompt = self._expand_template(content_template, expanded_data)
        
        # LLMで生成
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=8000,
            temperature=0.7
        )
        
        return response.strip()
    
    def _replace_transaction_marker(self, content: str, transaction_data: Dict[str, Any]) -> str:
        """
        <TRANSACTION_DATA>マーカーを取引データで置き換え
        
        LLMに書かせるのではなく、コードで整形したHTMLを挿入する
        
        Args:
            content: Markdown本文
            transaction_data: 取引データ
        
        Returns:
            マーカーを置き換えた本文
        """
        if not transaction_data.get('has_transaction_data'):
            # データがない場合はマーカーを削除
            return content.replace('<TRANSACTION_DATA>', '')
        
        # データを整形
        period = transaction_data.get('transaction_period', '2022年〜2024年')
        count = transaction_data.get('transaction_count', 0)
        avg = transaction_data.get('transaction_avg', 0)
        min_price = transaction_data.get('transaction_min', 0)
        max_price = transaction_data.get('transaction_max', 0)
        
        # 金額を読みやすく変換
        def format_price(price: int) -> str:
            """金額を読みやすい形式に変換（億円・千万円・万円単位）"""
            if price >= 100000000:  # 1億円以上
                oku = price // 100000000  # 億円部分
                senman = (price % 100000000) // 10000000  # 千万円部分
                if senman > 0:
                    return f'{oku}億{senman}千万円'
                else:
                    return f'{oku}億円'
            elif price >= 10000000:  # 1000万円以上
                # 千万円単位で表示（例: 6,572万円 → 6,572万円）
                return f'{price / 10000:.0f}万円'
            elif price >= 10000:  # 1万円以上
                return f'{price / 10000:.0f}万円'
            else:
                return f'{price:,}円'
        
        avg_str = format_price(avg)
        min_str = format_price(min_price)
        max_str = format_price(max_price)
        
        # HTMLを生成
        transaction_html = f'''
<div style="background-color: #f0f9ff; padding: 20px; border-left: 4px solid #3b82f6; margin: 30px 0;">
  <h3 style="margin-top: 0; color: #1e40af;">実際の取引価格データ（{period}）</h3>
  <ul style="list-style: none; padding-left: 0;">
    <li style="margin-bottom: 8px;"><strong style="font-weight: bold;">取引件数:</strong> {count:,}件</li>
    <li style="margin-bottom: 8px;"><strong style="font-weight: bold;">平均取引価格:</strong> 約{avg_str}</li>
    <li style="margin-bottom: 8px;"><strong style="font-weight: bold;">価格帯:</strong> {min_str}〜{max_str}</li>
  </ul>
  <p style="font-size: 14px; color: #6b7280; margin-bottom: 0;">
    （出典：国土交通省 不動産取引価格情報）
  </p>
</div>
'''
        
        return content.replace('<TRANSACTION_DATA>', transaction_html)
    
    def _generate_intro(self, area: Area, score: ScoreResult, data: Dict) -> str:
        """イントロ生成（LLM 500文字）"""
        latest_price = data.get('latest_price', 0)
        
        prompt = f"""あなたは不動産資産価値アナリストです。

以下のエリアのオーナーに向けて、「資産価値を知ることの重要性」を訴えるイントロを500文字程度で書いてください。

【エリア】
{area.ward}{area.choume}

【資産価値スコア】
{score.asset_value_score}点

【最新地価】
{latest_price:,}円/㎡

【要点】
- 多くのオーナーが自分の資産の価値を知らない現実
- 銀行預金は確認するのに、不動産は何年も確認していない
- この記事では、客観的データで資産価値を証明

【文体】
- 丁寧語ベース
- 時々「〜なんですよね」などの口語
- 押し付けがましくない

【出力】
Markdownの## 見出し付きで出力してください。
見出し: ## あなたの資産、正確な価値を知っていますか？
"""
        
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.strip()
    
    def _generate_analysis(self, area: Area, data: Dict) -> str:
        """データ解釈生成（LLM 800文字）"""
        latest_price = data.get('latest_price', 0)
        price_change_5y = data.get('price_change_5y', 0)
        price_change_1y = data.get('price_change_1y', 0)
        land_use = data.get('land_use', '不明')
        building_coverage_ratio = data.get('building_coverage_ratio', '-')
        floor_area_ratio = data.get('floor_area_ratio', '-')
        road_direction = data.get('road_direction', '-')
        road_width = data.get('road_width', '-')
        
        prompt = f"""あなたは不動産資産価値アナリストです。

以下のデータを解釈して、5つの価値を800文字程度で解説してください。

【エリア】
{area.ward}{area.choume}

【地価データ】
- 最新地価: {latest_price:,}円/㎡
- 5年変動率: {price_change_5y:.1f}%
- 1年変動率: {price_change_1y:.1f}%

【国土数値情報】
- 用途地域: {land_use}
- 建蔽率: {building_coverage_ratio}%
- 容積率: {floor_area_ratio}%
- 前面道路: {road_direction}向き {road_width}m

【5つの価値】
1. 地価データ：世田谷区平均との比較
2. 用途地域：{land_use}の希少性と意味
3. 開発余地：容積率{floor_area_ratio}%の可能性
4. 立地条件：{road_direction}向き前面道路の価値
5. 長期安定性：{price_change_5y:.1f}%上昇の意味

【各項目の説明】
各項目について150-200文字で説明してください。

【文体】
- 「実は〜」「データを見ると〜」などの表現
- 専門用語は平易に解説
- 丁寧語ベース

【出力】
Markdownの## 見出し付きで出力してください。
見出し: ## このデータが証明する5つの価値
"""
        
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=1200,
            temperature=0.7
        )
        
        return response.strip()
    
    def _generate_conclusion(self, area: Area, data: Dict) -> str:
        """まとめ+CTA生成（LLM 500文字）"""
        prompt = f"""あなたは不動産資産価値アナリストです。

以下のエリアについて、まとめと無料査定への誘導を500文字程度で書いてください。

【エリア】
{area.ward}{area.choume}

【要点】
- データで証明された資産価値
- 売る・売らないは別として、まず正確な価値を知ることが重要
- 無料査定で知識武装
- 複数社比較のメリット

【トーン】
- 押し売りしない
- 「知ることの価値」を強調
- 査定 = 資産価値を知る手段（売却ではない）

【出力】
Markdownの## 見出し付きで出力してください。
見出し: ## だから今、正確な価値を知るべき
"""
        
        response = self.llm.generate(
            prompt=prompt,
            max_tokens=800,
            temperature=0.7
        )
        
        return response.strip()
    
    def _generate_kokudo_section(self, data: Dict) -> str:
        """国土数値情報セクション（コード生成）"""
        
        # 用途地域の説明
        land_use = data.get('land_use', '不明')
        land_use_explain = self._explain_land_use(land_use)
        
        # 世田谷区平均との比較
        avg_price = 719776  # 世田谷区平均
        latest_price = data.get('latest_price', 0)
        price_diff = ((latest_price / avg_price) - 1) * 100 if latest_price > 0 else 0
        
        price_change_5y = data.get('price_change_5y', 0)
        avg_change_5y = 12.5  # 世田谷区平均の5年変動率
        
        building_coverage_ratio = data.get('building_coverage_ratio', '-')
        floor_area_ratio = data.get('floor_area_ratio', '-')
        road_direction = data.get('road_direction', '-')
        road_width = data.get('road_width', '-')
        land_area = data.get('land_area', '-')
        
        # 地積の坪数計算（数値の場合のみ）
        land_area_text = f"{land_area}㎡"
        if isinstance(land_area, (int, float)) and land_area > 0:
            tsubo = land_area * 0.3025
            land_area_text = f"{land_area}㎡（約{tsubo:.1f}坪）"
        
        section = f"""
### あなたの土地の詳細データ

| 項目 | 値 | 意味 |
|------|-----|------|
| **用途地域** | {land_use} | {land_use_explain} |
| **建蔽率** | {building_coverage_ratio}% | 敷地の{building_coverage_ratio}%まで建築可能 |
| **容積率** | {floor_area_ratio}% | 敷地面積の{floor_area_ratio}%の延床面積まで建築可能 |
| **前面道路** | {road_direction}向き {road_width}m | 日照・再建築性に影響 |
| **地積** | {land_area_text} | 土地の面積 |

**世田谷区平均との比較**

| 項目 | あなたの土地 | 世田谷区平均 | 差 |
|------|-------------|--------------|-----|
| 地価 | {latest_price:,}円/㎡ | {avg_price:,}円/㎡ | {'+' if price_diff > 0 else ''}{price_diff:.1f}% |
| 5年変動率 | {'+' if price_change_5y > 0 else ''}{price_change_5y:.1f}% | +{avg_change_5y:.1f}% | {'+' if (price_change_5y - avg_change_5y) > 0 else ''}{(price_change_5y - avg_change_5y):.1f}pt |
"""
        return section
    
    def _generate_score_section(self, score: ScoreResult, data: Dict) -> str:
        """スコア内訳セクション（コード生成）"""
        
        price_change_5y = data.get('price_change_5y', 0)
        land_use = data.get('land_use', '-')
        floor_area_ratio = data.get('floor_area_ratio', '-')
        road_direction = data.get('road_direction', '-')
        road_width = data.get('road_width', '-')
        
        section = f"""
### 資産価値スコア {score.asset_value_score}点の内訳

| 評価項目 | 説明 | 理由 |
|---------|------|------|
| **地価上昇トレンド** | 過去の価格推移 | 5年で{'+' if price_change_5y > 0 else ''}{price_change_5y:.1f}%の変動 |
| **用途地域の希少性** | 法的な環境保全 | {land_use}は世田谷区内でも限定的 |
| **容積率（開発余地）** | 将来の建て替え可能性 | {floor_area_ratio}%の開発ポテンシャル |
| **前面道路条件** | 日照・再建築性 | {road_direction}向き・幅員{road_width}m |
| **長期安定性** | 価格の底堅さ | 安定した推移 |
| **合計** | | **{score.asset_value_score}点** |
"""
        return section
    
    def _generate_glossary(self, data: Dict) -> str:
        """用語解説（定型文）"""
        
        glossary = """
## 用語解説

### 用途地域とは

都市計画法に基づいて定められた、土地利用の制限を示す区分です。どのような建物が建てられるか、どのような環境が保たれるかが法的に定められています。

**主な用途地域**:
- **第一種低層住居専用地域（1低専）**: 低層住宅中心、高さ制限あり
- **近隣商業地域（近商）**: 商業施設と住宅が共存
- **商業地域**: 商業・業務施設が中心

### 建蔽率・容積率とは

**建蔽率**: 敷地面積に対する建築面積（建物を真上から見た面積）の割合
- 例: 建蔽率60%、敷地100㎡ → 建築面積60㎡まで

**容積率**: 敷地面積に対する延床面積（各階の床面積の合計）の割合
- 例: 容積率200%、敷地100㎡ → 延床面積200㎡まで（2階建てなら各階100㎡）

容積率が高いほど、高層建築や広い延床面積の建物が建てられます。
"""
        return glossary
    
    def _explain_land_use(self, land_use: str) -> str:
        """用途地域の簡潔な説明"""
        explanations = {
            '1低専': '低層住宅中心、環境が法的に守られた地域',
            '近商': '商業施設と住宅が共存する地域',
            '商業': '商業・業務施設中心の地域',
            '1中専': '中高層住宅が可能な地域',
            '1住居': '住宅と小規模店舗が共存する地域',
            '準住居': '幹線道路沿いの住宅地域',
            '2住居': '住宅と店舗が混在する地域',
        }
        return explanations.get(land_use, '詳細不明')
    
    def _build_article(
        self,
        area: Area,
        price_graph_filename: str,
        kokudo_section: str,
        score_section: str,
        llm_intro: str,
        llm_analysis: str,
        glossary: str,
        llm_conclusion: str
    ) -> str:
        """記事を結合"""
        
        # タイトル生成
        title = f"# {area.choume}の土地、実は世田谷区内トップクラスの価値\n\n"
        
        # データセクション
        graph_section = ""
        if price_graph_filename:
            graph_section = f"""
### 地価推移（過去5年）

![地価推移]({price_graph_filename})

"""
        
        data_section = f"""
## あなたの土地の価値データ

{graph_section}{kokudo_section}

{score_section}
"""
        
        # CTA
        cta = """
---

**無料で資産価値を確認する**

<AFFILIATE>
"""
        
        # 全体結合
        article = (
            title +
            llm_intro + "\n\n" +
            data_section + "\n\n" +
            llm_analysis + "\n\n" +
            glossary + "\n\n" +
            llm_conclusion + "\n\n" +
            cta
        )
        
        return article

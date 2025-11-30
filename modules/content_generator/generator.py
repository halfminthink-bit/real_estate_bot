"""
Content Generator - 固定セクション方式
"""
from pathlib import Path
from typing import Dict, Any
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
        
        logger.info(f"Initialized ContentGenerator with prompts_dir={self.prompts_dir}")
    
    def generate(
        self,
        area: Area,
        score: ScoreResult,
        data: Dict[str, Any]
    ) -> str:
        """
        記事生成（固定セクション方式）
        
        Args:
            area: エリア情報
            score: スコア
            data: 収集データ
        
        Returns:
            str: Markdown記事
        """
        logger.info(f"Generating content for {area.ward}{area.choume}")
        
        # Step 1: グラフ生成
        area_name = f"{area.ward.replace('区', '')}_{area.choume.replace('丁目', '')}"
        price_graph_filename = ""
        if 'land_price_history' in data and data['land_price_history']:
            price_graph_filename = self.graph_generator.generate_price_graph(
                data['land_price_history'],
                area_name
            )
            logger.info(f"Generated price graph: {price_graph_filename}")
        
        # Step 2: データセクション生成（コード）
        kokudo_section = self._generate_kokudo_section(data)
        score_section = self._generate_score_section(score, data)
        
        # Step 3: LLM生成（3セクション）
        llm_intro = self._generate_intro(area, score, data)
        llm_analysis = self._generate_analysis(area, data)
        llm_conclusion = self._generate_conclusion(area, data)
        
        # Step 4: 用語解説（定型文）
        glossary = self._generate_glossary(data)
        
        # Step 5: テンプレート結合
        article = self._build_article(
            area=area,
            price_graph_filename=price_graph_filename,
            kokudo_section=kokudo_section,
            score_section=score_section,
            llm_intro=llm_intro,
            llm_analysis=llm_analysis,
            glossary=glossary,
            llm_conclusion=llm_conclusion
        )
        
        logger.info(f"Generated article: {len(article)} characters")
        return article
    
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

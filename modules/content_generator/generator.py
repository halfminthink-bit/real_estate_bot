from pathlib import Path
from typing import Dict, Any
from core.models import Area, ScoreResult
from .llm.base_client import BaseLLMClient
import logging

logger = logging.getLogger(__name__)

class ContentGenerator:
    """記事生成（2段階）"""

    def __init__(self, config, llm_client: BaseLLMClient):
        self.config = config
        self.llm = llm_client
        self.prompts_dir = config.prompts_dir
        logger.info(f"Initialized ContentGenerator with prompts_dir={self.prompts_dir}")

    def generate(self, area: Area, score: ScoreResult, data: Dict[str, Any]) -> str:
        """
        2段階生成
        1. アウトライン生成
        2. 本文生成

        Returns:
            Markdown形式の記事
        """
        logger.info(f"Generating content for {area.ward}{area.choume}")

        # Stage 1: アウトライン生成
        outline = self._generate_outline(area, score, data)
        logger.info("Generated outline")

        # Stage 2: 本文生成
        content = self._generate_content(area, score, data, outline)
        logger.info("Generated full content")

        return content

    def _generate_outline(self, area: Area, score: ScoreResult, data: Dict) -> str:
        """アウトライン生成"""
        persona = self._load_prompt('persona.txt')
        outline_template = self._load_prompt('outline.txt')

        prompt = outline_template.format(
            persona=persona,
            ward=area.ward,
            choume=area.choume,
            total_score=score.total_score,
            safety_score=score.safety_score,
            education_score=score.education_score,
            convenience_score=score.convenience_score,
            asset_value_score=score.asset_value_score,
            living_score=score.living_score,
            crime_count=data.get('crime_count', 0)
        )

        return self.llm.generate(prompt, temperature=0.7, max_tokens=2000)

    def _generate_content(self, area: Area, score: ScoreResult, data: Dict, outline: str) -> str:
        """本文生成"""
        persona = self._load_prompt('persona.txt')
        content_template = self._load_prompt('content.txt')

        # データを文字列化
        data_str = self._format_data(area, score, data)

        prompt = content_template.format(
            persona=persona,
            outline=outline,
            data=data_str
        )

        return self.llm.generate(prompt, temperature=0.7, max_tokens=8000)

    def _load_prompt(self, filename: str) -> str:
        """プロンプトファイル読み込み"""
        path = self.prompts_dir / filename
        if not path.exists():
            logger.error(f"Prompt file not found: {path}")
            raise FileNotFoundError(f"Prompt file not found: {path}")

        with open(path, 'r', encoding='utf-8') as f:
            return f.read()

    def _format_data(self, area: Area, score: ScoreResult, data: Dict) -> str:
        """データを読みやすい文字列に整形"""
        formatted = f"""
【エリア情報】
- 区: {area.ward}
- 町丁目: {area.choume}

【スコアデータ】
- 総合スコア: {score.total_score}/100
- 治安スコア: {score.safety_score}/100
- 教育スコア: {score.education_score}/100
- 利便性スコア: {score.convenience_score}/100
- 資産価値スコア: {score.asset_value_score}/100
- 住環境スコア: {score.living_score}/100

【詳細データ】
- 犯罪件数: {data.get('crime_count', 0)}件/年
- データ年月: {data.get('year', 2025)}年{data.get('month', 10)}月
- データ出典: {data.get('source', '警視庁')}
"""
        return formatted

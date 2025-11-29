import yaml
from pathlib import Path
from typing import Dict, Any
from .base_scorer import BaseScorer
import logging

logger = logging.getLogger(__name__)

class SafetyScorer(BaseScorer):
    """治安スコア計算"""

    def __init__(self, rules_path: Path):
        with open(rules_path, 'r', encoding='utf-8') as f:
            rules = yaml.safe_load(f)
        self.rules = rules.get('safety', {})
        logger.info("Initialized SafetyScorer")

    def calculate(self, data: Dict[str, Any]) -> int:
        """
        犯罪件数からスコア計算

        Args:
            data: {'crime_count': int}

        Returns:
            0-100のスコア
        """
        crime_count = data.get('crime_count', 0)
        logger.debug(f"Calculating safety score for crime_count={crime_count}")

        # スコアリングルールに基づいて計算
        for level, rule in self.rules.items():
            max_crimes = rule.get('max_crimes', 999)
            if crime_count <= max_crimes:
                score_range = rule.get('score_range', [0, 100])
                min_score, max_score = score_range

                # 線形補間でスコア計算
                # 犯罪件数が少ないほど高スコア
                if level == 'excellent':
                    prev_max = 0
                elif level == 'good':
                    prev_max = self.rules.get('excellent', {}).get('max_crimes', 30)
                elif level == 'average':
                    prev_max = self.rules.get('good', {}).get('max_crimes', 50)
                else:
                    prev_max = self.rules.get('average', {}).get('max_crimes', 80)

                # 範囲内での位置を計算
                range_size = max_crimes - prev_max
                if range_size > 0:
                    position = (crime_count - prev_max) / range_size
                    score = int(max_score - (max_score - min_score) * position)
                else:
                    score = max_score

                logger.debug(f"Safety score calculated: {score}")
                return max(0, min(100, score))

        # ルールに該当しない場合は最低スコア
        logger.warning(f"Crime count {crime_count} exceeds all rules, returning 0")
        return 0

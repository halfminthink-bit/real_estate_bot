from pathlib import Path
from typing import Dict, Any
from datetime import datetime
from core.models import ScoreResult, Area
from .scorers.safety_scorer import SafetyScorer
import logging

logger = logging.getLogger(__name__)

class ScoreCalculator:
    """スコア計算のコーディネーター"""

    def __init__(self, rules_path: Path):
        self.safety_scorer = SafetyScorer(rules_path)
        # 資産価値スコア計算器を初期化
        from .scorers.asset_value_scorer import AssetValueScorer
        self.asset_value_scorer = AssetValueScorer()
        logger.info("Initialized ScoreCalculator")

    def calculate(self, area: Area, data: Dict[str, Any]) -> ScoreResult:
        """全スコアを計算"""
        logger.info(f"Calculating scores for area {area.area_id}")

        # 治安スコア（実装済み）
        safety = self.safety_scorer.calculate(data)

        # Phase 1では他のスコアはダミー値
        # Phase 2で実装予定
        education = self._calculate_education_dummy(data)
        convenience = self._calculate_convenience_dummy(data)
        asset_value = self._calculate_asset_value(data)
        living = self._calculate_living_dummy(data)

        # 総合スコア（5つの平均）
        total = int((safety + education + convenience + asset_value + living) / 5)

        logger.info(f"Scores calculated - Total: {total}, Safety: {safety}, "
                   f"Education: {education}, Convenience: {convenience}, "
                   f"Asset: {asset_value}, Living: {living}")

        return ScoreResult(
            area_id=area.area_id,
            safety_score=safety,
            education_score=education,
            convenience_score=convenience,
            asset_value_score=asset_value,
            living_score=living,
            total_score=total,
            calculated_at=datetime.now()
        )

    def _calculate_education_dummy(self, data: Dict[str, Any]) -> int:
        """教育スコア（Phase 1はダミー）"""
        # Phase 2で学校・保育園データから計算
        return 80

    def _calculate_convenience_dummy(self, data: Dict[str, Any]) -> int:
        """利便性スコア（Phase 1はダミー）"""
        # Phase 2で駅・店舗データから計算
        return 85

    def _calculate_asset_value(self, data: Dict[str, Any]) -> int:
        """資産価値スコア（地価データベース版）"""
        # asset_value_scorerを使用
        if hasattr(self, 'asset_value_scorer'):
            return self.asset_value_scorer.calculate(data)
        else:
            # フォールバック
            return 75

    def _calculate_living_dummy(self, data: Dict[str, Any]) -> int:
        """住環境スコア（Phase 1はダミー）"""
        # Phase 2で公園・医療施設データから計算
        return 88

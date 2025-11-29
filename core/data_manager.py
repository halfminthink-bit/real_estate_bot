from pathlib import Path
import pandas as pd
from typing import List, Optional, Dict, Any
from datetime import datetime
from core.models import Area, DataPoint, ScoreResult
import logging

logger = logging.getLogger(__name__)

class CSVDataManager:
    """CSV形式でデータ管理（Phase 1用）"""

    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        self.areas_path = data_dir / 'areas.csv'
        self.crime_path = data_dir / 'crime_data.csv'
        self.population_path = data_dir / 'population_data.csv'
        self.facility_path = data_dir / 'facility_data.csv'
        self.scores_path = data_dir / 'scores.csv'

        # スコアCSVが存在しない場合は作成
        if not self.scores_path.exists():
            self._initialize_scores_csv()

    def _initialize_scores_csv(self):
        """スコアCSVファイルを初期化"""
        df = pd.DataFrame(columns=[
            'area_id', 'safety_score', 'education_score', 'convenience_score',
            'asset_value_score', 'living_score', 'total_score', 'calculated_at'
        ])
        df.to_csv(self.scores_path, index=False)
        logger.info(f"Initialized scores CSV at {self.scores_path}")

    def get_pending_areas(self, limit: int = 10) -> List[Area]:
        """未処理の町丁目を取得"""
        if not self.areas_path.exists():
            logger.warning(f"Areas CSV not found at {self.areas_path}")
            return []

        df = pd.read_csv(self.areas_path)
        pending = df[df['status'] == 'pending'].head(limit)

        areas = []
        for _, row in pending.iterrows():
            areas.append(Area(
                area_id=int(row['area_id']),
                ward=row['ward'],
                choume=row['choume'],
                priority=row['priority'],
                status=row['status']
            ))

        return areas

    def get_area_by_id(self, area_id: int) -> Optional[Area]:
        """IDで町丁目を取得"""
        if not self.areas_path.exists():
            return None

        df = pd.read_csv(self.areas_path)
        row = df[df['area_id'] == area_id]

        if row.empty:
            return None

        row = row.iloc[0]
        return Area(
            area_id=int(row['area_id']),
            ward=row['ward'],
            choume=row['choume'],
            priority=row['priority'],
            status=row['status']
        )

    def update_area_status(self, area_id: int, status: str):
        """町丁目のステータスを更新"""
        if not self.areas_path.exists():
            logger.error(f"Areas CSV not found at {self.areas_path}")
            return

        df = pd.read_csv(self.areas_path)
        df.loc[df['area_id'] == area_id, 'status'] = status
        df.to_csv(self.areas_path, index=False)
        logger.info(f"Updated area {area_id} status to {status}")

    def get_crime_data(self, area_id: int) -> Optional[Dict[str, Any]]:
        """犯罪データを取得"""
        if not self.crime_path.exists():
            logger.warning(f"Crime data CSV not found at {self.crime_path}")
            return None

        df = pd.read_csv(self.crime_path)
        data = df[df['area_id'] == area_id]

        if data.empty:
            return None

        row = data.iloc[0]
        return {
            'crime_count': int(row['crime_count']),
            'year': int(row['year']),
            'month': int(row['month']),
            'crime_type': row['crime_type'],
            'source': row['data_source']
        }

    def save_score(self, score: ScoreResult):
        """スコアを保存"""
        df = pd.read_csv(self.scores_path)

        # 既存のスコアを削除
        df = df[df['area_id'] != score.area_id]

        # 新しいスコアを追加
        new_row = pd.DataFrame([{
            'area_id': score.area_id,
            'safety_score': score.safety_score,
            'education_score': score.education_score,
            'convenience_score': score.convenience_score,
            'asset_value_score': score.asset_value_score,
            'living_score': score.living_score,
            'total_score': score.total_score,
            'calculated_at': datetime.now().isoformat()
        }])

        df = pd.concat([df, new_row], ignore_index=True)
        df.to_csv(self.scores_path, index=False)
        logger.info(f"Saved score for area {score.area_id}")

    def get_score(self, area_id: int) -> Optional[ScoreResult]:
        """保存されたスコアを取得"""
        if not self.scores_path.exists():
            return None

        df = pd.read_csv(self.scores_path)
        data = df[df['area_id'] == area_id]

        if data.empty:
            return None

        row = data.iloc[0]
        return ScoreResult(
            area_id=int(row['area_id']),
            safety_score=int(row['safety_score']),
            education_score=int(row['education_score']),
            convenience_score=int(row['convenience_score']),
            asset_value_score=int(row['asset_value_score']),
            living_score=int(row['living_score']),
            total_score=int(row['total_score'])
        )

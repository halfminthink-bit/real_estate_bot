from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any

@dataclass
class Area:
    """町丁目データモデル"""
    area_id: int
    ward: str
    choume: str
    priority: str  # high/medium/low
    status: str = "pending"  # pending/processing/completed
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

@dataclass
class DataPoint:
    """収集データポイント"""
    area_id: int
    data_type: str  # crime/population/facility
    value: Any
    source: str
    collected_at: datetime

@dataclass
class ScoreResult:
    """スコア計算結果"""
    area_id: int
    safety_score: int
    education_score: int
    convenience_score: int
    asset_value_score: int
    living_score: int
    total_score: int
    calculated_at: Optional[datetime] = None

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            'area_id': self.area_id,
            'safety_score': self.safety_score,
            'education_score': self.education_score,
            'convenience_score': self.convenience_score,
            'asset_value_score': self.asset_value_score,
            'living_score': self.living_score,
            'total_score': self.total_score,
            'calculated_at': self.calculated_at.isoformat() if self.calculated_at else None
        }

@dataclass
class Article:
    """記事データモデル"""
    article_id: int
    area_id: int
    title: str
    markdown_path: str
    html_path: str
    chart_path: str
    status: str = "draft"  # draft/published
    generated_at: Optional[datetime] = None

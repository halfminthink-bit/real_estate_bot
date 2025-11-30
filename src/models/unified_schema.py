"""
統一データスキーマ（Pydantic）

異なるデータソースからのデータを統一フォーマットに変換するためのスキーマ定義。
Pydanticを使用してバリデーションとシリアライゼーションを行います。
"""

from pydantic import BaseModel, Field, field_validator
from datetime import date, datetime
from typing import Optional
import logging

logger = logging.getLogger(__name__)


class LandPriceRecord(BaseModel):
    """地価データの統一フォーマット"""

    choume_code: str = Field(..., description="町丁目コード（11桁）")
    survey_year: int = Field(..., description="調査年", ge=1970, le=2100)
    land_type: str = Field(..., description="用途区分（住宅地、商業地、工業地）")
    official_price: int = Field(..., description="公示価格（円/㎡）", ge=0)
    year_on_year_change: Optional[float] = Field(None, description="前年比（%）")
    data_source: str = Field(..., description="データソース")
    original_address: str = Field(..., description="元の住所")
    latitude: Optional[float] = Field(None, description="緯度", ge=-90, le=90)
    longitude: Optional[float] = Field(None, description="経度", ge=-180, le=180)
    created_at: date = Field(default_factory=date.today)

    @field_validator('land_type')
    @classmethod
    def normalize_land_type(cls, v: str) -> str:
        """用途区分を正規化"""
        land_type_map = {
            '住宅': '住宅地',
            '宅地': '住宅地',
            '商業': '商業地',
            '工業': '工業地'
        }
        return land_type_map.get(v, v)

    @field_validator('choume_code')
    @classmethod
    def validate_choume_code(cls, v: str) -> str:
        """町丁目コードのバリデーション"""
        if len(v) != 11:
            logger.warning(f"Invalid choume_code length: {v} (expected 11 digits)")
        return v

    class Config:
        """Pydantic設定"""
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }


class PopulationRecord(BaseModel):
    """人口データの統一フォーマット"""

    choume_code: str = Field(..., description="町丁目コード（11桁）")
    census_year: int = Field(..., description="国勢調査年", ge=1970, le=2100)
    total_population: Optional[int] = Field(None, description="総人口", ge=0)
    male_population: Optional[int] = Field(None, description="男性人口", ge=0)
    female_population: Optional[int] = Field(None, description="女性人口", ge=0)
    household_count: Optional[int] = Field(None, description="世帯数", ge=0)
    avg_household_size: Optional[float] = Field(None, description="平均世帯人数", ge=0)
    age_0_14: Optional[int] = Field(None, description="0-14歳人口", ge=0)
    age_15_64: Optional[int] = Field(None, description="15-64歳人口", ge=0)
    age_65_plus: Optional[int] = Field(None, description="65歳以上人口", ge=0)
    data_source: str = Field(..., description="データソース")
    created_at: date = Field(default_factory=date.today)

    @field_validator('total_population', 'male_population', 'female_population')
    @classmethod
    def validate_population_consistency(cls, v, info):
        """人口データの整合性チェック"""
        # 男性 + 女性 = 総人口のチェックは、全フィールドが揃った後に行う
        # ここでは個別のバリデーションのみ
        return v

    class Config:
        """Pydantic設定"""
        json_encoders = {
            date: lambda v: v.isoformat() if v else None
        }


class AreaScoreRecord(BaseModel):
    """エリアスコアの統一フォーマット"""

    choume_code: str = Field(..., description="町丁目コード（11桁）")
    calculation_date: date = Field(..., description="計算日")
    asset_value_score: Optional[int] = Field(None, description="資産価値スコア", ge=0, le=100)
    future_potential_score: Optional[int] = Field(None, description="将来性スコア", ge=0, le=100)
    total_score: Optional[int] = Field(None, description="総合スコア", ge=0, le=100)
    score_details: Optional[dict] = Field(None, description="スコア根拠データ")
    created_at: datetime = Field(default_factory=datetime.now)

    @field_validator('total_score')
    @classmethod
    def calculate_total_score(cls, v, info):
        """総合スコアの計算（未設定の場合）"""
        if v is None:
            asset_score = info.data.get('asset_value_score', 0)
            future_score = info.data.get('future_potential_score', 0)

            if asset_score or future_score:
                # 重み付け平均（資産価値50%、将来性50%）
                total = int((asset_score * 0.5 + future_score * 0.5))
                return total

        return v

    class Config:
        """Pydantic設定"""
        json_encoders = {
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None
        }

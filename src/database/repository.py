"""
データアクセス層（Repository パターン）

データベースへのCRUD操作を抽象化し、ビジネスロジックから分離します。
"""

import psycopg2
from typing import List, Optional, Dict, Any
import logging

from src.models.unified_schema import LandPriceRecord, PopulationRecord, AreaScoreRecord

logger = logging.getLogger(__name__)


class LandPriceRepository:
    """地価データのRepository"""

    def __init__(self, conn):
        """
        Args:
            conn: psycopg2 connection
        """
        self.conn = conn

    def bulk_insert(self, records: List[LandPriceRecord]) -> int:
        """
        地価データを一括挿入（upsert）

        Args:
            records: 挿入するレコードリスト

        Returns:
            挿入・更新件数
        """
        if not records:
            logger.warning("No records to insert")
            return 0

        cursor = self.conn.cursor()
        insert_count = 0

        try:
            for record in records:
                cursor.execute("""
                    INSERT INTO land_prices
                    (choume_code, survey_year, land_type, official_price,
                     year_on_year_change, data_source, original_address,
                     latitude, longitude, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (choume_code, survey_year, land_type, data_source)
                    DO UPDATE SET
                        official_price = EXCLUDED.official_price,
                        year_on_year_change = EXCLUDED.year_on_year_change,
                        latitude = EXCLUDED.latitude,
                        longitude = EXCLUDED.longitude,
                        original_address = EXCLUDED.original_address
                """, (
                    record.choume_code,
                    record.survey_year,
                    record.land_type,
                    record.official_price,
                    record.year_on_year_change,
                    record.data_source,
                    record.original_address,
                    record.latitude,
                    record.longitude,
                    record.created_at
                ))

                insert_count += cursor.rowcount

            self.conn.commit()
            logger.info(f"✅ Bulk insert completed: {insert_count} records")

        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"❌ Bulk insert failed: {e}", exc_info=True)
            raise

        finally:
            cursor.close()

        return insert_count

    def get_by_choume_and_year(
        self,
        choume_code: str,
        survey_year: int,
        land_type: str = None
    ) -> List[Dict[str, Any]]:
        """
        町丁目コードと年度で地価データを取得

        Args:
            choume_code: 町丁目コード
            survey_year: 調査年
            land_type: 用途区分（オプション）

        Returns:
            検索結果（辞書のリスト）
        """
        cursor = self.conn.cursor()

        try:
            if land_type:
                cursor.execute("""
                    SELECT * FROM land_prices
                    WHERE choume_code = %s AND survey_year = %s AND land_type = %s
                    ORDER BY data_source
                """, (choume_code, survey_year, land_type))
            else:
                cursor.execute("""
                    SELECT * FROM land_prices
                    WHERE choume_code = %s AND survey_year = %s
                    ORDER BY land_type, data_source
                """, (choume_code, survey_year))

            columns = [desc[0] for desc in cursor.description]
            results = []

            for row in cursor.fetchall():
                results.append(dict(zip(columns, row)))

            return results

        finally:
            cursor.close()

    def get_latest_by_choume(self, choume_code: str) -> Optional[Dict[str, Any]]:
        """
        最新の地価データを取得

        Args:
            choume_code: 町丁目コード

        Returns:
            最新レコード
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM land_prices
                WHERE choume_code = %s
                ORDER BY survey_year DESC, created_at DESC
                LIMIT 1
            """, (choume_code,))

            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            return None

        finally:
            cursor.close()


class PopulationRepository:
    """人口データのRepository"""

    def __init__(self, conn):
        self.conn = conn

    def bulk_insert(self, records: List[PopulationRecord]) -> int:
        """
        人口データを一括挿入（upsert）

        Args:
            records: 挿入するレコードリスト

        Returns:
            挿入・更新件数
        """
        if not records:
            return 0

        cursor = self.conn.cursor()
        insert_count = 0

        try:
            for record in records:
                cursor.execute("""
                    INSERT INTO population
                    (choume_code, census_year, total_population, male_population,
                     female_population, household_count, avg_household_size,
                     age_0_14, age_15_64, age_65_plus, data_source, created_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (choume_code, census_year)
                    DO UPDATE SET
                        total_population = EXCLUDED.total_population,
                        male_population = EXCLUDED.male_population,
                        female_population = EXCLUDED.female_population,
                        household_count = EXCLUDED.household_count,
                        avg_household_size = EXCLUDED.avg_household_size,
                        age_0_14 = EXCLUDED.age_0_14,
                        age_15_64 = EXCLUDED.age_15_64,
                        age_65_plus = EXCLUDED.age_65_plus
                """, (
                    record.choume_code,
                    record.census_year,
                    record.total_population,
                    record.male_population,
                    record.female_population,
                    record.household_count,
                    record.avg_household_size,
                    record.age_0_14,
                    record.age_15_64,
                    record.age_65_plus,
                    record.data_source,
                    record.created_at
                ))

                insert_count += cursor.rowcount

            self.conn.commit()
            logger.info(f"✅ Bulk insert completed: {insert_count} population records")

        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"❌ Bulk insert failed: {e}", exc_info=True)
            raise

        finally:
            cursor.close()

        return insert_count


class AreaScoreRepository:
    """エリアスコアのRepository"""

    def __init__(self, conn):
        self.conn = conn

    def save(self, record: AreaScoreRecord) -> int:
        """
        スコアを保存（upsert）

        Args:
            record: スコアレコード

        Returns:
            影響を受けた行数
        """
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                INSERT INTO area_scores
                (choume_code, calculation_date, asset_value_score,
                 future_potential_score, total_score, score_details, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (choume_code, calculation_date)
                DO UPDATE SET
                    asset_value_score = EXCLUDED.asset_value_score,
                    future_potential_score = EXCLUDED.future_potential_score,
                    total_score = EXCLUDED.total_score,
                    score_details = EXCLUDED.score_details
            """, (
                record.choume_code,
                record.calculation_date,
                record.asset_value_score,
                record.future_potential_score,
                record.total_score,
                record.score_details,
                record.created_at
            ))

            self.conn.commit()
            row_count = cursor.rowcount

            logger.info(f"✅ Saved score for {record.choume_code}")

            return row_count

        except psycopg2.Error as e:
            self.conn.rollback()
            logger.error(f"❌ Save failed: {e}", exc_info=True)
            raise

        finally:
            cursor.close()

    def get_latest_by_choume(self, choume_code: str) -> Optional[Dict[str, Any]]:
        """最新スコアを取得"""
        cursor = self.conn.cursor()

        try:
            cursor.execute("""
                SELECT * FROM area_scores
                WHERE choume_code = %s
                ORDER BY calculation_date DESC
                LIMIT 1
            """, (choume_code,))

            row = cursor.fetchone()

            if row:
                columns = [desc[0] for desc in cursor.description]
                return dict(zip(columns, row))

            return None

        finally:
            cursor.close()

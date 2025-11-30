-- ============================================
-- Migration: 002_add_kokudo_fields.sql
-- 国土数値情報の追加フィールド
-- ============================================

-- land_prices テーブルに新しいカラムを追加
ALTER TABLE land_prices
ADD COLUMN IF NOT EXISTS land_use VARCHAR(50),              -- 用途地域
ADD COLUMN IF NOT EXISTS building_coverage_ratio INTEGER,   -- 建蔽率(%)
ADD COLUMN IF NOT EXISTS floor_area_ratio INTEGER,          -- 容積率(%)
ADD COLUMN IF NOT EXISTS road_direction VARCHAR(10),        -- 前面道路方位
ADD COLUMN IF NOT EXISTS road_width DECIMAL(5,1),           -- 前面道路幅員(m)
ADD COLUMN IF NOT EXISTS land_area INTEGER,                 -- 地積(㎡)
ADD COLUMN IF NOT EXISTS nearest_station VARCHAR(100),      -- 最寄駅名
ADD COLUMN IF NOT EXISTS station_distance INTEGER;          -- 駅距離(m)

-- インデックス追加
CREATE INDEX IF NOT EXISTS idx_land_prices_land_use ON land_prices(land_use);
CREATE INDEX IF NOT EXISTS idx_land_prices_survey_year ON land_prices(survey_year);

-- コメント追加
COMMENT ON COLUMN land_prices.land_use IS '用途地域（1低専、近商、商業など）';
COMMENT ON COLUMN land_prices.building_coverage_ratio IS '建蔽率(%)';
COMMENT ON COLUMN land_prices.floor_area_ratio IS '容積率(%)';
COMMENT ON COLUMN land_prices.road_direction IS '前面道路方位（南、南東など）';
COMMENT ON COLUMN land_prices.road_width IS '前面道路幅員(m)';
COMMENT ON COLUMN land_prices.land_area IS '地積(㎡)';
COMMENT ON COLUMN land_prices.nearest_station IS '最寄駅名';
COMMENT ON COLUMN land_prices.station_distance IS '駅距離(m)';


-- ============================================
-- RealEstateBot Database Schema
-- Version: 1.0
-- Target: PostgreSQL 14+
-- ============================================

-- ============================================
-- マスタテーブル
-- ============================================

-- 都道府県マスタ
CREATE TABLE IF NOT EXISTS prefectures (
    prefecture_code VARCHAR(2) PRIMARY KEY,
    prefecture_name VARCHAR(50) NOT NULL,
    prefecture_name_en VARCHAR(50),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE prefectures IS '都道府県マスタ';
COMMENT ON COLUMN prefectures.prefecture_code IS '都道府県コード（JIS X 0401）';

-- 市区町村マスタ
CREATE TABLE IF NOT EXISTS cities (
    city_code VARCHAR(5) PRIMARY KEY,
    prefecture_code VARCHAR(2) NOT NULL REFERENCES prefectures(prefecture_code),
    city_name VARCHAR(100) NOT NULL,
    city_name_kana VARCHAR(100),
    city_type VARCHAR(20),  -- '区', '市', '町', '村'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE cities IS '市区町村マスタ';
COMMENT ON COLUMN cities.city_code IS '市区町村コード（JIS X 0402）';

CREATE INDEX idx_cities_prefecture ON cities(prefecture_code);

-- 町丁目マスタ
CREATE TABLE IF NOT EXISTS choume (
    choume_code VARCHAR(11) PRIMARY KEY,
    city_code VARCHAR(5) NOT NULL REFERENCES cities(city_code),
    choume_name VARCHAR(200) NOT NULL,
    choume_name_kana VARCHAR(200),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(11, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

COMMENT ON TABLE choume IS '町丁目マスタ';
COMMENT ON COLUMN choume.choume_code IS '町丁目コード（11桁）';

CREATE INDEX idx_choume_city ON choume(city_code);
CREATE INDEX idx_choume_name ON choume(choume_name);

-- ============================================
-- 時系列データテーブル
-- ============================================

-- 地価公示データ（年次）
CREATE TABLE IF NOT EXISTS land_prices (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    survey_year INT NOT NULL,
    land_type VARCHAR(20),  -- '住宅地', '商業地', '工業地'
    official_price INT NOT NULL,  -- 円/㎡
    year_on_year_change DECIMAL(5, 2),  -- 前年比（%）
    data_source VARCHAR(50) NOT NULL,  -- 'kokudo_suuchi', 'tokyo_opendata'
    original_address TEXT,  -- デバッグ用
    latitude DECIMAL(10, 7),
    longitude DECIMAL(11, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_land_price UNIQUE (choume_code, survey_year, land_type, data_source)
);

COMMENT ON TABLE land_prices IS '地価公示データ（年次）';
COMMENT ON COLUMN land_prices.official_price IS '公示価格（円/㎡）';

CREATE INDEX idx_land_prices_year ON land_prices(survey_year);
CREATE INDEX idx_land_prices_choume_year ON land_prices(choume_code, survey_year);

-- 人口データ（5年ごと）
CREATE TABLE IF NOT EXISTS population (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    census_year INT NOT NULL,  -- 2015, 2020, 2025...
    total_population INT,
    male_population INT,
    female_population INT,
    household_count INT,
    avg_household_size DECIMAL(3, 2),
    age_0_14 INT,
    age_15_64 INT,
    age_65_plus INT,
    data_source VARCHAR(50) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_population UNIQUE (choume_code, census_year)
);

COMMENT ON TABLE population IS '人口データ（国勢調査、5年ごと）';

CREATE INDEX idx_population_year ON population(census_year);
CREATE INDEX idx_population_choume_year ON population(choume_code, census_year);

-- ============================================
-- 集計・分析テーブル
-- ============================================

-- 地価推移サマリー（町丁目ごと）
CREATE TABLE IF NOT EXISTS land_price_summary (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    latest_year INT,
    latest_price INT,
    price_5year_ago INT,
    price_10year_ago INT,
    change_5year_pct DECIMAL(5, 2),  -- 過去5年の変化率
    change_10year_pct DECIMAL(5, 2),  -- 過去10年の変化率
    trend VARCHAR(20),  -- '上昇', '横ばい', '下降'
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_land_price_summary UNIQUE (choume_code)
);

COMMENT ON TABLE land_price_summary IS '地価推移サマリー（分析用）';

-- 人口推移サマリー（町丁目ごと）
CREATE TABLE IF NOT EXISTS population_summary (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    latest_year INT,
    latest_population INT,
    population_20year_ago INT,
    change_20year_pct DECIMAL(5, 2),
    trend VARCHAR(20),  -- '増加', '横ばい', '減少'
    calculated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_population_summary UNIQUE (choume_code)
);

COMMENT ON TABLE population_summary IS '人口推移サマリー（分析用）';

-- スコア計算結果
CREATE TABLE IF NOT EXISTS area_scores (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    calculation_date DATE NOT NULL,

    -- 各スコア（100点満点）
    asset_value_score INT,  -- 資産価値スコア
    future_potential_score INT,  -- 将来性スコア
    total_score INT,  -- 総合スコア

    -- スコア根拠データ（JSON）
    score_details JSONB,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_area_score UNIQUE (choume_code, calculation_date)
);

COMMENT ON TABLE area_scores IS 'エリアスコア計算結果';
COMMENT ON COLUMN area_scores.score_details IS 'スコア根拠データ（JSON形式）';

CREATE INDEX idx_scores_date ON area_scores(calculation_date);
CREATE INDEX idx_scores_choume ON area_scores(choume_code);

-- グラフデータ（Chart.js用）
CREATE TABLE IF NOT EXISTS graph_data (
    id SERIAL PRIMARY KEY,
    choume_code VARCHAR(11) NOT NULL REFERENCES choume(choume_code),
    graph_type VARCHAR(50) NOT NULL,  -- 'land_price_trend', 'population_trend'
    graph_data JSONB NOT NULL,  -- Chart.js用のJSON
    generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_graph_data UNIQUE (choume_code, graph_type)
);

COMMENT ON TABLE graph_data IS 'グラフデータ（Chart.js形式）';

CREATE INDEX idx_graph_type ON graph_data(graph_type);

-- ============================================
-- トリガー（updated_at自動更新）
-- ============================================

CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_prefectures_updated_at
    BEFORE UPDATE ON prefectures
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_cities_updated_at
    BEFORE UPDATE ON cities
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

CREATE TRIGGER update_choume_updated_at
    BEFORE UPDATE ON choume
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

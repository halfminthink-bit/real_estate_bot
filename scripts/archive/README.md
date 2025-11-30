# アーカイブ - 旧バージョン・完了済みスクリプト

このディレクトリには、現在使用していない旧バージョンや一度実行済みのスクリプトが格納されています。

## 構成

- `old_versions/` - 旧バージョンのインポートスクリプト
- `completed/` - 一度実行済み・完了したスクリプト
- `tests/` - テスト用スクリプト

## 注意

これらのスクリプトは参考用です。実行する場合は最新のスキーマ・データ構造に対応していない可能性があります。

## 詳細

### old_versions/

旧バージョンのインポートスクリプト：
- `import_kokudo_test_3years.py` - テスト用（3年分のみ）
- `import_kokudo_multi_year.py` - 旧バージョン
- `import_kokudo_multi_year_fixed.py` - 旧バージョン
- `12_import_kokudo_data.py` - 旧バージョン
- `20_import_historical_kokudo_data.py` - 旧バージョン
- `05_import_tokyo_data.py` - 東京都データ（地価公示に統一）

**現在のメインスクリプト**: `scripts/import_kokudo_all_years.py`（26年分データインポート）

### completed/

一度実行済み・完了したスクリプト：
- `13_verify_kokudo_data.py` - 検証完了
- `14_apply_schema_migration.py` - マイグレーション完了
- `15_check_address_format.py` - 検証完了
- `21_import_choume_master.py` - マスタデータ投入完了
- `add_unknown_choume.py` - データ修正完了
- `fix_unique_constraint.py` - 制約修正完了
- `insert_master_data.py` - マスタデータ投入完了
- `11_create_areas_csv.py` - areas.csv作成完了
- `analyze_kokudo_shapefiles.py` - 分析完了
- `find_asset_value_data.py` - 分析完了
- `investigate_asset_value_data.py` - 分析完了
- `README_20_import.md` - 旧ドキュメント

### tests/

テスト用スクリプト：
- `16_test_extended_collector.py` - テスト完了


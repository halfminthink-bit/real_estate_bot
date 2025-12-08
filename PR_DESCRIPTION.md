# アフィリエイト設定ファイル対応と再投稿機能の実装

## 📋 概要

ASP承認待ちのダミーリンクで投稿した記事を、承認後に本番リンクに差し替えるための機能を実装しました。また、不動産APIのエラーハンドリングを改善し、世田谷区の記事生成が本番運用可能な状態になりました。

## ✨ 主な変更内容

### 1. アフィリエイト設定ファイル対応

- `affiliate_config.yml` の構造を更新（`affiliates.primary/secondary` 形式）
- `HTMLBuilder` のアフィリエイトセクションを新しいデザインに更新
  - カードデザイン、赤いバナー、ハイライト付きタイトル
  - 設定ファイルから動的にリンクとテキストを読み込み

### 2. 再投稿機能の実装

- `WordPressPublisher` に `update_post()` メソッドを追加
- `ArticleManager` に `get_published_articles()` メソッドを追加
- `modules/wordpress_publisher/republisher.py` を新規作成
  - 既存投稿を再HTML化してWordPressを更新
  - MarkdownからHTMLを再生成し、アフィリエイトリンクを更新
- `scripts/republish_articles.py` を追加（ラッパースクリプト）

### 3. 不動産APIの改善

- リトライ処理を追加（最大3回、指数バックオフ）
- タイムアウトを30秒 → 60秒に延長
- API呼び出し間の待機時間を0.5秒 → 5秒に延長
- エラーハンドリングとログ出力を改善

### 4. プロンプトの改善

- `<TRANSACTION_DATA>` マーカーの配置指示を強化
- `has_transaction_data` が `True` の場合に必ずマーカーを配置するよう明記

### 5. ドキュメントの更新

- `docs/commands.md` に以下を追加：
  - アフィリエイトリンク更新（再投稿）の手順
  - 全投稿のリセットと再投稿の手順
  - アフィリエイト設定ファイルの構造説明

## 🚀 使用方法

### ASP承認後のリンク差し替え

1. `affiliate_config.yml` を更新（本番リンクに変更）
2. 再投稿スクリプトを実行：
   ```bash
   python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml
   ```

### 全投稿のリセットと再投稿

```bash
# 1. 全記事のWordPress投稿情報をリセット
python scripts/post_to_wordpress.py --reset-all

# 2. 全記事を再投稿
python scripts/post_to_wordpress.py
```

## 📁 変更ファイル

### 新規ファイル
- `modules/wordpress_publisher/republisher.py`
- `scripts/republish_articles.py`

### 修正ファイル
- `modules/article_manager/manager.py`
- `modules/html_builder/builder.py`
- `modules/wordpress_publisher/publisher.py`
- `modules/wordpress_publisher/__init__.py`
- `modules/data_aggregator/collectors/transaction_price_collector.py`
- `projects/setagaya_real_estate/affiliate_config.yml`
- `projects/setagaya_real_estate/prompts/content.txt`
- `docs/commands.md`

## ✅ テスト結果

- 記事生成が正常に動作することを確認
- アフィリエイトセクションが新しいデザインで表示されることを確認
- 不動産APIのリトライ処理が正常に動作することを確認（ログで確認済み）

## 🎯 本番運用について

**世田谷区に関しては本番運用可能な状態です。**

- 記事生成パイプラインが安定して動作
- アフィリエイトリンクの差し替えが可能
- エラーハンドリングが改善され、一時的なAPIエラーでも自動リトライ
- ドキュメントが整備され、運用方法が明確

## 📝 今後の改善案

- [ ] 取引データが取得できない場合のフォールバック処理の強化
- [ ] バッチ処理でのAPI呼び出し最適化
- [ ] エラーログの集計と監視機能




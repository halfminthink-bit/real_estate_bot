#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress投稿状況を確認するスクリプト
"""
import argparse
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import ProjectConfig
from modules.article_manager import ArticleManager

def main():
    parser = argparse.ArgumentParser(description='WordPress投稿状況を確認')
    parser.add_argument('--project', required=True, help='プロジェクト設定ファイル')
    args = parser.parse_args()
    
    # 設定読み込み
    config = ProjectConfig(args.project)
    
    # ArticleManager初期化
    db_path = config.project_dir / 'articles.db'
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        return 1
    
    article_manager = ArticleManager(str(db_path))
    
    # 投稿済み記事を取得
    articles = article_manager.get_published_articles()
    
    if not articles:
        print("投稿済み記事がありません")
        return 0
    
    print("=" * 80)
    print(f"投稿済み記事: {len(articles)}件")
    print("=" * 80)
    
    for i, article in enumerate(articles, 1):
        print(f"\n[{i}] {article['ward']}{article['choume']}")
        print(f"  タイトル: {article['title']}")
        print(f"  WP Post ID: {article.get('wp_post_id', 'N/A')}")
        print(f"  WP URL: {article.get('wp_url', 'N/A')}")
        print(f"  WP Status: {article.get('wp_status', 'N/A')}")
        print(f"  HTML Path: {article.get('html_path', 'N/A')}")
    
    print("\n" + "=" * 80)
    
    # ステータス別の集計
    stats = article_manager.get_statistics()
    print("\n統計情報:")
    print(f"  総記事数: {stats['total']}")
    print(f"  公開済み: {stats['published']}")
    print(f"  下書き: {stats['draft']}")
    print(f"  未投稿: {stats['unpublished']}")
    
    # ステータス別の詳細
    print("\nステータス別の記事:")
    for status in ['published', 'future', 'draft']:
        articles_by_status = article_manager.get_by_status(status)
        if articles_by_status:
            print(f"\n  {status}: {len(articles_by_status)}件")
            for article in articles_by_status[:5]:  # 最初の5件だけ表示
                print(f"    - {article['choume']} (ID: {article.get('wp_post_id', 'N/A')}, URL: {article.get('wp_url', 'N/A')})")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())


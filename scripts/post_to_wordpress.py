#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress自動投稿スクリプト

使い方:
    # 1件テスト
    python scripts/post_to_wordpress.py --limit 1
    
    # 全件投稿
    python scripts/post_to_wordpress.py
    
    # 再投稿モード
    python scripts/post_to_wordpress.py --republish --limit 5
    
    # 全記事リセット
    python scripts/post_to_wordpress.py --reset-all
"""

import sys
import argparse
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.article_manager import ArticleManager
from modules.wordpress_publisher import WordPressPublisher


def main():
    parser = argparse.ArgumentParser(description='WordPress自動投稿')
    parser.add_argument('--limit', type=int, default=None, help='投稿件数制限')
    parser.add_argument('--republish', action='store_true', 
                       help='再投稿モード: 投稿済み記事も含めて再投稿')
    parser.add_argument('--reset-all', action='store_true',
                       help='全記事のWordPress投稿情報をリセット（再投稿準備）')
    parser.add_argument('--project', type=str, 
                       default='projects/setagaya_real_estate',
                       help='プロジェクトディレクトリ')
    
    args = parser.parse_args()
    
    # プロジェクトパス
    project_dir = project_root / args.project
    db_path = project_dir / 'articles.db'
    
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        print(f"   まず記事を生成してください: python main_orchestrator.py ...")
        return 1
    
    # ArticleManager初期化
    article_manager = ArticleManager(str(db_path))
    
    # 全記事リセットモード
    if args.reset_all:
        stats = article_manager.get_statistics()
        total_published = stats['published'] + stats['draft']
        
        if total_published == 0:
            print("\nリセットする記事がありません。")
            return 0
        
        print("\n" + "=" * 70)
        print("WordPress投稿情報リセット")
        print("=" * 70)
        print(f"投稿済み記事: {total_published}件")
        print("=" * 70)
        
        response = input(f"\n{total_published}件の記事のWordPress情報をリセットしますか？ (y/N): ")
        if response.lower() != 'y':
            print("キャンセルしました。")
            return 0
        
        reset_count = article_manager.reset_all_wp_posts()
        print(f"\n✅ {reset_count}件の記事をリセットしました。")
        print("   これで再投稿できるようになりました。")
        return 0
    
    # 統計表示
    stats = article_manager.get_statistics()
    print("\n" + "=" * 70)
    print("ArticleManager統計")
    print("=" * 70)
    print(f"総記事数:         {stats['total']}件")
    print(f"WordPress公開済み: {stats['published']}件")
    print(f"WordPress下書き:   {stats['draft']}件")
    print(f"未投稿:           {stats['unpublished']}件")
    print("=" * 70)
    
    # 再投稿モードの確認
    if args.republish:
        total_articles = stats['total']
        if total_articles == 0:
            print("\n投稿する記事がありません。")
            return 1
        
        limit_text = f"{args.limit}件" if args.limit else f"{total_articles}件（全件）"
        print(f"\n⚠️  再投稿モード: 投稿済み記事も含めて{limit_text}を再投稿します。")
        response = input(f"続行しますか？ (y/N): ")
        if response.lower() != 'y':
            print("キャンセルしました。")
            return 0
    else:
        # 通常モード
        if stats['unpublished'] == 0:
            print("\n投稿する記事がありません。")
            print("再投稿する場合は --republish オプションを使用してください。")
            return 0
        
        limit_text = f"{args.limit}件" if args.limit else f"{stats['unpublished']}件（全件）"
        response = input(f"\n{limit_text}の記事をWordPressに投稿しますか？ (y/N): ")
        if response.lower() != 'y':
            print("キャンセルしました。")
            return 0
    
    # WordPressPublisher初期化
    try:
        publisher = WordPressPublisher(
            article_manager=article_manager,
            project_dir=project_dir
        )
    except ValueError as e:
        print(f"❌ 設定エラー: {e}")
        print("   .envファイルにWordPress設定を追加してください。")
        return 1
    
    # 投稿実行
    result = publisher.publish_all(
        limit=args.limit,
        republish=args.republish
    )
    
    # 最終統計
    print("\n" + "=" * 70)
    print("最終統計")
    print("=" * 70)
    stats = article_manager.get_statistics()
    print(f"総記事数:         {stats['total']}件")
    print(f"WordPress公開済み: {stats['published']}件")
    print(f"WordPress下書き:   {stats['draft']}件")
    print(f"未投稿:           {stats['unpublished']}件")
    print("=" * 70)
    
    # 結果表示
    print(f"\n✅ 完了: 成功={result['success']}件, 失敗={result['failed']}件")
    
    return 0 if result['failed'] == 0 else 1


if __name__ == '__main__':
    sys.exit(main())

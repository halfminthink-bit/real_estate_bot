"""記事統計表示スクリプト"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.article_manager import ArticleManager

def main():
    db_path = project_root / "projects" / "setagaya_real_estate" / "articles.db"
    
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        return
    
    manager = ArticleManager(db_path)
    
    # 統計情報
    stats = manager.get_statistics()
    
    print("\n" + "="*60)
    print("📊 記事統計")
    print("="*60)
    print(f"総記事数:         {stats['total']:>3}件")
    print(f"WordPress公開済み: {stats['published']:>3}件")
    print(f"WordPress下書き:   {stats['draft']:>3}件")
    print(f"未投稿:           {stats['unpublished']:>3}件")
    print("="*60)
    
    # 未投稿記事リスト
    if stats['unpublished'] > 0:
        print("\n📝 未投稿記事:")
        unpublished = manager.get_unpublished()
        for i, article in enumerate(unpublished[:10], 1):
            print(f"  {i}. {article['ward']}{article['choume']}")
        if len(unpublished) > 10:
            print(f"  ... 他{len(unpublished) - 10}件")
    
    # 最近の記事
    print("\n📰 最近生成された記事（5件）:")
    recent = manager.get_all_articles()[:5]
    for i, article in enumerate(recent, 1):
        wp_status = article['wp_status'] or '未投稿'
        print(f"  {i}. {article['choume']} - {wp_status} ({article['generated_at'][:10]})")
    
    print()

if __name__ == "__main__":
    main()







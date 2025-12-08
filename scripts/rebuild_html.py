#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存MarkdownファイルからHTMLを再生成するスクリプト

目的:
- Markdownファイルはそのまま
- HTMLファイルのみを再生成
- データベースのhtml_pathを更新
- WordPress投稿は行わない

使い方:
    # 全記事のHTMLを再生成
    python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml
    
    # 指定件数だけ再生成
    python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --limit 10
    
    # 強制再生成（既存HTMLを上書き）
    python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force
"""

import argparse
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from core.config import ProjectConfig
from modules.html_builder.builder import HTMLBuilder
from modules.article_manager import ArticleManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def rebuild_html(project_path: str, limit: int = None, force: bool = False) -> int:
    """
    既存のMarkdownからHTMLを再生成
    
    Args:
        project_path: プロジェクト設定ファイルのパス
        limit: 再生成する記事数（Noneの場合は全件）
        force: Trueの場合、既存HTMLがあっても上書き
    
    Returns:
        int: 0=成功, 1=失敗
    """
    # 設定読み込み
    logger.info(f"Loading project configuration: {project_path}")
    config = ProjectConfig(project_path)
    
    # HTMLBuilder初期化
    html_builder = HTMLBuilder(config)
    
    # ArticleManager初期化
    db_path = config.project_dir / 'articles.db'
    if not db_path.exists():
        logger.error(f"Database not found: {db_path}")
        logger.error("Please generate articles first using main_orchestrator.py")
        return 1
    
    article_manager = ArticleManager(str(db_path))
    
    # 全記事を取得
    articles = article_manager.get_all_articles()
    
    # limit指定がある場合はスライス
    if limit:
        articles = articles[:limit]
    
    if not articles:
        logger.warning("No articles found in database")
        return 0
    
    logger.info("=" * 70)
    logger.info(f"HTML Rebuild Process")
    logger.info("=" * 70)
    logger.info(f"Total articles: {len(articles)}")
    logger.info(f"Force rebuild: {force}")
    logger.info("=" * 70)
    
    success_count = 0
    failed_count = 0
    skipped_count = 0
    
    for i, article in enumerate(articles):
        logger.info(f"\n[{i+1}/{len(articles)}] Processing: {article['ward']}{article['choume']}")
        
        try:
            # Markdownファイルのパスを取得
            markdown_path_str = article['markdown_path'].replace('\\', '/')
            markdown_path = config.project_dir / markdown_path_str
            markdown_path = markdown_path.resolve()
            
            if not markdown_path.exists():
                logger.warning(f"  ⚠️  Markdown file not found: {markdown_path}")
                failed_count += 1
                continue
            
            # HTML出力パス
            html_path_str = article.get('html_path', '').replace('\\', '/')
            if not html_path_str:
                # html_pathが未設定の場合、デフォルトパスを生成
                html_filename = f"{article['ward']}{article['choume']}.html"
                html_path = config.html_dir / html_filename
                html_path_str = f"html/{html_filename}"
            else:
                html_path = config.project_dir / html_path_str
                html_path = html_path.resolve()
            
            # 既存HTMLがある場合、forceフラグを確認
            if html_path.exists() and not force:
                logger.info(f"  ⏭️  HTML already exists, skipping (use --force to overwrite)")
                skipped_count += 1
                continue
            
            # グラフパスを取得
            chart_path = None
            if article.get('chart_path'):
                chart_path_str = article['chart_path'].replace('\\', '/')
                chart_path = config.project_dir / chart_path_str
                chart_path = chart_path.resolve()
                if not chart_path.exists():
                    logger.warning(f"  ⚠️  Chart file not found: {chart_path}")
                    chart_path = None
            
            # HTML生成
            logger.info(f"  → Generating HTML from Markdown...")
            html_builder.build(
                markdown_path=markdown_path,
                chart_path=chart_path,
                output_path=html_path,
                data={}  # Markdownに既にデータが含まれているため不要
            )
            
            logger.info(f"  ✅ HTML generated: {html_path.name}")
            
            # データベースのhtml_pathを直接更新（register_articleは複雑なので使わない）
            try:
                import sqlite3
                with sqlite3.connect(article_manager.db_path, timeout=30.0) as conn:
                    conn.execute(
                        '''
                        UPDATE articles
                        SET html_path = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE ward = ? AND choume = ?
                        ''',
                        (html_path_str, article['ward'], article['choume'])
                    )
                    conn.commit()
                logger.info(f"  ✅ Database updated: html_path={html_path_str}")
            except Exception as e:
                logger.warning(f"  ⚠️  Database update failed: {e}")
                logger.info(f"  ℹ️  HTML file was created successfully, but database was not updated")
            
            success_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {article.get('choume', 'unknown')}: {e}", exc_info=True)
            failed_count += 1
    
    # 結果サマリー
    logger.info("\n" + "=" * 70)
    logger.info("HTML Rebuild Complete")
    logger.info("=" * 70)
    logger.info(f"Success: {success_count}件")
    logger.info(f"Failed: {failed_count}件")
    logger.info(f"Skipped: {skipped_count}件")
    logger.info("=" * 70)
    
    return 0 if failed_count == 0 else 1


def main():
    parser = argparse.ArgumentParser(
        description='既存MarkdownファイルからHTMLを再生成',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # 全記事のHTMLを再生成
  python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml
  
  # 10件だけ再生成
  python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --limit 10
  
  # 既存HTMLを強制上書き
  python scripts/rebuild_html.py --project projects/setagaya_real_estate/config.yml --force
        """
    )
    parser.add_argument(
        '--project',
        required=True,
        help='プロジェクト設定ファイル（例: projects/setagaya_real_estate/config.yml）'
    )
    parser.add_argument(
        '--limit',
        type=int,
        help='再生成する記事数（デフォルト: 全件）'
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help='既存HTMLがあっても強制的に上書き'
    )
    args = parser.parse_args()
    
    return rebuild_html(args.project, args.limit, args.force)


if __name__ == '__main__':
    sys.exit(main())
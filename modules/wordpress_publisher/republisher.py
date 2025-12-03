#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の投稿を更新するモジュール

ASP承認後、affiliate_config.ymlを更新してから実行

使い方:
    from modules.wordpress_publisher.republisher import republish_articles
    
    # 全記事を再投稿
    republish_articles('projects/setagaya_real_estate/config.yml')
    
    # 指定件数だけ再投稿
    republish_articles('projects/setagaya_real_estate/config.yml', limit=10)
"""

import logging
from pathlib import Path
from typing import Optional

from core.config import ProjectConfig
from modules.html_builder.builder import HTMLBuilder
from modules.article_manager import ArticleManager
from modules.wordpress_publisher.publisher import WordPressPublisher

logger = logging.getLogger(__name__)


def republish_articles(project_path: str, limit: Optional[int] = None) -> int:
    """
    既存の記事を再HTML化してWordPressを更新
    
    Args:
        project_path: プロジェクト設定ファイルのパス
        limit: 更新する記事数（Noneの場合は全件）
    
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
    
    # WordPress Publisher初期化
    try:
        wp_publisher = WordPressPublisher(
            article_manager=article_manager,
            project_dir=config.project_dir
        )
    except ValueError as e:
        logger.error(f"WordPress configuration error: {e}")
        logger.error("Please add WordPress settings to .env file")
        return 1
    
    # 投稿済みの記事を取得
    articles = article_manager.get_published_articles(limit=limit)
    
    if not articles:
        logger.warning("No published articles found")
        return 0
    
    logger.info(f"Found {len(articles)} published articles to update")
    
    success_count = 0
    failed_count = 0
    
    for i, article in enumerate(articles):
        logger.info(f"\n[{i+1}/{len(articles)}] Processing: {article['ward']}{article['choume']}")
        
        try:
            # Markdownファイルを読み込み
            markdown_path_str = article['markdown_path'].replace('\\', '/')
            markdown_path = config.project_dir / markdown_path_str
            markdown_path = markdown_path.resolve()
            
            if not markdown_path.exists():
                logger.warning(f"Markdown file not found: {markdown_path}")
                failed_count += 1
                continue
            
            # グラフパスを取得
            chart_path = None
            if article.get('chart_path'):
                chart_path_str = article['chart_path'].replace('\\', '/')
                chart_path = config.project_dir / chart_path_str
                chart_path = chart_path.resolve()
                if not chart_path.exists():
                    logger.warning(f"Chart file not found: {chart_path}")
                    chart_path = None
            
            # HTML出力パス
            html_path_str = article['html_path'].replace('\\', '/')
            html_path = config.project_dir / html_path_str
            html_path = html_path.resolve()
            
            # Markdownに既にデータが含まれているため、dataは不要
            # html_builder.build()はMarkdownから直接読み取る
            data = {}
            
            # 再HTML化
            logger.info(f"  → Rebuilding HTML from Markdown...")
            html_builder.build(
                markdown_path=markdown_path,
                chart_path=chart_path,
                output_path=html_path,
                data=data
            )
            
            logger.info(f"  ✅ HTML updated: {html_path.name}")
            
            # HTMLファイルを読み込み
            with open(html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            # WordPress用に本文部分のみを抽出
            body_content = wp_publisher._extract_body_content(html_content)
            
            # WordPressの既存投稿を更新
            wp_post_id = article['wp_post_id']
            
            logger.info(f"  → Updating WordPress post (ID: {wp_post_id})...")
            result = wp_publisher.update_post(
                post_id=wp_post_id,
                title=article['title'],
                content=body_content,
                status=article.get('wp_status', 'publish')
            )
            
            if result['success']:
                logger.info(f"  ✅ WordPress update successful: {article['choume']} (ID: {wp_post_id})")
                logger.info(f"  🔗 URL: {result.get('url', 'N/A')}")
                success_count += 1
            else:
                logger.error(f"  ❌ WordPress update failed: {article['choume']}: {result.get('error')}")
                failed_count += 1
        
        except Exception as e:
            logger.error(f"  ❌ Error processing {article.get('choume', 'unknown')}: {e}", exc_info=True)
            failed_count += 1
    
    # 結果サマリー
    logger.info("\n" + "=" * 70)
    logger.info("Republishing Complete")
    logger.info("=" * 70)
    logger.info(f"Success: {success_count}件")
    logger.info(f"Failed: {failed_count}件")
    logger.info("=" * 70)
    
    return 0 if failed_count == 0 else 1



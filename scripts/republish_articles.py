#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
既存の投稿を更新するスクリプト（ラッパー）

ASP承認後、affiliate_config.ymlを更新してから実行

使い方:
    # 全記事を再投稿
    python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml
    
    # 指定件数だけ再投稿
    python scripts/republish_articles.py --project projects/setagaya_real_estate/config.yml --limit 10
"""

import argparse
import logging
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from modules.wordpress_publisher.republisher import republish_articles

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def main():
    parser = argparse.ArgumentParser(description='既存のWordPress投稿を更新')
    parser.add_argument('--project', required=True, help='プロジェクト設定ファイル（例: projects/setagaya_real_estate/config.yml）')
    parser.add_argument('--limit', type=int, help='更新する記事数（デフォルト: 全件）')
    args = parser.parse_args()
    
    return republish_articles(args.project, args.limit)


if __name__ == '__main__':
    sys.exit(main())



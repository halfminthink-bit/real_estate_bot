#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース内のパスを修正（Windowsのバックスラッシュを / に統一）

使い方:
    python scripts/fix_db_paths.py
"""

import sqlite3
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

def fix_paths(db_path: Path):
    """データベース内のパスを修正"""
    if not db_path.exists():
        print(f"❌ データベースが見つかりません: {db_path}")
        return False
    
    conn = sqlite3.connect(str(db_path))
    cursor = conn.execute('SELECT id, html_path, chart_path, markdown_path FROM articles')
    rows = cursor.fetchall()
    
    if not rows:
        print("修正する記事がありません。")
        conn.close()
        return True
    
    print(f"\n見つかった記事: {len(rows)}件")
    print("=" * 70)
    
    fixed_count = 0
    for row_id, html_path, chart_path, markdown_path in rows:
        # パスを正規化
        new_html = html_path.replace('\\', '/') if html_path else ''
        new_chart = chart_path.replace('\\', '/') if chart_path else ''
        new_markdown = markdown_path.replace('\\', '/') if markdown_path else ''
        
        # 変更があるかチェック
        changed = (
            (html_path and html_path != new_html) or
            (chart_path and chart_path != new_chart) or
            (markdown_path and markdown_path != new_markdown)
        )
        
        if changed:
            print(f"ID {row_id}:")
            if html_path != new_html:
                print(f"  html_path: {html_path!r} -> {new_html!r}")
            if chart_path and chart_path != new_chart:
                print(f"  chart_path: {chart_path!r} -> {new_chart!r}")
            if markdown_path and markdown_path != new_markdown:
                print(f"  markdown_path: {markdown_path!r} -> {new_markdown!r}")
            
            conn.execute(
                'UPDATE articles SET html_path = ?, chart_path = ?, markdown_path = ? WHERE id = ?',
                (new_html, new_chart, new_markdown, row_id)
            )
            fixed_count += 1
    
    if fixed_count > 0:
        conn.commit()
        print("=" * 70)
        print(f"[OK] {fixed_count}件のパスを修正しました")
    else:
        print("[OK] 修正が必要なパスはありませんでした")
    
    conn.close()
    return True


def main():
    """メイン処理"""
    import argparse
    
    parser = argparse.ArgumentParser(description='データベースパス修正ツール')
    parser.add_argument('--yes', '-y', action='store_true', help='確認なしで実行')
    args = parser.parse_args()
    
    # デフォルトのデータベースパス
    db_path = project_root / 'projects' / 'setagaya_real_estate' / 'articles.db'
    
    print("=" * 70)
    print("データベースパス修正ツール")
    print("=" * 70)
    print(f"データベース: {db_path}")
    
    if not db_path.exists():
        print(f"\n❌ データベースが見つかりません: {db_path}")
        print("   プロジェクトディレクトリを指定してください。")
        return 1
    
    # 確認（--yes オプションがない場合のみ）
    if not args.yes:
        try:
            response = input(f"\n{db_path} のパスを修正しますか？ (y/N): ")
            if response.lower() != 'y':
                print("キャンセルしました。")
                return 0
        except EOFError:
            # 非対話環境の場合は自動実行
            print("\n非対話環境のため、自動実行します。")
    
    # 修正実行
    success = fix_paths(db_path)
    
    return 0 if success else 1


if __name__ == '__main__':
    sys.exit(main())


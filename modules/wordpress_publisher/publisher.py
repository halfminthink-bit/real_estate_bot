#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress REST APIを使った自動投稿モジュール

機能:
- ArticleManagerから未投稿記事を取得
- WordPress REST APIで投稿
- 投稿結果をArticleManagerに記録
- 予約投稿（1日5件ずつ、18:00）
"""

import base64
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Tuple, Optional
import requests
from dotenv import dotenv_values

from modules.article_manager import ArticleManager


class WordPressPublisher:
    """WordPress REST APIを使った自動投稿（ArticleManager版）"""

    WORDPRESS_ENV_KEYS = {
        "site_url": "WP_SITE_URL",
        "username": "WP_USERNAME",
        "app_password": "WP_APP_PASSWORD",
        "default_status": "WP_DEFAULT_STATUS",
        "default_category": "WP_DEFAULT_CATEGORY",
    }

    def __init__(self, article_manager: ArticleManager, project_dir: Path = None, config: dict = None):
        """
        初期化
        
        Args:
            article_manager: ArticleManagerインスタンス
            project_dir: プロジェクトディレクトリ（Noneの場合はDBパスから推測）
            config: WordPress設定（Noneの場合は.envから読み込み）
        """
        self.article_manager = article_manager
        
        # プロジェクトディレクトリを設定（DBパスから推測）
        if project_dir:
            self.project_dir = Path(project_dir)
        else:
            # ArticleManagerのDBパスから推測
            db_path = Path(article_manager.db_path)
            # projects/setagaya_real_estate/articles.db -> projects/setagaya_real_estate
            self.project_dir = db_path.parent
        
        # .envを読み込んで設定をマージ
        env_values = self._load_env_values()
        self.config = self._merge_config_with_env(config or {}, env_values)
        
        # WordPress REST API エンドポイント
        self.site_url = self.config["site_url"].rstrip('/')
        self.api_url = f"{self.site_url}/wp-json/wp/v2"
        
        # 認証情報
        self.username = self.config["username"]
        self.app_password = self.config["app_password"]
        
        # 投稿設定
        self.default_status = self.config.get("default_status", "future")
        self.default_category = self.config.get("default_category", "")
        
        # 設定情報を表示
        print("=" * 70)
        print("WordPress Publisher Configuration")
        print("=" * 70)
        print(f"  Site URL: {self.site_url}")
        print(f"  API URL: {self.api_url}")
        print(f"  Username: {self.username}")
        print(f"  App Password Length: {len(self.app_password)} chars")
        print(f"  Default Status: {self.default_status}")
        print(f"  Default Category: {self.default_category}")
        print("=" * 70)
    
    def publish_all(self, limit: int = None, republish: bool = False) -> dict:
        """
        未投稿記事をすべて投稿
        
        Args:
            limit: 投稿件数制限（Noneの場合は全件）
            republish: Trueの場合、投稿済み記事も含めて再投稿
        
        Returns:
            {"success": 3, "failed": 1, "skipped": 0}
        """
        print("\n" + "=" * 70)
        print("Starting WordPress Publishing Process")
        print("=" * 70)
        
        # 記事を取得
        if republish:
            # 再投稿モード: 全記事を取得
            articles = self.article_manager.get_all_for_republish()
            print(f"\n再投稿モード: 全記事 {len(articles)}件")
        else:
            # 通常モード: 未投稿記事のみ
            articles = self.article_manager.get_unpublished()
            print(f"\n未投稿記事: {len(articles)}件")
        
        if limit:
            articles = articles[:limit]
            print(f"制限: {limit}件まで投稿")
        
        if not articles:
            print("投稿する記事がありません。")
            return {"success": 0, "failed": 0, "skipped": 0}
        
        # 予約投稿の基準日を計算
        base_date = self._calculate_base_date()
        print(f"予約投稿基準日: {base_date.strftime('%Y-%m-%d %H:%M:%S')}")
        
        success_count = 0
        failed_count = 0
        
        for i, article in enumerate(articles):
            print(f"\n[{i+1}/{len(articles)}] {article['ward']}{article['choume']}")
            
            try:
                # HTMLファイルを読み込み（project_dirからの相対パス）
                html_path = self.project_dir / article['html_path']
                html_path = html_path.resolve()  # 絶対パスに変換
                
                if not html_path.exists():
                    print(f"  ❌ HTMLファイルが見つかりません")
                    print(f"     検索パス: {html_path}")
                    print(f"     プロジェクトディレクトリ: {self.project_dir.resolve()}")
                    print(f"     データベースのhtml_path: {article['html_path']}")
                    failed_count += 1
                    continue
                
                with open(html_path, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 本文部分のみを抽出（<body>タグ内 + h1削除）
                html_content = self._extract_body_content(html_content)
                
                # 画像をアップロード
                if article.get('chart_path'):
                    chart_path = self.project_dir / article['chart_path']
                    chart_path = chart_path.resolve()  # 絶対パスに変換
                    
                    if chart_path.exists():
                        # WordPressにアップロード
                        uploaded_url = self._upload_image_to_wordpress(chart_path)
                        
                        if uploaded_url:
                            # HTML内の画像パスを置き換え
                            # 元のパス例: ../charts/世田谷_上北沢4_price_graph.png
                            import re
                            
                            # imgタグを探して置き換え
                            def replace_img_src(match):
                                # src属性のみを置き換え
                                old_src = match.group(1)
                                if 'charts/' in old_src or '../charts/' in old_src:
                                    return f'<img src="{uploaded_url}"'
                                return match.group(0)
                            
                            html_content = re.sub(
                                r'<img\s+src="([^"]+)"',
                                replace_img_src,
                                html_content
                            )
                            
                            print(f"  ✅ 画像パス置き換え完了")
                        else:
                            print(f"  ⚠️ 画像アップロードに失敗（記事は投稿）")
                    else:
                        print(f"  ⚠️ グラフファイルが見つかりません: {chart_path}")
                else:
                    print(f"  ℹ️ グラフなし")
                
                # 予約投稿日時を計算（1日5件ずつ）
                days_to_add = (i // 5) + 1
                target_date = base_date + timedelta(days=days_to_add)
                target_date = target_date.replace(hour=18, minute=0, second=0, microsecond=0)
                post_date_iso = target_date.isoformat()
                
                # スラッグを生成
                slug = self._generate_slug(article['choume'])
                
                print(f"  📅 予約日時: {target_date.strftime('%Y-%m-%d %H:%M')}")
                print(f"  📝 タイトル: {article['title']}")
                print(f"  🔗 スラッグ: {slug}")
                
                # WordPress投稿
                success, result = self._post_to_wordpress(
                    title=article['title'],
                    content=html_content,
                    slug=slug,
                    post_status='future',
                    post_date=post_date_iso
                )
                
                if success:
                    # 投稿成功
                    post_id = result['id']
                    post_url = result['link']
                    
                    # ArticleManagerに記録
                    self.article_manager.update_wp_post(
                        ward=article['ward'],
                        choume=article['choume'],
                        wp_post_id=post_id,
                        wp_url=post_url,
                        status='future'
                    )
                    
                    print(f"  ✅ 投稿成功: WP ID={post_id}")
                    print(f"  🔗 URL: {post_url}")
                    success_count += 1
                else:
                    # 投稿失敗
                    print(f"  ❌ 投稿失敗: {result}")
                    failed_count += 1
            
            except Exception as e:
                print(f"  ❌ エラー: {e}")
                import traceback
                traceback.print_exc()
                failed_count += 1
        
        # 結果サマリー
        print("\n" + "=" * 70)
        print("投稿完了")
        print("=" * 70)
        print(f"成功: {success_count}件")
        print(f"失敗: {failed_count}件")
        print("=" * 70)
        
        return {
            "success": success_count,
            "failed": failed_count,
            "skipped": 0
        }
    
    def _upload_image_to_wordpress(self, image_path: Path) -> Optional[str]:
        """
        画像をWordPress Media Libraryにアップロード
        
        Args:
            image_path: ローカル画像パス
        
        Returns:
            アップロードされた画像URL or None
        """
        import mimetypes
        import hashlib
        
        if not image_path.exists():
            print(f"  ⚠️ 画像が見つかりません: {image_path}")
            return None
        
        # Application Passwordのスペース除去
        app_password_clean = self.app_password.replace(' ', '')
        
        credentials = f"{self.username}:{app_password_clean}"
        token = base64.b64encode(credentials.encode()).decode()
        
        # MIMEタイプを取得
        mime_type, _ = mimetypes.guess_type(str(image_path))
        if not mime_type:
            mime_type = 'image/png'
        
        # ファイル名を生成（日本語を避ける）
        file_hash = hashlib.md5(image_path.name.encode()).hexdigest()[:8]
        file_extension = image_path.suffix
        filename = f"chart-{file_hash}{file_extension}"
        
        headers = {
            'Authorization': f'Basic {token}',
            'Content-Disposition': f'attachment; filename="{filename}"',
        }
        
        print(f"  → 画像アップロード中: {image_path.name}")
        
        try:
            with open(image_path, 'rb') as f:
                response = requests.post(
                    f"{self.api_url}/media",
                    headers=headers,
                    files={'file': (filename, f, mime_type)},
                    timeout=60
                )
            
            print(f"  → Response: HTTP {response.status_code}")
            
            if response.status_code == 201:
                media_data = response.json()
                media_url = media_data['source_url']
                media_id = media_data['id']
                print(f"  ✅ 画像アップロード成功: ID={media_id}")
                print(f"  🔗 URL: {media_url}")
                return media_url
            else:
                print(f"  ❌ 画像アップロード失敗: {response.text[:200]}")
                return None
        
        except Exception as e:
            print(f"  ❌ 画像アップロードエラー: {e}")
            return None
    
    def _calculate_base_date(self) -> datetime:
        """
        予約投稿の基準日を計算
        
        Returns:
            datetime: 基準日時
        """
        # ArticleManagerから最新の投稿日時を取得
        published = self.article_manager.get_by_status('future')
        
        if published:
            # 最新の予約投稿日時を取得
            dates = []
            for article in published:
                if article['wp_posted_at']:
                    try:
                        dt = datetime.fromisoformat(article['wp_posted_at'])
                        dates.append(dt)
                    except:
                        pass
            
            if dates:
                last_date = max(dates)
                now = datetime.now()
                
                # 最新の予約日時が未来なら、その日時から続ける
                if last_date > now:
                    return last_date
        
        # デフォルトは現在時刻
        return datetime.now()
    
    def _extract_body_content(self, html: str) -> str:
        """
        HTMLから<body>内のコンテンツを抽出
        
        WordPress用に以下の処理を行う:
        - <body>タグ内のコンテンツを抽出
        - <h1>タグを削除（WordPressのタイトル欄と重複するため）
        - 最初の<div>コンテナを除去
        
        Args:
            html: 完全なHTMLファイルの内容
        
        Returns:
            str: <body>内のコンテンツ（<h1>タグ削除済み）
        """
        import re
        
        # <body>タグを探す
        match = re.search(r'<body[^>]*>(.*?)</body>', html, re.DOTALL)
        if match:
            body_content = match.group(1)
            
            # メインコンテナの中身だけを抽出
            div_match = re.search(r'<div[^>]*>(.*)</div>\s*$', body_content, re.DOTALL)
            if div_match:
                content = div_match.group(1).strip()
            else:
                content = body_content.strip()
            
            # <h1>タグをすべて削除
            # パターン1: <h1>...</h1>
            content = re.sub(r'<h1[^>]*>.*?</h1>', '', content, flags=re.DOTALL)
            
            # パターン2: 念のため自己閉じタグも
            content = re.sub(r'<h1[^>]*\s*/>', '', content)
            
            # 連続する改行を整理
            content = re.sub(r'\n{3,}', '\n\n', content)
            
            return content.strip()
        
        # <body>が見つからない場合はそのまま返す（<h1>は削除）
        content = re.sub(r'<h1[^>]*>.*?</h1>', '', html, flags=re.DOTALL)
        content = re.sub(r'<h1[^>]*\s*/>', '', content)
        return content.strip()
    
    def _generate_slug(self, choume: str) -> str:
        """
        町丁目からスラッグを生成
        
        Args:
            choume: 町丁目（例: 三軒茶屋1丁目、上北沢4丁目）
        
        Returns:
            str: スラッグ（例: sangenjaya-1-chome, kamikitazawa-4-chome）
        """
        try:
            from pykakasi import kakasi
            
            # pykakasiインスタンスを作成
            kks = kakasi()
            
            # ローマ字変換を実行
            result = kks.convert(choume)
            
            # hepburnフィールドを取得してスラッグを作成
            slug_parts = []
            for item in result:
                if 'hepburn' in item and item['hepburn']:
                    slug_parts.append(item['hepburn'])
            
            # ハイフンで連結
            slug = '-'.join(slug_parts)
            
            # 小文字化
            slug = slug.lower()
            
            # 不要な文字を除去（英数字とハイフンのみ）
            import re
            slug = re.sub(r'[^a-z0-9-]', '', slug)
            
            # 連続するハイフンを1つに
            slug = re.sub(r'-+', '-', slug)
            
            # 前後のハイフンを除去
            slug = slug.strip('-')
            
            # スラッグが空の場合はフォールバック
            if not slug:
                # 日本語をURLエンコード
                import urllib.parse
                slug = urllib.parse.quote(choume, safe='')
                print(f"  ⚠️ スラッグが空のためURLエンコード: {slug}")
            else:
                print(f"  → スラッグ変換: {choume} → {slug}")
            
            return slug
        
        except ImportError:
            # pykakasiがインストールされていない場合のフォールバック
            import urllib.parse
            slug = urllib.parse.quote(choume, safe='')
            print(f"  ⚠️ pykakasi未インストール、URLエンコード: {slug}")
            return slug
        except Exception as e:
            # エラー時は日本語をURLエンコード
            import urllib.parse
            slug = urllib.parse.quote(choume, safe='')
            print(f"  ⚠️ スラッグ生成エラー: {e}")
            print(f"  → フォールバック: {slug}")
            return slug
    
    def _post_to_wordpress(
        self,
        title: str,
        content: str,
        slug: str,
        post_status: str = 'future',
        post_date: Optional[str] = None
    ) -> Tuple[bool, any]:
        """
        WordPress REST APIで投稿
        
        Args:
            title: 投稿タイトル
            content: HTML本文
            slug: スラッグ
            post_status: 投稿ステータス（'publish', 'future', 'draft'）
            post_date: 予約投稿日時（ISO8601形式）
        
        Returns:
            (成功フラグ, 投稿データ or エラーメッセージ)
        """
        # Basic認証（Application Passwordのスペース除去）
        # Application Passwordのスペースを除去
        app_password_clean = self.app_password.replace(' ', '')
        
        credentials = f"{self.username}:{app_password_clean}"
        token = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        # デバッグ出力（初回のみ）
        if not hasattr(self, '_auth_debug_logged'):
            print(f"  [DEBUG] Username: {self.username}")
            print(f"  [DEBUG] App Password Length (original): {len(self.app_password)}")
            print(f"  [DEBUG] App Password Length (cleaned): {len(app_password_clean)}")
            print(f"  [DEBUG] Credentials: {self.username}:***{app_password_clean[-4:]}")
            self._auth_debug_logged = True
        
        # カテゴリIDを取得
        category_ids = []
        if self.default_category:
            cat_id = self._get_or_create_category(self.default_category)
            if cat_id:
                category_ids.append(cat_id)
        
        # 投稿データ
        post_data = {
            'title': title,
            'content': content,
            'slug': slug,
            'status': post_status,
        }
        
        if post_date:
            post_data['date'] = post_date
        
        if category_ids:
            post_data['categories'] = category_ids
        
        print(f"  → 投稿中... ({len(content)} chars)")
        
        try:
            response = requests.post(
                f"{self.api_url}/posts",
                json=post_data,
                headers=headers,
                timeout=30
            )
            
            print(f"  → Response: HTTP {response.status_code}")
            
            if response.status_code == 201:
                return True, response.json()
            else:
                # エラーメッセージをデコード
                try:
                    error_data = response.json()
                    error_message = error_data.get('message', response.text)
                    error_code = error_data.get('code', 'unknown')
                    error_msg = f"HTTP {response.status_code} ({error_code}): {error_message}"
                except:
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                
                return False, error_msg
        
        except requests.exceptions.RequestException as e:
            return False, f"Request error: {str(e)}"
        except Exception as e:
            return False, f"Unexpected error: {str(e)}"
    
    def _get_or_create_category(self, category_name: str) -> Optional[int]:
        """
        カテゴリを取得または作成
        
        Args:
            category_name: カテゴリ名
        
        Returns:
            カテゴリID or None
        """
        # Application Passwordのスペース除去
        app_password_clean = self.app_password.replace(' ', '')
        
        credentials = f"{self.username}:{app_password_clean}"
        token = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            'Authorization': f'Basic {token}',
            'Content-Type': 'application/json'
        }
        
        try:
            # カテゴリ一覧を取得
            response = requests.get(
                f"{self.api_url}/categories",
                headers=headers,
                params={'search': category_name},
                timeout=10
            )
            
            print(f"  → カテゴリ検索: HTTP {response.status_code}")
            
            if response.status_code == 200:
                categories = response.json()
                for cat in categories:
                    if cat['name'] == category_name:
                        print(f"  → カテゴリ: {category_name} (ID: {cat['id']})")
                        return cat['id']
            elif response.status_code == 401:
                print(f"  ⚠️ カテゴリ検索で認証エラー（401）")
                return None
            
            # カテゴリが存在しない場合は作成
            print(f"  → カテゴリ作成: {category_name}")
            create_response = requests.post(
                f"{self.api_url}/categories",
                json={'name': category_name},
                headers=headers,
                timeout=10
            )
            
            print(f"  → カテゴリ作成: HTTP {create_response.status_code}")
            
            if create_response.status_code == 201:
                cat_data = create_response.json()
                print(f"  → カテゴリ作成完了: ID={cat_data['id']}")
                return cat_data['id']
            elif create_response.status_code == 401:
                print(f"  ⚠️ カテゴリ作成で認証エラー（401）")
                return None
            else:
                print(f"  ⚠️ カテゴリ作成失敗: {create_response.text[:100]}")
                return None
        
        except Exception as e:
            print(f"  ⚠️ カテゴリ取得/作成エラー: {e}")
            return None
    
    def _load_env_values(self) -> Dict[str, Optional[str]]:
        """
        プロジェクトルートの .env を読み込む
        
        Returns:
            dict: .envのキーと値
        """
        # プロジェクトルートを取得（このファイルの位置から推測）
        import sys
        from pathlib import Path
        
        # modules/wordpress_publisher/publisher.py -> プロジェクトルート
        current_file = Path(__file__)
        project_root = current_file.parent.parent.parent
        
        env_path = project_root / ".env"
        if env_path.exists():
            return dotenv_values(env_path)
        return {}
    
    def _merge_config_with_env(
        self, 
        config: Dict[str, any], 
        env_values: Dict[str, Optional[str]]
    ) -> Dict[str, any]:
        """
        WordPress設定を .env で上書き
        
        Args:
            config: 元の設定
            env_values: .envの値
        
        Returns:
            マージされた設定
        """
        merged = dict(config or {})
        
        for cfg_key, env_key in self.WORDPRESS_ENV_KEYS.items():
            env_value = env_values.get(env_key)
            if env_value not in (None, ""):
                merged[cfg_key] = env_value
        
        # 必須項目チェック
        required_keys = ["site_url", "username", "app_password"]
        missing = [key for key in required_keys if not merged.get(key)]
        if missing:
            raise ValueError(f"Missing WordPress configuration: {', '.join(missing)}")
        
        return merged





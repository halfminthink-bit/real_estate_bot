#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WordPress認証テストスクリプト

機能:
- .envからWordPress設定を読み込み
- Application Password認証をテスト
- ユーザー情報を取得して権限を確認
"""

import sys
import base64
from pathlib import Path
import requests
from dotenv import dotenv_values

# プロジェクトルート
project_root = Path(__file__).parent.parent

def test_authentication():
    """WordPress認証テスト"""
    print("=" * 70)
    print("WordPress認証テスト")
    print("=" * 70)
    
    # .env読み込み
    env_path = project_root / ".env"
    if not env_path.exists():
        print(f"❌ .envファイルが見つかりません: {env_path}")
        return
    
    env = dotenv_values(env_path)
    
    # 設定取得
    site_url = env.get('WP_SITE_URL', '').rstrip('/')
    username = env.get('WP_USERNAME', '')
    app_password = env.get('WP_APP_PASSWORD', '')
    
    if not all([site_url, username, app_password]):
        print("❌ WordPress設定が不足しています")
        print(f"   WP_SITE_URL: {'✓' if site_url else '✗'}")
        print(f"   WP_USERNAME: {'✓' if username else '✗'}")
        print(f"   WP_APP_PASSWORD: {'✓' if app_password else '✗'}")
        return
    
    print(f"\n設定:")
    print(f"  Site URL: {site_url}")
    print(f"  Username: {username}")
    print(f"  App Password Length: {len(app_password)} chars")
    print(f"  App Password (masked): {app_password[:4]}...{app_password[-4:]}")
    
    # Test 1: スペース除去なし
    print("\n" + "-" * 70)
    print("Test 1: Application Password（元のまま）")
    print("-" * 70)
    test_auth_request(site_url, username, app_password)
    
    # Test 2: スペース除去
    app_password_clean = app_password.replace(' ', '')
    if app_password_clean != app_password:
        print("\n" + "-" * 70)
        print("Test 2: Application Password（スペース除去）")
        print("-" * 70)
        print(f"  Cleaned Length: {len(app_password_clean)} chars")
        test_auth_request(site_url, username, app_password_clean)

def test_auth_request(site_url: str, username: str, app_password: str):
    """認証リクエストを実行"""
    # Basic認証
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {token}',
    }
    
    print(f"  Credentials: {username}:***{app_password[-4:]}")
    print(f"  Token (first 20): {token[:20]}...")
    
    try:
        # ユーザー情報取得
        response = requests.get(
            f"{site_url}/wp-json/wp/v2/users/me",
            headers=headers,
            timeout=10
        )
        
        print(f"  Response: HTTP {response.status_code}")
        
        if response.status_code == 200:
            user_data = response.json()
            print(f"  ✅ 認証成功")
            print(f"     User ID: {user_data.get('id')}")
            print(f"     Name: {user_data.get('name')}")
            print(f"     Roles: {user_data.get('roles', [])}")
            
            # 権限情報を取得
            capabilities = user_data.get('capabilities', {})
            if capabilities:
                print(f"     Capabilities: {list(capabilities.keys())[:5]}...")
            
            # 投稿権限チェック
            can_publish = capabilities.get('publish_posts', False)
            can_edit = capabilities.get('edit_posts', False)
            can_create = capabilities.get('create_posts', False)
            
            print(f"\n  投稿権限:")
            print(f"     publish_posts: {'✅' if can_publish else '❌'}")
            print(f"     edit_posts: {'✅' if can_edit else '❌'}")
            print(f"     create_posts: {'✅' if can_create else '❌'}")
            
            if can_publish and can_edit and can_create:
                print(f"  ✅ 投稿に必要な権限があります")
            else:
                print(f"  ⚠️ 投稿権限が不足している可能性があります")
        
        elif response.status_code == 401:
            print(f"  ❌ 認証失敗（401 Unauthorized）")
            try:
                error = response.json()
                print(f"     Code: {error.get('code')}")
                print(f"     Message: {error.get('message')}")
            except:
                print(f"     Response: {response.text[:100]}")
        
        else:
            print(f"  ❌ エラー: HTTP {response.status_code}")
            print(f"     Response: {response.text[:200]}")
    
    except requests.exceptions.RequestException as e:
        print(f"  ❌ リクエストエラー: {e}")
    except Exception as e:
        print(f"  ❌ 予期しないエラー: {e}")

def main():
    test_authentication()
    
    print("\n" + "=" * 70)
    print("テスト完了")
    print("=" * 70)
    print("\n対処方法:")
    print("1. 認証失敗の場合:")
    print("   → WordPress管理画面でApplication Passwordを再生成")
    print("   → .envファイルを更新")
    print("\n2. 権限不足の場合:")
    print("   → WordPress管理画面でユーザー権限を「管理者」に変更")
    print("\n3. 両方OKの場合:")
    print("   → WordPress投稿スクリプトを再実行")
    print("=" * 70)

if __name__ == "__main__":
    main()







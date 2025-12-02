#!/usr/bin/env python3
"""WordPress POSTリクエストテスト"""

import sys
import base64
from pathlib import Path
import requests
from dotenv import dotenv_values

project_root = Path(__file__).parent

def test_post_request():
    """POSTリクエストのテスト"""
    env_path = project_root / ".env"
    
    if not env_path.exists():
        print(f"❌ .envファイルが見つかりません: {env_path}")
        print("\n.envファイルを作成してください。例:")
        print("WP_SITE_URL=https://yoursite.com")
        print("WP_USERNAME=your_username")
        print("WP_APP_PASSWORD=xxxx xxxx xxxx xxxx")
        return
    
    env = dotenv_values(env_path)
    
    # 必要なキーのチェック
    required_keys = ['WP_SITE_URL', 'WP_USERNAME', 'WP_APP_PASSWORD']
    missing_keys = [key for key in required_keys if not env.get(key)]
    
    if missing_keys:
        print(f"❌ .envファイルに必要な設定が不足しています:")
        for key in missing_keys:
            print(f"   - {key}")
        print("\n.envファイルに以下を追加してください:")
        for key in missing_keys:
            print(f"{key}=your_value")
        return
    
    site_url = env['WP_SITE_URL'].rstrip('/')
    username = env['WP_USERNAME']
    app_password = env['WP_APP_PASSWORD'].replace(' ', '')
    
    credentials = f"{username}:{app_password}"
    token = base64.b64encode(credentials.encode()).decode()
    
    headers = {
        'Authorization': f'Basic {token}',
        'Content-Type': 'application/json'
    }
    
    print("=" * 70)
    print("WordPress POSTリクエストテスト")
    print("=" * 70)
    print(f"Site: {site_url}")
    print(f"User: {username}")
    
    # テスト投稿（下書き）
    post_data = {
        'title': 'テスト投稿（削除してください）',
        'content': 'これはREST APIのテスト投稿です。',
        'status': 'draft'
    }
    
    print("\n下書き投稿をテスト中...")
    
    try:
        response = requests.post(
            f"{site_url}/wp-json/wp/v2/posts",
            json=post_data,
            headers=headers,
            timeout=30
        )
        
        print(f"Response: HTTP {response.status_code}")
        
        if response.status_code == 201:
            data = response.json()
            print(f"✅ 投稿成功!")
            print(f"   Post ID: {data['id']}")
            print(f"   URL: {data['link']}")
            print(f"\n※この下書きは削除してください")
        else:
            print(f"❌ 投稿失敗")
            try:
                error = response.json()
                print(f"   Code: {error.get('code')}")
                print(f"   Message: {error.get('message')}")
            except:
                print(f"   Response: {response.text[:200]}")
    
    except Exception as e:
        print(f"❌ エラー: {e}")

if __name__ == "__main__":
    test_post_request()
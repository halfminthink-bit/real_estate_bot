#!/usr/bin/env python3
"""
記事生成テスト（Phase 2対応：新プロンプト）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.data_aggregator.collectors.land_price_collector import LandPriceCollector
from modules.content_generator.generator import ContentGenerator
from modules.content_generator.llm.anthropic_client import AnthropicClient
from core.models import Area, ScoreResult
from core.config import ProjectConfig
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    print("="*80)
    print("記事生成テスト（Phase 2: 新プロンプト）")
    print("="*80)
    
    # テスト対象エリア
    area = Area(
        area_id=2,
        ward='世田谷区',
        choume='三軒茶屋1丁目',
        priority='high',
        choume_code=None  # 住所検索で動作確認
    )
    
    print(f"\n対象エリア: {area.ward}{area.choume}")
    
    # データ取得
    print("\n1. データ取得中...")
    collector = LandPriceCollector()
    data = collector.fetch(area)
    
    if not data:
        print("❌ データ取得失敗")
        return
    
    print(f"✅ データ取得成功")
    history = data.get('land_price_history', [])
    print(f"   期間: {len(history)}年分")
    print(f"   平均: {data.get('latest_price', 0):,}円/㎡")
    print(f"   価格帯: {data.get('latest_price_min', 0):,}〜{data.get('latest_price_max', 0):,}円/㎡")
    print(f"   地点数: {data.get('latest_point_count', 1)}地点")
    
    # スコア（仮）
    score = ScoreResult(
        area_id=area.area_id,
        asset_value_score=100,
        safety_score=0,
        education_score=0,
        convenience_score=0,
        living_score=0,
        total_score=100
    )
    
    # 記事生成
    print("\n2. 記事生成中...")
    
    config = ProjectConfig('projects/setagaya_real_estate/config.yml')
    api_key = os.getenv('ANTHROPIC_API_KEY')
    
    if not api_key:
        print("❌ ANTHROPIC_API_KEYが設定されていません")
        print("   .envファイルにANTHROPIC_API_KEYを設定してください")
        return
    
    llm_client = AnthropicClient(api_key=api_key, model='claude-sonnet-4-5-20250929')
    generator = ContentGenerator(config, llm_client)
    
    # 記事生成
    article = generator.generate(area, score, data)
    
    if article:
        print(f"✅ 記事生成成功")
        print(f"   文字数: {len(article)}文字")
        print(f"\n【生成された記事（最初の500文字）】")
        print("="*80)
        print(article[:500])
        print("...")
        print("="*80)
        
        # ファイル保存
        output_dir = Path(__file__).parent.parent / 'test_output'
        output_dir.mkdir(exist_ok=True)
        output_path = output_dir / f"{area.choume}_article.md"
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(article)
        
        print(f"\n✅ 記事を保存: {output_path}")
    else:
        print("❌ 記事生成失敗")
    
    print("\n" + "="*80)
    print("テスト完了")
    print("="*80)

if __name__ == '__main__':
    main()

"""
地価推移グラフ生成
"""
import matplotlib
matplotlib.use('Agg')  # GUIなし環境対応
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class PriceGraphGenerator:
    """地価推移グラフを生成"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 日本語フォント設定（既存のChartGeneratorと同じロジック）
        self._setup_japanese_font()
        
        logger.info(f"Initialized PriceGraphGenerator with output_dir={output_dir}")
    
    def _setup_japanese_font(self):
        """日本語フォント設定"""
        # 既存のChartGeneratorと同じロジック
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']
    
    def generate_price_graph(
        self, 
        price_history: List[Dict],
        area_name: str
    ) -> str:
        """
        地価推移グラフを生成
        
        Args:
            price_history: [{'year': 2021, 'price': 720000, 'change': 0.0}, ...]
            area_name: "三軒茶屋1丁目"
        
        Returns:
            str: 画像ファイル名（相対パス）
        """
        if not price_history:
            logger.warning(f"No price history data for {area_name}")
            return ""
        
        # データ抽出
        years = [item['year'] for item in price_history]
        prices = [item['price'] for item in price_history]
        
        # グラフ作成
        plt.figure(figsize=(10, 6))
        plt.plot(years, prices, marker='o', linewidth=2.5, 
                color='#1E3A8A', markersize=8)
        plt.fill_between(years, prices, alpha=0.2, color='#1E3A8A')
        
        # タイトル・ラベル
        plt.title('地価推移（過去5年）', fontsize=16, pad=20, fontweight='bold')
        plt.xlabel('年', fontsize=12)
        plt.ylabel('地価（円/㎡）', fontsize=12)
        
        # グリッド
        plt.grid(True, alpha=0.3, linestyle='--')
        
        # 各点に価格を表示
        for x, y in zip(years, prices):
            plt.annotate(
                f'{y:,}',
                (x, y),
                textcoords="offset points",
                xytext=(0, 10),
                ha='center',
                fontsize=10,
                bbox=dict(boxstyle='round,pad=0.3', 
                         facecolor='white', 
                         edgecolor='#1E3A8A', 
                         alpha=0.8)
            )
        
        # 変動率を表示（最新年のみ）
        if len(price_history) >= 2:
            latest_change = price_history[-1].get('change', 0)
            if latest_change is not None:
                if latest_change > 0:
                    color = '#22C55E'  # 緑
                    prefix = '+'
                elif latest_change < 0:
                    color = '#EF4444'  # 赤
                    prefix = ''
                else:
                    color = '#6B7280'  # グレー
                    prefix = ''
                
                plt.text(
                    years[-1], prices[-1],
                    f'{prefix}{latest_change:.1f}%',
                    fontsize=11,
                    color=color,
                    ha='center',
                    va='bottom',
                    bbox=dict(boxstyle='round,pad=0.3', 
                             facecolor='white', 
                             edgecolor=color,
                             alpha=0.9)
                )
        
        # レイアウト調整
        plt.tight_layout()
        
        # 保存
        safe_name = area_name.replace('/', '_').replace('\\', '_').replace('区', '').replace('丁目', '')
        filename = f"{safe_name}_price_graph.png"
        output_path = self.output_dir / filename
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Generated price graph: {output_path}")
        
        # ファイル名のみを返す（Markdownで使用）
        return filename


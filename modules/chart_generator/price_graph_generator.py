"""
地価推移グラフ生成（ハイブリッド表示：平均値 + 価格帯レンジ）
"""
import matplotlib
matplotlib.use('Agg')  # GUIなし環境対応
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm
from pathlib import Path
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class PriceGraphGenerator:
    """地価推移グラフを生成（ハイブリッド表示）"""
    
    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._setup_japanese_font()
        logger.info(f"Initialized PriceGraphGenerator with output_dir={output_dir}")
    
    def _setup_japanese_font(self):
        """日本語フォント設定（文字化け対策）"""
        import platform
        
        plt.rcParams['font.family'] = 'sans-serif'
        
        # OSに応じてフォントを設定
        if platform.system() == 'Windows':
            plt.rcParams['font.sans-serif'] = [
                'MS Gothic', 'Yu Gothic', 'Meiryo', 'DejaVu Sans'
            ]
        elif platform.system() == 'Darwin':  # macOS
            plt.rcParams['font.sans-serif'] = [
                'Hiragino Sans', 'AppleGothic', 'DejaVu Sans'
            ]
        else:  # Linux
            plt.rcParams['font.sans-serif'] = [
                'Noto Sans CJK JP', 'DejaVu Sans'
            ]
        
        plt.rcParams['axes.unicode_minus'] = False
    
    def _format_price(self, price: float) -> str:
        """
        金額を読みやすい形式に変換（グラフ用）
        
        Args:
            price: 価格（円/㎡）
        
        Returns:
            str: フォーマット済み文字列（例: "65万円/㎡", "1.2億円/㎡"）
        """
        if price >= 100000000:  # 1億円以上
            return f'{price / 100000000:.1f}億円/㎡'
        elif price >= 10000000:  # 1000万円以上
            return f'{price / 10000000:.0f}万円/㎡'
        elif price >= 10000:  # 1万円以上
            return f'{price / 10000:.0f}万円/㎡'
        else:
            return f'{price:,.0f}円/㎡'
    
    def _format_price_for_axis(self, price: float) -> str:
        """
        Y軸用の金額フォーマット（単位のみ、数値はmatplotlibが自動設定）
        
        Args:
            price: 価格（円/㎡）
        
        Returns:
            str: 単位のみ（例: "万円/㎡", "億円/㎡"）
        """
        if price >= 100000000:  # 1億円以上
            return '億円/㎡'
        elif price >= 10000:  # 1万円以上
            return '万円/㎡'
        else:
            return '円/㎡'
    
    def generate_price_graph(
        self, 
        price_history: List[Dict],
        area_name: str
    ) -> Optional[Path]:
        """
        地価推移グラフを生成（ハイブリッド表示：平均値 + 価格帯レンジ）
        
        Args:
            price_history: [
                {
                    'year': 2000, 
                    'price': 620000,      # 平均
                    'price_min': 555000,  # 最小
                    'price_max': 683000,  # 最大
                    'point_count': 2,     # 地点数
                    'change': 0.0
                }, 
                ...
            ]
            area_name: "三軒茶屋1丁目"
        
        Returns:
            Path: 画像ファイルのパス（存在しない場合はNone）
        """
        if not price_history:
            logger.warning(f"No price history data for {area_name}")
            return None
        
        # データ抽出
        years = [item['year'] for item in price_history]
        avg_prices = [item['price'] for item in price_history]
        min_prices = [item.get('price_min', item['price']) for item in price_history]
        max_prices = [item.get('price_max', item['price']) for item in price_history]
        point_counts = [item.get('point_count', 1) for item in price_history]
        
        num_years = len(years)
        
        # グラフ作成（横長）
        fig, ax = plt.subplots(figsize=(14, 7))
        
        # 価格帯の影（最小〜最大）
        ax.fill_between(years, min_prices, max_prices, 
                        alpha=0.15, color='#1E3A8A', 
                        label=f'価格帯の幅（{point_counts[-1]}地点）')
        
        # 平均値ライン（メイン）
        ax.plot(years, avg_prices, marker='o', linewidth=3, 
                color='#1E3A8A', markersize=7, 
                label='平均地価', zorder=5)
        
        # タイトル・ラベル
        title = f'{area_name} 地価推移（{years[0]}-{years[-1]}年）'
        ax.set_title(title, fontsize=16, pad=20, fontweight='bold')
        ax.set_xlabel('年', fontsize=12)
        
        # Y軸の単位を決定（最大価格に基づく）
        max_price = max(max_prices)
        y_unit = self._format_price_for_axis(max_price)
        ax.set_ylabel(f'地価（{y_unit}）', fontsize=12)
        
        # グリッド
        ax.grid(True, alpha=0.3, linestyle='--', linewidth=0.8)
        
        # 主要イベント注釈（26年分の場合）
        if num_years >= 20:
            # リーマンショック
            if 2008 in years:
                idx = years.index(2008)
                ax.axvline(x=2008, color='#EF4444', linestyle='--', 
                          linewidth=1.5, alpha=0.6, zorder=1)
                ax.annotate('リーマンショック', 
                           xy=(2008, avg_prices[idx]), 
                           xytext=(2008, avg_prices[idx] * 0.85),  # 下に配置（コロナ禍と同じ）
                           ha='center', fontsize=10,
                           bbox=dict(boxstyle='round,pad=0.4', 
                                   facecolor='#FEE2E2', 
                                   edgecolor='#EF4444',
                                   alpha=0.8),
                           arrowprops=dict(arrowstyle='->', 
                                         color='#EF4444',
                                         lw=1.5),
                           zorder=10)
            
            # コロナ禍
            if 2020 in years:
                idx = years.index(2020)
                ax.axvline(x=2020, color='#F59E0B', linestyle='--', 
                          linewidth=1.5, alpha=0.6, zorder=1)
                ax.annotate('コロナ禍', 
                           xy=(2020, avg_prices[idx]), 
                           xytext=(2020, avg_prices[idx] * 0.85),
                           ha='center', fontsize=10,
                           bbox=dict(boxstyle='round,pad=0.4', 
                                   facecolor='#FEF3C7', 
                                   edgecolor='#F59E0B',
                                   alpha=0.8),
                           arrowprops=dict(arrowstyle='->', 
                                         color='#F59E0B',
                                         lw=1.5),
                           zorder=10)
        
        # 平均価格表示（間引き）
        if num_years <= 10:
            display_indices = range(len(years))
        elif num_years <= 20:
            display_indices = [0] + list(range(1, len(years)-1, 2)) + [len(years)-1]
        else:
            display_indices = [0] + list(range(4, len(years)-1, 5)) + [len(years)-1]
        
        for i in display_indices:
            # 価格を読みやすい形式に変換
            price_text = self._format_price(avg_prices[i])
            ax.annotate(
                price_text,
                (years[i], avg_prices[i]),
                textcoords="offset points",
                xytext=(0, 8),
                ha='center',
                fontsize=9,
                bbox=dict(boxstyle='round,pad=0.3', 
                         facecolor='white', 
                         edgecolor='#1E3A8A', 
                         alpha=0.9),
                zorder=10)
        
        # 最新年の変動率表示
        if len(price_history) >= 2:
            latest_change = price_history[-1].get('change', 0)
            if latest_change is not None:
                if latest_change > 0:
                    color = '#22C55E'
                    prefix = '+'
                elif latest_change < 0:
                    color = '#EF4444'
                    prefix = ''
                else:
                    color = '#6B7280'
                    prefix = ''
                
                ax.text(
                    years[-1], avg_prices[-1] * 1.05,
                    f'前年比 {prefix}{latest_change:.1f}%',
                    fontsize=11,
                    color=color,
                    ha='center',
                    va='bottom',
                    fontweight='bold',
                    bbox=dict(boxstyle='round,pad=0.4', 
                             facecolor='white', 
                             edgecolor=color,
                             linewidth=2,
                             alpha=0.95),
                    zorder=10)
        
        # 価格帯の情報（右下）
        latest_min = min_prices[-1]
        latest_max = max_prices[-1]
        latest_points = point_counts[-1]
        # 価格を読みやすい形式に変換
        min_text = self._format_price(latest_min)
        max_text = self._format_price(latest_max)
        info_text = f'価格帯: {min_text}〜{max_text}\n地点数: {latest_points}地点'
        ax.text(0.98, 0.03, info_text,
                transform=ax.transAxes,
                fontsize=10,
                verticalalignment='bottom',
                horizontalalignment='right',
                bbox=dict(boxstyle='round,pad=0.5', 
                         facecolor='white', 
                         edgecolor='#1E3A8A',
                         alpha=0.9),
                zorder=10)
        
        # 凡例
        ax.legend(loc='upper left', fontsize=10, framealpha=0.9)
        
        # Y軸のフォーマット（万円/億円形式）
        # 最大価格に基づいて単位を決定
        max_price = max(max_prices)
        if max_price >= 100000000:  # 1億円以上
            # 億円単位
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{x / 100000000:.1f}億'))
        elif max_price >= 10000:  # 1万円以上
            # 万円単位
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x / 10000)}万'))
        else:
            # 円単位（カンマ区切り）
            ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, p: f'{int(x):,}'))
        
        # レイアウト調整
        plt.tight_layout()
        
        # 保存
        safe_name = area_name.replace('/', '_').replace('\\', '_').replace('区', '').replace('丁目', '')
        filename = f"{safe_name}_price_graph.png"
        output_path = self.output_dir / filename
        
        plt.savefig(output_path, dpi=150, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        plt.close()
        
        logger.info(f"Generated hybrid price graph ({num_years} years, {latest_points} points): {output_path}")
        
        return output_path  # Pathオブジェクトを返す


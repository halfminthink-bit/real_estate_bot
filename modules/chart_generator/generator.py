import matplotlib
matplotlib.use('Agg')  # GUIなし環境対応
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from core.models import ScoreResult, Area
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    """レーダーチャート生成"""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # 日本語フォント設定（DejaVu Sansをフォールバック）
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial']

        logger.info(f"Initialized ChartGenerator with output_dir={output_dir}")

    def generate(self, area: Area, score: ScoreResult) -> Path:
        """
        レーダーチャート生成

        Returns:
            生成された画像のパス
        """
        logger.info(f"Generating radar chart for {area.ward}{area.choume}")

        labels = ['治安', '教育', '利便性', '資産価値', '住環境']
        values = [
            score.safety_score,
            score.education_score,
            score.convenience_score,
            score.asset_value_score,
            score.living_score
        ]

        # レーダーチャート描画
        angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
        values_plot = values + values[:1]  # 閉じるために最初の値を追加
        angles_plot = angles + angles[:1]

        fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(projection='polar'))
        ax.plot(angles_plot, values_plot, 'o-', linewidth=2, color='#FF6B35')
        ax.fill(angles_plot, values_plot, alpha=0.25, color='#FF6B35')
        ax.set_thetagrids(np.degrees(angles), labels)
        ax.set_ylim(0, 100)
        ax.set_title(f'{area.ward}{area.choume} Livability Score', pad=20, fontsize=16, fontweight='bold')
        ax.grid(True, linestyle='--', alpha=0.7)

        # グリッド線のカスタマイズ
        ax.set_yticks([20, 40, 60, 80, 100])
        ax.set_yticklabels(['20', '40', '60', '80', '100'])

        # 保存
        filename = f"{area.ward.replace('区', '')}_{area.choume.replace('丁目', '')}_radar.png"
        output_path = self.output_dir / filename
        plt.savefig(output_path, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()

        logger.info(f"Chart saved to {output_path}")
        return output_path

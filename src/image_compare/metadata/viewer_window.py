"""メタデータ表示ウィンドウ。

現時点ではタブ分けは行わず、見つかったテキストメタデータのキーと生データを
そのまま縦に並べて表示するだけの、最小限の実装とする。
タブUI・タイル配置との連動・スクロール同期は将来の拡張候補
(まずはこの最小形で実際に使ってみて、必要性を見極める)。
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QLabel,
    QTextEdit,
    QScrollArea,
    QWidget,
)

from image_compare.metadata.reader import read_text_metadata


class MetadataWindow(QDialog):
    """1枚の画像のテキストメタデータを表示する別ウィンドウ。"""

    def __init__(self, image_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"メタデータ - {image_path.name}")
        self.resize(700, 800)

        outer_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        outer_layout.addWidget(scroll_area)

        content = QWidget()
        content_layout = QVBoxLayout(content)
        scroll_area.setWidget(content)

        text_data = read_text_metadata(image_path)

        if not text_data:
            no_data_label = QLabel("テキストメタデータは見つかりませんでした。")
            no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            content_layout.addWidget(no_data_label)
            return

        for key, value in text_data.items():
            key_label = QLabel(f"[{key}]")
            key_label.setStyleSheet("font-weight: bold;")
            content_layout.addWidget(key_label)

            text_edit = QTextEdit()
            text_edit.setPlainText(value)
            text_edit.setReadOnly(True)
            # 内容量に応じて自然な高さになるよう、大まかな目安を設定する
            text_edit.setMinimumHeight(150)
            content_layout.addWidget(text_edit)

        content_layout.addStretch(1)
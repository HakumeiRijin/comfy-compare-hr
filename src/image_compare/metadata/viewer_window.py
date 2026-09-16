"""メタデータ表示ウィンドウ。

現時点ではタブ分けは行わず、見つかったテキストメタデータのキーと生データを
そのまま縦に並べて表示するだけの、最小限の実装とする。
タブUI・スクロール同期の作り込みは、まずこの土台で表示できることを
確認してから、必要性を見極めて追加していく。
"""
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QGridLayout,
    QLabel,
    QTextEdit,
    QScrollArea,
    QWidget,
)

from image_compare.layout_rules import columns_for_count
from image_compare.metadata.reader import read_text_metadata


def _build_metadata_panel(
    image_path: Path,
    show_title: bool = True,
    excluded_keys: frozenset[str] = frozenset(),
) -> QWidget:
    """1枚の画像分のメタデータ表示パネル(見出し+キーごとのテキスト)を作る。

    MetadataWindow(1枚版)とMultiMetadataWindow(複数枚版)の両方から
    共通して使う、画像1枚あたりの表示内容を組み立てる部分。
    show_title=Falseの場合、ファイル名の見出しラベルを省略する
    (1枚版はウィンドウタイトルに既にファイル名が出るため重複を避ける)。
    excluded_keysに含まれるキーは表示から除外する
    (全画像版でworkflowのような分量の多いキーを省くために使う)。
    """
    panel = QWidget()
    layout = QVBoxLayout(panel)

    if show_title:
        title_label = QLabel(image_path.name)
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title_label)

    text_data = read_text_metadata(image_path)

    if not text_data:
        no_data_label = QLabel("テキストメタデータは見つかりませんでした。")
        no_data_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(no_data_label)
        return panel

    for key, value in text_data.items():
        if key in excluded_keys:
            continue

        key_label = QLabel(f"[{key}]")
        key_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(key_label)

        text_edit = QTextEdit()
        text_edit.setPlainText(value)
        text_edit.setReadOnly(True)
        # 内容量に応じて自然な高さになるよう、大まかな目安を設定する
        text_edit.setMinimumHeight(150)
        layout.addWidget(text_edit)

    return panel


class MetadataWindow(QDialog):
    """1枚の画像のテキストメタデータを表示する別ウィンドウ。"""

    def __init__(self, image_path: Path, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"メタデータ - {image_path.name}")
        self.resize(700, 800)
        # QDialogは既定では閉じるボタンのみのため、最大化ボタンを明示的に
        # 追加する(メタデータをじっくり見比べたい用途のため)。
        # 最小化ボタンは、QDialogでは最小化後の挙動が不安定
        # (タスクバーに行かず画面内に妙な形で残る、サイズが戻らなくなる等)
        # だったため、追加しないことにした。
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint
        )

        outer_layout = QVBoxLayout(self)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        outer_layout.addWidget(scroll_area)

        panel = _build_metadata_panel(image_path, show_title=False)
        scroll_area.setWidget(panel)


# 全画像版では、workflowは分量が多く要点把握の妨げになりやすいため表示しない。
# 1枚版(MetadataWindow)は対象外で、これまで通り全キーを表示する。
MULTI_VIEW_EXCLUDED_KEYS = frozenset({"workflow"})


class MultiMetadataWindow(QDialog):
    """表示中の全画像のテキストメタデータを、画像タイルと同じ配置で表示する別ウィンドウ。

    列数は layout_rules.columns_for_count() を再利用し、メイン画面の
    タイル配置と一致させる。各パネルのスクロールは独立しており連動しない
    (個別に見たい場合はMetadataWindowを1枚ずつ開けばよいため実用上問題は
    小さいと判断し、スクロール連動の実装は見送った)。
    """

    def __init__(self, image_paths: list[Path], parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("メタデータ - すべての画像")
        self.resize(1200, 800)
        # QDialogは既定では閉じるボタンのみのため、最大化ボタンを明示的に
        # 追加する(メタデータをじっくり見比べたい用途のため)。
        # 最小化ボタンは、QDialogでは最小化後の挙動が不安定
        # (タスクバーに行かず画面内に妙な形で残る、サイズが戻らなくなる等)
        # だったため、追加しないことにした。
        self.setWindowFlags(
            self.windowFlags() | Qt.WindowType.WindowMaximizeButtonHint
        )

        outer_layout = QGridLayout(self)

        if not image_paths:
            empty_label = QLabel("表示中の画像がありません。")
            empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            outer_layout.addWidget(empty_label, 0, 0)
            return

        columns = columns_for_count(len(image_paths))

        for index, image_path in enumerate(image_paths):
            row = index // columns
            col = index % columns

            scroll_area = QScrollArea()
            scroll_area.setWidgetResizable(True)
            scroll_area.setWidget(
                _build_metadata_panel(image_path, excluded_keys=MULTI_VIEW_EXCLUDED_KEYS)
            )
            outer_layout.addWidget(scroll_area, row, col)
"""Image Compare Viewer エントリポイント。

`uv run python -m image_compare` で起動する。

操作体系(マウスのみで完結させる方針):
- 左クリック(ドラッグなし): Fit⇔100%表示トグル
- 左ドラッグ: 全画像同期パン
- 右クリック: コンテキストメニュー表示(このタイルを削除・全画像を削除・
  オーバーレイ表示切替・Fit表示にリセット)
- ホイール: 全画像同期ズーム
"""
import math
import sys
from pathlib import Path

from PySide6.QtWidgets import (
    QApplication,
    QMainWindow,
    QLabel,
    QWidget,
    QGridLayout,
    QStackedWidget,
    QMenu,
)
from PySide6.QtCore import Qt, QPointF, QTimer
from PySide6.QtGui import QDragEnterEvent, QDropEvent

from image_compare.image_view import ImageTile
from image_compare.layout_rules import columns_for_count

# 仕様書4章: 対応画像形式
SUPPORTED_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

# 仕様書6章: 表示枚数の目標上限
MAX_IMAGES = 8

# ズームの倍率レンジ（極端な値による描画崩れ・無限拡大を防ぐ）
MIN_ZOOM = 0.1
MAX_ZOOM = 20.0
ZOOM_STEP = 1.15  # ホイール1クリックあたりの倍率変化

WINDOW_TITLE = "Image Compare Viewer"


class LeftClickOnlyMenu(QMenu):
    """右クリックでの項目選択を無効化したコンテキストメニュー。

    右クリックでメニューを開いた直後に、そのまま右ボタンで項目を選べてしまうと
    誤操作の原因になるため、右ボタンでのリリースは選択として扱わない。
    """

    def mouseReleaseEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.RightButton:
            event.ignore()
            return
        super().mouseReleaseEvent(event)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle(WINDOW_TITLE)
        self.resize(1000, 700)

        self.setAcceptDrops(True)

        self.image_paths: list[Path] = []
        self.tiles: list[ImageTile] = []

        # 全タイル共通のズーム倍率（仕様書10章: 全画像で常に同一の値を共有）
        self.shared_zoom: float = 1.0

        # 現在100%表示モードかどうか(Trueの場合は次の左クリックでFitに切り替わる)
        # ズーム・パン・リセット・新規ドロップ・削除などの操作が起きると
        # 必ずTrueに戻す(=次の左クリックは必ずFitになる)。左クリックのたびに
        # このフラグを反転させる。
        self.is_100_percent_mode: bool = True

        # ファイル名・倍率のオーバーレイ表示/非表示(右クリックメニューで全タイル共通にトグル)
        self.overlay_visible: bool = False

        # 画像タイルを並べるグリッドコンテナ
        self.grid_container = QWidget()
        self.grid_layout = QGridLayout(self.grid_container)
        self.grid_layout.setSpacing(4)
        self.grid_layout.setContentsMargins(4, 4, 4, 4)

        # プレースホルダ（0枚時に表示）
        self.placeholder = QLabel("ここに画像をドラッグ＆ドロップ")
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # setCentralWidgetで中央から外れたウィジェットはQtに破棄されることがあるため、
        # placeholderとgrid_containerを両方ともQStackedWidgetの子として常時保持し、
        # 表示の切り替えはQStackedWidget.setCurrentWidgetで行う
        # （setCentralWidgetの呼び直しはしない）。
        self.stack = QStackedWidget()
        self.stack.addWidget(self.placeholder)
        self.stack.addWidget(self.grid_container)
        self.setCentralWidget(self.stack)

        self._show_placeholder()

    def _show_placeholder(self) -> None:
        """画像が0枚のときのプレースホルダ表示に切り替える。"""
        self.stack.setCurrentWidget(self.placeholder)

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent) -> None:
        try:
            urls = event.mimeData().urls()
            dropped_paths = [Path(url.toLocalFile()) for url in urls if url.isLocalFile()]
        except Exception as exc:  # noqa: BLE001 - ドロップ内容の解釈失敗でクラッシュさせない
            print(f"[ERROR] ドロップ内容の解釈に失敗しました: {exc}")
            event.ignore()
            return

        # 既存表示中のファイルと重複しないように正規化パスの集合を用意する
        # (Windowsはパスの大小文字を区別しないため resolve() で正規化して比較する)
        existing_resolved = {p.resolve() for p in self.image_paths}

        valid_paths = []
        ignored_paths = []
        duplicate_paths = []
        for path in dropped_paths:
            try:
                is_valid = path.suffix.lower() in SUPPORTED_EXTENSIONS and path.is_file()
            except OSError as exc:
                print(f"[ERROR] ファイル確認中にエラー: {path} ({exc})")
                is_valid = False

            if not is_valid:
                ignored_paths.append(path)
                continue

            resolved = path.resolve()
            if resolved in existing_resolved:
                # 既に表示中、または今回のドロップ内で先に採用済みの重複ファイル
                duplicate_paths.append(path)
                continue

            existing_resolved.add(resolved)
            valid_paths.append(path)

        print(f"[DROP] 有効な画像: {len(valid_paths)}件")
        for p in valid_paths:
            print(f"  - {p}")
        if ignored_paths:
            print(f"[DROP] 無視したファイル: {len(ignored_paths)}件")
            for p in ignored_paths:
                print(f"  - {p}")
        if duplicate_paths:
            print(f"[DROP] 重複のため無視したファイル: {len(duplicate_paths)}件")
            for p in duplicate_paths:
                print(f"  - {p}")

        if not valid_paths:
            # 有効な画像が1枚も追加されない場合(全て重複や無効ファイル)は、
            # 現在のズーム・表示内容を変更しない
            event.acceptProposedAction()
            return

        self.image_paths.extend(valid_paths)

        # 仕様書6章: 上限を超えたら先頭MAX_IMAGES枚のみ採用
        if len(self.image_paths) > MAX_IMAGES:
            overflow = len(self.image_paths) - MAX_IMAGES
            print(f"[DROP] 上限{MAX_IMAGES}枚を超えたため、末尾{overflow}件を無視します")
            self.image_paths = self.image_paths[:MAX_IMAGES]

        # 仕様書9章: 新しい画像セットが追加されたら初期Fit状態(倍率1.0)に戻す
        self.shared_zoom = 1.0
        self.is_100_percent_mode = True

        self._rebuild_grid()

        event.acceptProposedAction()

    def _rebuild_grid(self) -> None:
        # 既存のタイルを一旦すべて取り除く
        while self.grid_layout.count():
            item = self.grid_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.setParent(None)
                widget.deleteLater()
        self.tiles = []

        # setRowStretch/setColumnStretchは一度設定すると自動では解除されないため、
        # 枚数が減って列数・行数が縮小した際に古い設定が残らないよう明示的にリセットする
        # （残ったままだと減った列/行が幅・高さを持ち続け、詰め直しが見た目に反映されない）
        for r in range(self.grid_layout.rowCount()):
            self.grid_layout.setRowStretch(r, 0)
        for c in range(self.grid_layout.columnCount()):
            self.grid_layout.setColumnStretch(c, 0)

        if not self.image_paths:
            self._show_placeholder()
            return

        columns = columns_for_count(len(self.image_paths))

        for index, path in enumerate(self.image_paths):
            row = index // columns
            col = index % columns
            try:
                tile = ImageTile(path)
            except Exception as exc:  # noqa: BLE001 - 1枚のタイル生成失敗で全体を巻き込まない
                print(f"[ERROR] タイル生成に失敗しました: {path} ({exc})")
                continue
            tile.zoom_factor = self.shared_zoom
            tile.overlay_visible = self.overlay_visible
            tile.on_wheel_zoom = self._handle_wheel_zoom
            tile.on_pan_drag = self._handle_pan_drag
            tile.on_left_clicked = self._handle_tile_left_clicked
            tile.on_context_menu_requested = self._handle_tile_context_menu
            self.grid_layout.addWidget(tile, row, col)
            self.tiles.append(tile)

        # 空いたマス（例: 3枚時の4マス目）は空白のままでよい仕様のため、
        # 明示的なストレッチだけ整えておく
        row_count = math.ceil(len(self.image_paths) / columns)
        for r in range(row_count):
            self.grid_layout.setRowStretch(r, 1)
        for c in range(columns):
            self.grid_layout.setColumnStretch(c, 1)

        self.stack.setCurrentWidget(self.grid_container)

    def _handle_wheel_zoom(self, source_tile: ImageTile, delta: int) -> None:
        """いずれかのタイル上でのホイール操作を、全タイルに同期反映する。

        各タイルは常に「枠の中心」を不動の基準点として拡大縮小する
        （画像側にパンでズレが生じていても、枠の中心自体は動かない）。
        そのため、既存のpan_offsetも倍率の変化比だけ一緒にスケールする。
        """
        old_zoom = self.shared_zoom
        if delta > 0:
            new_zoom = old_zoom * ZOOM_STEP
        else:
            new_zoom = old_zoom / ZOOM_STEP
        new_zoom = max(MIN_ZOOM, min(MAX_ZOOM, new_zoom))

        if new_zoom == old_zoom:
            return

        zoom_ratio = new_zoom / old_zoom

        # ホイール操作でズームすると「Fitでも、ちょうど100%でもない」状態になるため、
        # 次に左クリックしたときは必ずFitから開始するようにしておく
        self.is_100_percent_mode = True

        self.shared_zoom = new_zoom
        for tile in self.tiles:
            tile.zoom_factor = self.shared_zoom
            tile.pan_offset = tile.pan_offset * zoom_ratio
            tile.update()

    def _handle_pan_drag(self, dx: float, dy: float) -> None:
        """いずれかのタイルでのドラッグ移動量を、全タイルに同期反映する。

        仕様書11章: 移動量はピクセル単位でよく、正規化・相対座標化は不要。
        """
        # パン操作を行うと「ちょうど100%」の位置関係ではなくなるため、
        # 次に左クリックしたときは必ずFitから開始するようにしておく
        self.is_100_percent_mode = True

        delta = QPointF(dx, dy)
        for tile in self.tiles:
            tile.pan_offset = tile.pan_offset + delta
            tile.update()

    def _handle_tile_left_clicked(self, clicked_tile: ImageTile) -> None:
        """左クリック(ドラッグなし)でFit⇔100%表示をトグルする。

        clicked_tileを基準に、全タイル共通のzoom_factorを切り替える。
        画像サイズが異なるタイルが混在する場合、他タイルの見た目上の%は
        clicked_tile基準の値からズレるが、これはホイールでの同期ズームと
        同じ仕様(全タイルでzoom_factorという1つの値を共有する)であり、
        混在を前提としない運用では実質的に問題にならない。
        """
        base_scale = clicked_tile.fit_scale()
        if base_scale <= 0:
            return

        if self.is_100_percent_mode:
            # 100% -> Fit に戻す（Fitリセットと同じ状態にする）
            new_zoom = 1.0
            self.is_100_percent_mode = False
            self.shared_zoom = new_zoom
            for tile in self.tiles:
                tile.zoom_factor = new_zoom
                tile.pan_offset = QPointF(0.0, 0.0)
                tile.update()
            return

        # Fit -> 100% (画像の実ピクセルサイズ) にする
        new_zoom = 1.0 / base_scale
        self.is_100_percent_mode = True
        self.shared_zoom = new_zoom
        for tile in self.tiles:
            tile.zoom_factor = new_zoom
            tile.update()

    def _handle_tile_context_menu(self, clicked_tile: ImageTile, global_pos: QPointF) -> None:
        """右クリックでコンテキストメニューを表示する。"""
        menu = LeftClickOnlyMenu(self)

        remove_action = menu.addAction("この画像を削除")
        clear_action = menu.addAction("すべての画像を削除")
        menu.addSeparator()
        overlay_label = "ファイル名/倍率の表示をオフ" if self.overlay_visible else "ファイル名/倍率の表示をオン"
        overlay_action = menu.addAction(overlay_label)
        menu.addSeparator()
        reset_action = menu.addAction("Fit表示にリセット")

        # メニュー表示中は全タイルのマウス入力を無視させる。
        # 加えて、メニュー外をクリックして閉じた場合、そのクリックは
        # 「メニューを閉じる」動作として消費された後、直後に新しい独立した
        # クリックイベントとして背後のタイルに配送されることがある
        # (menu.exec()が返ってきた"後"に mousePressEvent が発生する)。
        # そのため、メニューが閉じた直後も少しの間 suppress_input を
        # 維持し、閉じるためのクリックがトグルとして扱われないようにする。
        for tile in self.tiles:
            tile.force_reset_drag_state()
            tile.suppress_input = True
        chosen = menu.exec(global_pos.toPoint())
        QTimer.singleShot(100, self._clear_all_suppress_input)

        if chosen == remove_action:
            self.remove_tile(clicked_tile)
        elif chosen == clear_action:
            self.clear_all_tiles()
        elif chosen == overlay_action:
            self.toggle_overlay()
        elif chosen == reset_action:
            self.reset_view()

    def _clear_all_suppress_input(self) -> None:
        for tile in self.tiles:
            tile.suppress_input = False

    def reset_view(self) -> None:
        """仕様書12章: Fit/Reset。全画像の倍率・位置を初期状態に戻す。"""
        self.shared_zoom = 1.0
        self.is_100_percent_mode = True
        for tile in self.tiles:
            tile.zoom_factor = 1.0
            tile.pan_offset = QPointF(0.0, 0.0)
            tile.update()

    def remove_tile(self, target_tile: ImageTile) -> None:
        """指定した画像を表示から取り除く（ファイル自体は削除しない）。"""
        target_path = target_tile.image_path
        try:
            self.image_paths.remove(target_path)
        except ValueError:
            # 同一パスが重複ドロップされていた場合など、念のため無視して継続
            pass
        # 削除後も「次の左クリックは必ずFitから開始する」を一貫させる
        self.is_100_percent_mode = True
        self._rebuild_grid()

    def toggle_overlay(self) -> None:
        """各タイルのファイル名・倍率オーバーレイの表示/非表示を切り替える。"""
        self.overlay_visible = not self.overlay_visible
        for tile in self.tiles:
            tile.overlay_visible = self.overlay_visible
            tile.update()

    def clear_all_tiles(self) -> None:
        """表示中の画像をすべてクリアする（ファイルは削除しない）。"""
        if not self.image_paths:
            return
        self.image_paths = []
        self.shared_zoom = 1.0
        self.is_100_percent_mode = True
        self._rebuild_grid()


def main() -> None:
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

"""個別の画像表示領域。

倍率(zoom_factor)とオフセット(pan_offset)は MainWindow が一元管理し、
このクラスは「指示された通りに描画する」「操作イベントを通知する」だけの
受動的な部品とする。
(仕様書15章: 重複更新防止のため、状態変更の発生源を1箇所に絞る)

操作体系(マウスのみで完結させる方針):
- 左クリック(ドラッグなし): Fit⇔100%表示トグル
- 左ドラッグ: 全画像同期パン
- 右クリック: コンテキストメニュー表示(このタイルを削除・すべてのタイルを削除・
  オーバーレイ表示切替)。Qt標準のcontextMenuEvent経由で扱い、
  左クリックの処理経路とは完全に分離している。
- ホイール: 全画像同期ズーム
"""
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPixmap, QPainter, QWheelEvent, QMouseEvent
from PySide6.QtWidgets import QFrame


class ImageTile(QFrame):
    """1枚の画像を表示するタイル。"""

    def __init__(self, image_path: Path) -> None:
        super().__init__()
        self.image_path = image_path

        self.setFrameShape(QFrame.Shape.Box)
        self.setLineWidth(1)

        self._original_pixmap: QPixmap | None = None
        self.load_error = False

        # 表示状態: MainWindowから設定される
        # zoom_factor: 1.0 = Fit状態を基準とした倍率
        # pan_offset: Fit状態の中心からの画面ピクセル単位のズレ
        self.zoom_factor: float = 1.0
        self.pan_offset: QPointF = QPointF(0.0, 0.0)

        # オーバーレイ(ファイル名・倍率)の表示/非表示。右クリックメニューで全タイル共通に切り替える。
        self.overlay_visible: bool = False

        # ホイール操作をMainWindowに伝えるコールバック
        # 引数: (このタイル, delta方向(+1/-1))
        self.on_wheel_zoom: Optional[Callable[["ImageTile", int], None]] = None

        # ドラッグ(パン)操作をMainWindowに伝えるコールバック
        # 引数: (移動量dx, dy) ピクセル単位
        self.on_pan_drag: Optional[Callable[[float, float], None]] = None
        # 左クリック(ドラッグなし)をMainWindowに伝えるコールバック(Fit⇔100%トグル用)
        self.on_left_clicked: Optional[Callable[["ImageTile"], None]] = None
        # 右クリックをMainWindowに伝えるコールバック(コンテキストメニュー表示用)
        # 引数: (このタイル, 画面上でのグローバル座標)
        # Qt標準のcontextMenuEventから呼ばれるため、右クリックのpress/releaseが
        # 完結した後の、独立したイベントとして安全に発火する
        # (mousePressEvent側で直接menu.exec()を呼ぶと、右クリックの
        #  イベント処理そのものがメニューを閉じるまで完了しないため、
        #  左クリック等の後続イベントと処理が絡み合いやすくなる)
        self.on_context_menu_requested: Optional[Callable[["ImageTile", "QPointF"], None]] = None

        self._is_dragging = False
        self._last_mouse_pos: Optional[QPointF] = None
        self._drag_moved = False

        self._load_image()

    def _load_image(self) -> None:
        # 仕様書16章: 壊れた画像・読み込み不能な画像・存在しないファイルで
        # クラッシュしないよう、想定外の例外も含めて広く捕捉する。
        try:
            if not self.image_path.is_file():
                self.load_error = True
                return
            pixmap = QPixmap(str(self.image_path))
            if pixmap.isNull():
                self.load_error = True
            else:
                self._original_pixmap = pixmap
        except Exception as exc:  # noqa: BLE001 - 個人利用ツールのため広く捕捉して継続を優先
            print(f"[ERROR] 画像の読み込みに失敗しました: {self.image_path} ({exc})")
            self.load_error = True

    def has_image(self) -> bool:
        return self._original_pixmap is not None

    def image_size(self):
        if self._original_pixmap is None:
            return None
        return self._original_pixmap.size()

    def fit_scale(self) -> float:
        """このタイルの領域に画像を収めるための倍率(Fit時の基準倍率)。"""
        if self._original_pixmap is None or self.width() <= 0 or self.height() <= 0:
            return 1.0
        pw, ph = self._original_pixmap.width(), self._original_pixmap.height()
        if pw <= 0 or ph <= 0:
            return 1.0
        scale_w = self.width() / pw
        scale_h = self.height() / ph
        return min(scale_w, scale_h)

    def wheelEvent(self, event: QWheelEvent) -> None:
        if self.on_wheel_zoom is None:
            event.ignore()
            return
        wheel_delta = event.angleDelta().y()
        if wheel_delta == 0:
            # タッチパッドなど、垂直方向のホイール量が取得できない入力デバイスでは
            # 意図せずズームアウトと誤判定しないよう、何もせず無視する
            event.ignore()
            return
        delta = 1 if wheel_delta > 0 else -1
        self.on_wheel_zoom(self, delta)
        event.accept()

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._is_dragging = True
            self._drag_moved = False
            self._last_mouse_pos = event.position()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._is_dragging and self._last_mouse_pos is not None:
            current_pos = event.position()
            dx = current_pos.x() - self._last_mouse_pos.x()
            dy = current_pos.y() - self._last_mouse_pos.y()
            if dx != 0 or dy != 0:
                self._drag_moved = True
                if self.on_pan_drag is not None:
                    self.on_pan_drag(dx, dy)
            self._last_mouse_pos = current_pos
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._is_dragging:
            self._is_dragging = False
            self._last_mouse_pos = None
            # ドラッグ移動がなければ「クリック」とみなし、Fit⇔100%トグルを発火する
            if not self._drag_moved and self.on_left_clicked is not None:
                self.on_left_clicked(self)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def contextMenuEvent(self, event) -> None:
        """Qt標準のコンテキストメニュー通知。右クリックはここで一元的に扱う。

        mousePressEventの中で直接menu.exec()を呼ぶと、右クリックという
        1つのマウスイベントの処理そのものがメニューが閉じるまで完了せず、
        その後の左クリック等のイベント配送と絡み合う原因になっていた。
        contextMenuEventはQtが「右クリックの一連の操作(press+release)が
        完結した後」に独立して発火させる通知のため、ここでメニューを
        表示すれば、左クリックの処理と経路が交わらない。
        """
        if self.on_context_menu_requested is not None:
            self.on_context_menu_requested(self, event.globalPos())
        event.accept()

    def paintEvent(self, event) -> None:
        super().paintEvent(event)

        if self._original_pixmap is None:
            if self.load_error:
                painter = QPainter(self)
                painter.setRenderHint(QPainter.RenderHint.Antialiasing)
                painter.drawText(
                    self.rect(),
                    Qt.AlignmentFlag.AlignCenter,
                    f"読み込み失敗:\n{self.image_path.name}",
                )
                self._draw_overlay(painter, percent=None)
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        base_scale = self.fit_scale()
        effective_scale = base_scale * self.zoom_factor

        pw = self._original_pixmap.width() * effective_scale
        ph = self._original_pixmap.height() * effective_scale

        # 領域中心 + パンオフセットを描画中心とする
        center_x = self.width() / 2 + self.pan_offset.x()
        center_y = self.height() / 2 + self.pan_offset.y()

        target_rect = QRectF(
            center_x - pw / 2,
            center_y - ph / 2,
            pw,
            ph,
        )
        painter.drawPixmap(target_rect, self._original_pixmap, QRectF(self._original_pixmap.rect()))

        self._draw_overlay(painter, percent=effective_scale * 100)

    def _draw_overlay(self, painter: QPainter, percent: float | None) -> None:
        """タイル上部にファイル名と倍率(%)を半透明の帯で表示する(右クリックメニューで切り替え)。"""
        if not self.overlay_visible:
            return

        text = self.image_path.name
        if percent is not None:
            text = f"{text}  ({percent:.0f}%)"

        painter.save()

        metrics = painter.fontMetrics()
        text_height = metrics.height()
        padding = 4
        bar_height = text_height + padding * 2

        bar_rect = QRectF(0, 0, self.width(), bar_height)
        painter.setOpacity(0.55)
        painter.fillRect(bar_rect, Qt.GlobalColor.black)
        painter.setOpacity(1.0)

        painter.setPen(Qt.GlobalColor.white)
        text_rect = QRectF(padding, 0, self.width() - padding * 2, bar_height)
        elided = metrics.elidedText(text, Qt.TextElideMode.ElideMiddle, int(text_rect.width()))
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, elided)

        painter.restore()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update()
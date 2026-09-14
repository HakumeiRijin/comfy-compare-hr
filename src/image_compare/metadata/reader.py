"""画像からテキストメタデータを読み取る。

現時点ではPNGのtEXt/iTXt/zTXtチャンク(Pillowのimg.text)のみを対象とする。
ComfyUI等が書き込む生データをそのまま返し、整形・解釈は行わない。

JPEG等のEXIF対応、HEIF等の追加パッケージが必要な形式は対象外
(inspect_metadata.pyでの調査により、当面はこの範囲で十分と判断した)。
"""
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError


def read_text_metadata(image_path: Path) -> Optional[dict[str, str]]:
    """画像パスを受け取り、PNGのテキストメタデータを辞書で返す。

    見つからない場合、または読み取りに失敗した場合はNoneを返す
    (仕様書16章の方針にならい、失敗してもクラッシュさせず呼び出し元に
    委ねる)。
    """
    try:
        with Image.open(image_path) as img:
            text_data = getattr(img, "text", None)
    except (UnidentifiedImageError, OSError):
        return None

    if not text_data:
        return None

    return dict(text_data)
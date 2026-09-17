"""画像からテキストメタデータを読み取る。

PNGのtEXt/iTXt/zTXtチャンク(Pillowのimg.text)と、JPEG等のEXIFデータの
両方を対象とする。PNGは生データをそのまま返し、整形・解釈は行わない。
EXIFはPillow標準のExifTagsでタグ名に変換するところまでを行う。

対応範囲は「Pillow単体で読み取れるもの」までと決めている。IPTC・XMP・
ICCプロファイルといった、EXIFとは別の規格のメタデータ(実写真の
プロフェッショナル向けメタデータや、Adobe系ソフトの拡張メタデータなど)
は対象外。これらをフルに読み取るには追加のライブラリが必要になり、
ComfyUIが実際に書き込むのはPNGのtEXtチャンクのみであるため、当初の
目的(ComfyUI画像のメタデータ閲覧)には不要と判断した。
MakerNoteのようなメーカー独自領域や、HEIF等の追加パッケージが必要な
形式も同様に対象外。
"""
from pathlib import Path
from typing import Optional

from PIL import Image, UnidentifiedImageError
from PIL.ExifTags import TAGS


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


def read_exif_metadata(image_path: Path) -> Optional[dict[str, str]]:
    """画像パスを受け取り、EXIFメタデータをタグ名の辞書で返す。

    Pillow標準のPIL.ExifTags.TAGSで、数値のタグIDを人間が読める
    タグ名(Make, Model, DateTimeOriginal等)に変換する。
    値がbytes型の場合は、そのままでは表示できないため文字列に変換する
    (デコードできない場合はrepr()で代用し、クラッシュを避ける)。

    タグ名が対応表にないID(メーカー独自のMakerNote関連等)は、
    数値IDのままキーにする(解釈は行わず、存在だけ分かるようにする)。
    """
    try:
        with Image.open(image_path) as img:
            exif_data = img.getexif()
    except (UnidentifiedImageError, OSError):
        return None

    if not exif_data:
        return None

    result: dict[str, str] = {}
    for tag_id, value in exif_data.items():
        tag_name = TAGS.get(tag_id, str(tag_id))

        if isinstance(value, bytes):
            try:
                value = value.decode("utf-8", errors="replace")
            except Exception:  # noqa: BLE001 - デコード方式によらず表示だけは継続する
                value = repr(value)

        result[tag_name] = str(value)

    return result if result else None
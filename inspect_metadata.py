"""画像に埋め込まれたテキストメタデータを覗くための、使い捨ての調査スクリプト。

ComfyUI等が書き込むPNGのtEXt/iTXtチャンクの中身がどんな形式か、
実装前にざっと確認するためのもの。アプリ本体には組み込まない。

使い方:
    uv run python inspect_metadata.py "対象画像のパス"
"""
import sys
from pathlib import Path

from PIL import Image


def main() -> None:
    if len(sys.argv) != 2:
        print("使い方: uv run python inspect_metadata.py <画像パス>")
        sys.exit(1)

    path = Path(sys.argv[1])
    if not path.is_file():
        print(f"ファイルが見つかりません: {path}")
        sys.exit(1)

    with Image.open(path) as img:
        print(f"形式: {img.format}")
        print(f"サイズ: {img.size}")
        print(f"モード: {img.mode}")
        print()

        # PNGのtEXt/iTXt/zTXtチャンクは img.text に辞書として格納される
        # (JPEGなど他の形式では空になることが多い)
        text_data = getattr(img, "text", {})

        if not text_data:
            print("テキストメタデータは見つかりませんでした。")
            print("(img.info の中身も念のため表示します)")
            for key, value in img.info.items():
                print(f"  [info] {key}: {repr(value)[:200]}")
            return

        print(f"見つかったテキストキー: {list(text_data.keys())}")
        print()

        for key, value in text_data.items():
            print(f"=== キー: {key} ===")
            print(f"文字数: {len(value)}")
            # 長すぎる場合は先頭だけ表示する
            preview = value[:1000]
            print(preview)
            if len(value) > 1000:
                print(f"... (以下省略、全体は{len(value)}文字)")
            print()


if __name__ == "__main__":
    main()
# ComfyCompare-HR

Windows 11専用・個人利用の軽量画像比較ビューアです。

複数の画像生成結果（主にComfyUIの出力画像）を1つのウィンドウ内にタイル表示し、
同一箇所を拡大・移動しながら比較できます。あわせて、画像に埋め込まれたメタデータ
（PNGのテキストチャンク、EXIF）をその場で確認できます。

「画像編集ソフト」ではなく「画像比較ツール」というコンセプトのもとに作っています。
閲覧中に意図しない加工や編集をしてしまわないよう、画像ファイルは常に読み取り専用で
扱い、機能もあえてシンプルに絞っています。

元々は自分用に作ったツールですが、同じようなものを探している人が
**自己責任で**使えるように公開しています。動作保証や積極的なサポートは
行っていません。詳しい経緯は [CHANGELOG.md](CHANGELOG.md) を参照してください。

## できること

- Explorerからのドラッグ＆ドロップで画像を追加（最大8枚）
- 全画像同期のズーム・パン（同じ箇所を並べて見比べる）
- 左クリックでFit表示⇔100%表示を切り替え
- 右クリックメニューから、画像の削除・オーバーレイ表示切替・メタデータ表示
- PNGのテキストメタデータ（ComfyUIの`prompt`/`workflow`など）をJSON整形して表示
- JPEG等のEXIFメタデータ（撮影日時・機種名など）を表示
- 表示中の全画像のメタデータを、画像と同じ配置で一覧表示

操作方法や実装の詳細な経緯は [CHANGELOG.md](CHANGELOG.md) にまとめてあります。

## 対象環境

- Windows 11（他の環境での動作は確認していません）
- Python 3.10以上

## インストールと起動

[uv](https://docs.astral.sh/uv/) がインストールされていれば、依存関係のインストールと
実行を一度に行えます。

```powershell
git clone https://github.com/HakumeiRijin/comfy-compare-hr.git
cd comfy-compare-hr
uv run python -m image_compare
```

以後は `run.bat` をダブルクリックするだけで起動できます。

## 依存ライブラリ

- [PySide6-Essentials](https://pypi.org/project/PySide6-Essentials/)（Qt for Python, LGPLv3）
- [Pillow](https://python-pillow.org/)（画像・メタデータ処理, MIT License）

いずれも通常のパッケージインストール（動的リンク）の範囲で利用しています。

## 対応していないこと

- 画像編集・トリミング・回転・色調補正などの加工機能
- ファイル名変更・削除・フォルダ管理
- ネットワーク通信、クラウド連携
- HEIF等の追加パッケージが必要な画像形式
- IPTC・XMP・ICCプロファイルなど、EXIF以外のメタデータ規格

## ライセンス

[MIT License](LICENSE)
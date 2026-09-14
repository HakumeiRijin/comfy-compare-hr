"""枚数→列数の対応表。

固定値の対応表であり、動的な最適化アルゴリズムは実装しない。
主用途が縦長画像の比較であるため、3枚のときは2列(1枚だけ2行目に
余る配置)ではなく、3枚とも横一列に並べて同じ大きさで見せる。
"""


def columns_for_count(count: int) -> int:
    """画像枚数に対応する列数を返す。"""
    if count <= 1:
        return 1
    if count == 3:
        return 3
    if count <= 4:
        return 2
    if count <= 6:
        return 3
    return 4  # 7〜8枚
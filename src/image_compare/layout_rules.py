"""仕様書7章: 枚数→列数の対応表。

固定値の対応表であり、動的な最適化アルゴリズムは実装しない。
"""


def columns_for_count(count: int) -> int:
    """画像枚数に対応する列数を返す。"""
    if count <= 1:
        return 1
    if count <= 4:
        return 2
    if count <= 6:
        return 3
    return 4  # 7〜8枚

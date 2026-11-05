# -*- coding: utf-8 -*-
"""四个题目给定测试用例的一键回归。

运行：python run_tests.py
每个用例打印输入摘要、程序输出、预期输出与 PASS/FAIL，全部通过退出码为 0。
"""

from __future__ import annotations

import sys

from q1_maze import find_maze_path, render_path
from q2_weighted import min_cost_weighted
from q3_alphabeta import SearchStats, TreeNode, alphabeta, build_tree, minimax
from q4_treasure_game import best_first_move, format_matrix, initial_state, DIST

FAILURES = 0


def check(name: str, got, expected, equal=None) -> None:
    global FAILURES
    if expected is None:
        ok = got is not None
    elif name.startswith("题目一") and isinstance(expected, tuple):
        # 可能存在多条最短路径：校验是一条合法最短路，而非逐坐标相等
        ok = _valid_path(got, expected)
    else:
        ok = got == expected
    print(f"  程序输出: {got}")
    expect_desc = (
        "一条长度为 8 的合法最短路径"
        if name.startswith("题目一") and isinstance(expected, tuple)
        else expected
    )
    print(f"  预期输出: {expect_desc}")
    print(f"  结果: {'PASS' if ok else 'FAIL'}\n")
    if not ok:
        FAILURES += 1


def _valid_path(path, case) -> bool:
    start, end, grid, expect_len = case
    if not path or path[0] != start or path[-1] != end or len(path) != expect_len:
        return False
    for i in range(1, len(path)):
        r, c = path[i]
        pr, pc = path[i - 1]
        if abs(r - pr) + abs(c - pc) != 1:          # 只能上下左右走一步
            return False
        if grid[r][c] == "X":                        # 不能穿障碍
            return False
    return True


def test_q1() -> None:
    print("=" * 60)
    print("题目一：迷宫寻路（A* + 曼哈顿启发）")
    start, end = (0, 0), (3, 4)
    grid = [
        ["S", ".", ".", "X", "."],
        [".", "X", ".", ".", "."],
        [".", "X", ".", "X", "."],
        [".", ".", ".", "X", "E"],
        ["X", "X", ".", ".", "."],
    ]
    path = find_maze_path(start, end, grid)
    print(render_path(grid, path))
    check("题目一", path, (start, end, grid, 8))

    # 无解用例：终点被障碍围死
    grid_no = [["S", "X"], ["X", "E"]]
    path_no = find_maze_path((0, 0), (1, 1), grid_no)
    check("题目一(无解)", path_no, [])


def test_q2() -> None:
    print("=" * 60)
    print("题目二：加权地形（A* 最小代价）")
    start, end = (0, 0), (4, 4)
    grid = [
        ["S", 1, 1, 8, 1],
        [1, 8, 3, 1, 1],
        [1, 8, 1, 8, 1],
        [1, 1, 1, 8, 1],
        [8, 8, 1, 1, "E"],
    ]
    cost = min_cost_weighted(start, end, grid)
    check("题目二", cost, 7)

    # 无解用例
    grid_no = [["S", "X"], ["X", "E"]]
    check("题目二(无解)", min_cost_weighted((0, 0), (1, 1), grid_no), -1)


def test_q3() -> None:
    print("=" * 60)
    print("题目三：极大极小博弈树（Minimax / Alpha-Beta）")
    spec = {
        "is_maximizing_player": True,
        "children": [
            {
                "is_maximizing_player": False,
                "children": [
                    {"is_maximizing_player": True,
                     "children": [{"value": 3}, {"value": 5}]},
                    {"is_maximizing_player": True,
                     "children": [{"value": 6}, {"value": 9}]},
                ],
            },
            {
                "is_maximizing_player": False,
                "children": [
                    {"is_maximizing_player": True,
                     "children": [{"value": 6}, {"value": 9}]},
                    {"is_maximizing_player": True,
                     "children": [{"value": 1}, {"value": 2}]},
                ],
            },
        ],
    }
    root = build_tree(spec)
    s1, s2 = SearchStats(), SearchStats()
    v_mm = minimax(root, True, s1)
    v_ab = alphabeta(root, True, float("-inf"), float("inf"), s2)
    print(f"  Minimax    : value={v_mm}, visited={s1.visited}, leaves={s1.leaves}")
    print(f"  Alpha-Beta : value={v_ab}, visited={s2.visited}, leaves={s2.leaves}, pruned={s2.pruned}")
    check("题目三(Minimax)", v_mm, 5)
    check("题目三(Alpha-Beta)", v_ab, 5)


def test_q4() -> None:
    print("=" * 60)
    print("题目四：竞争环境下的宝藏分配（综合题）")
    print("  6x6 距离矩阵（A* 两两最小代价）：")
    print(format_matrix(DIST))
    for depth, expect_t, expect_v in ((2, "T2", -1), (4, "T3", 3)):
        for use_ab, tag in ((False, "Minimax"), (True, "Alpha-Beta")):
            t, v, stats, mv = best_first_move(initial_state(), depth, use_ab)
            print(f"  H={depth} {tag:<10}: best_target={t}, best_value={v}, "
                  f"nodes={stats.nodes}, evals={stats.evals}, pruned={stats.pruned}")
            print(f"      各首步 U: {mv}")
            check(f"题目四(H={depth},{tag})", (t, v), (expect_t, expect_v))


def main() -> None:
    test_q1()
    test_q2()
    test_q3()
    test_q4()
    print("=" * 60)
    print("全部通过 ✔" if FAILURES == 0 else f"共 {FAILURES} 项失败 ✘")
    sys.exit(0 if FAILURES == 0 else 1)


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""题目一：迷宫寻路。

网格中 'S' 起点、'E' 终点、'.' 可通过、'X' 障碍。
只能上下左右移动，每步代价 1。用 A*（曼哈顿启发）求最短路径坐标序列，
无解返回空列表。
"""

from __future__ import annotations

from typing import Callable, List, Tuple

from astar import SearchStats, astar, manhattan

Coord = Tuple[int, int]
Grid = List[List[str]]

BLOCKED = "X"


def in_bounds(grid: Grid, p: Coord) -> bool:
    return 0 <= p[0] < len(grid) and 0 <= p[1] < len(grid[0])


def passable(grid: Grid, p: Coord) -> bool:
    return in_bounds(grid, p) and grid[p[0]][p[1]] != BLOCKED


def four_neighbors(grid: Grid) -> Callable[[Coord], List[Coord]]:
    """生成四方向邻居函数，按 上/下/左/右 固定顺序返回（可复现）。"""

    def neighbors(p: Coord) -> List[Coord]:
        r, c = p
        out = []
        for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if passable(grid, q):
                out.append(q)
        return out

    return neighbors


def find_maze_path(
    start: Coord,
    end: Coord,
    grid: Grid,
    heuristic: str = "manhattan",
    stats: SearchStats | None = None,
    keep_log: bool = False,
) -> List[Coord]:
    """A* 求起点到终点的最短路径。

    heuristic: "manhattan" 用曼哈顿距离；"zero" 退化为 Dijkstra（h=0）。
    返回按顺序包含起点与终点的坐标列表；无解返回 []。
    """

    if not passable(grid, start) or not passable(grid, end):
        return []

    h_fn = (lambda p: manhattan(p, end)) if heuristic == "manhattan" else (lambda p: 0)
    path, _ = astar(
        start,
        end,
        four_neighbors(grid),
        cost_fn=lambda _a, _b: 1,  # 每移动一格代价为 1
        heuristic_fn=h_fn,
        stats=stats,
        keep_log=keep_log,
    )
    return path if path is not None else []


def render_path(grid: Grid, path: List[Coord]) -> str:
    """把路径画回网格，便于报告展示与人工核对。"""
    canvas = [row[:] for row in grid]
    for p in path:
        if canvas[p[0]][p[1]] == ".":
            canvas[p[0]][p[1]] = "*"
    return "\n".join(" ".join(row) for row in canvas)

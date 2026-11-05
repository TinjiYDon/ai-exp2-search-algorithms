# -*- coding: utf-8 -*-
"""题目二：加权地形。

地图由地形权值组成，进入某格的代价等于该格权值（如 1=平原，3=沼泽）。
按题目规定：起点 S 无进入代价，终点 E 可视为 0（进入 E 不收费）。
用 A* 求最小总代价，无解返回 -1。

启发函数可采纳性（报告讨论点）：
- 地形权值最小为 1，若忽略 E=0 的规定，曼哈顿距离 h = |Δr|+|Δc| 是
  每步至少花 1 的下界，看似可采纳；
- 但最后一步进入 E 实际代价为 0，严格地讲 h = manhattan 会高估真实
  剩余代价最多 1（例：与 E 相邻时 h=1 而真实代价为 0），因此不再是
  可采纳启发；
- 修正：h'(n) = max(manhattan(n, E) - 1, 0) * min_cost，其中 min_cost=1。
  任何 L 步路径的代价 >= (L-1)*1 + 0，故 h' 永不高估，可采纳。
本模块两种启发都实现，实验部分对比二者扩展节点数与结果一致性。
"""

from __future__ import annotations

from typing import Callable, List, Tuple, Union

from astar import SearchStats, astar, manhattan

Coord = Tuple[int, int]
Cell = Union[str, int]
Grid = List[List[Cell]]

START = "S"
END = "E"
BLOCKED = "X"


def enter_cost(grid: Grid, p: Coord) -> int:
    """进入 p 格的代价：E=0，S=1（防止负回环，最优路径不会回到 S），X 不可通行。"""
    v = grid[p[0]][p[1]]
    if v == END:
        return 0
    if v == START:
        return 1
    return int(v)


def in_bounds(grid: Grid, p: Coord) -> bool:
    return 0 <= p[0] < len(grid) and 0 <= p[1] < len(grid[0])


def passable(grid: Grid, p: Coord) -> bool:
    return in_bounds(grid, p) and grid[p[0]][p[1]] != BLOCKED


def four_neighbors(grid: Grid) -> Callable[[Coord], List[Coord]]:
    def neighbors(p: Coord) -> List[Coord]:
        r, c = p
        out = []
        for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
            if passable(grid, q):
                out.append(q)
        return out

    return neighbors


def make_heuristic(grid: Grid, end: Coord, kind: str) -> Callable[[Coord], int]:
    """构造加权地形的启发函数。

    kind:
      "zero"           h=0，退化为 Dijkstra；
      "manhattan"      h=曼哈顿（朴素，因 E=0 而可能高估 1）；
      "manhattan_fix"  h=max(曼哈顿-1,0)*最小地形权值，严格可采纳。
    """
    if kind == "zero":
        return lambda p: 0
    digit_cells = [
        int(grid[r][c])
        for r in range(len(grid))
        for c in range(len(grid[0]))
        if grid[r][c] not in (START, END, BLOCKED)
    ]
    min_cost = min(digit_cells) if digit_cells else 1
    if kind == "manhattan":
        return lambda p: manhattan(p, end) * min_cost
    if kind == "manhattan_fix":
        return lambda p: max(manhattan(p, end) - 1, 0) * min_cost
    raise ValueError(f"unknown heuristic: {kind}")


def min_cost_weighted(
    start: Coord,
    end: Coord,
    grid: Grid,
    heuristic: str = "manhattan_fix",
    stats: SearchStats | None = None,
    keep_log: bool = False,
) -> int:
    """A* 求 start 到 end 的最小总代价；无解返回 -1。"""

    if not passable(grid, start) or not passable(grid, end):
        return -1

    _, cost = astar(
        start,
        end,
        four_neighbors(grid),
        cost_fn=lambda _a, b: enter_cost(grid, b),
        heuristic_fn=make_heuristic(grid, end, heuristic),
        stats=stats,
        keep_log=keep_log,
    )
    return int(cost) if cost != float("inf") else -1

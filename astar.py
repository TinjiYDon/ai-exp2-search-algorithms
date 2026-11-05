# -*- coding: utf-8 -*-
"""通用 A* 搜索模块（题目一、二、四共用）。

设计要点
--------
- 状态：网格坐标 (row, col)。具体问题通过回调注入：
    neighbors_fn(pos)  -> 相邻可通行坐标
    cost_fn(a, b)      -> 从 a 进入 b 的代价
    heuristic_fn(pos)  -> 到终点的启发估计 h
- g(n)：起点到 n 的累计实际代价；f(n) = g(n) + h(n)。
- 优先队列：heapq 最小堆，按 f 弹出；用自增计数器做平局裁决（先入先出），
  保证结果可复现。
- 关闭表记录最优 g：若之后以更小的 g 再次到达同一状态，允许重新入堆
  （可采纳启发下不会发生，但保留该逻辑使实现对非一致启发也安全）。
- SearchStats 记录搜索过程指标：扩展节点数、生成节点数、最大 OPEN 规模，
  供实验报告做启发函数效率对比。
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from itertools import count
from typing import Callable, Dict, Hashable, List, Optional, Tuple

State = Hashable


@dataclass
class SearchStats:
    """A* 搜索过程统计。"""

    expanded: int = 0      # 从 OPEN 弹出并扩展的节点数
    generated: int = 0     # 被生成（首次入堆）的节点数
    max_open: int = 0      # OPEN 表历史最大长度
    reopened: int = 0      # 以更优 g 重新打开的次数
    log: List[Tuple[State, float, float, float]] = field(default_factory=list)
    # log 中每条记录为 (state, g, h, f)，记录扩展顺序，便于报告展示过程


def astar(
    start: State,
    goal: State,
    neighbors_fn: Callable[[State], List[State]],
    cost_fn: Callable[[State, State], float],
    heuristic_fn: Callable[[State], float],
    stats: Optional[SearchStats] = None,
    keep_log: bool = False,
) -> Tuple[Optional[List[State]], float]:
    """运行 A*，返回 (路径, 最小代价)。无解返回 (None, inf)。"""

    if start == goal:
        return [start], 0.0

    tie = count()  # 平局裁决计数器：f 相同则先扩展先入堆者
    g_best: Dict[State, float] = {start: 0.0}
    parent: Dict[State, State] = {}
    # 堆元素：(f, 平局序号, 状态)
    open_heap: List[Tuple[float, int, State]] = [(heuristic_fn(start), next(tie), start)]
    closed: set = set()
    generated = 1

    while open_heap:
        if stats is not None:
            stats.max_open = max(stats.max_open, len(open_heap))
        f, _, node = heapq.heappop(open_heap)
        if node in closed:
            continue  # 该状态已按最优 g 扩展过，堆中的是过期副本
        g = g_best[node]

        if node == goal:
            path = [node]
            while node in parent:
                node = parent[node]
                path.append(node)
            path.reverse()
            if stats is not None:
                stats.generated = generated
            return path, g

        closed.add(node)
        if stats is not None:
            stats.expanded += 1
            if keep_log:
                stats.log.append((node, g, f - g, f))

        for nxt in neighbors_fn(node):
            if nxt in closed:
                continue
            g_new = g + cost_fn(node, nxt)
            old = g_best.get(nxt)
            if old is not None and g_new >= old:
                continue
            if old is not None and stats is not None:
                stats.reopened += 1
            g_best[nxt] = g_new
            parent[nxt] = node
            if old is None:
                generated += 1
            heapq.heappush(open_heap, (g_new + heuristic_fn(nxt), next(tie), nxt))

    if stats is not None:
        stats.generated = generated
    return None, float("inf")


def manhattan(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """曼哈顿距离：四方向移动下最常用的网格启发函数。"""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])

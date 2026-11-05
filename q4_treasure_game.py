# -*- coding: utf-8 -*-
"""题目四：竞争环境下的宝藏分配（A* + Minimax / Alpha-Beta 综合）。

规则摘要
--------
- 7x7 地图：X 为障碍，数字为进入代价，A、B、T 格进入代价为 1，四方向移动。
- A（MAX）与 B（MIN）按 A→B→A→B 轮流选取一个尚未获得的宝藏，
  沿最小代价路径移动过去（经过其他宝藏不收集，对手不阻挡）。
- Gain(p, Ti) = Vi - d(p, Ti)，U = Score_A - Score_B；
  A 最大化 U，B 最小化 U；到达深度上限或宝藏取完时以当前 U 评估。

实现结构
--------
1. 用 A* 预计算 {A, B, T1..T4} 两两最小代价 -> 6x6 距离矩阵
   （玩家每回合结束必停在某宝藏或起点格上，故该矩阵覆盖所有可能查询）。
2. 博弈状态 GameState：双方位置、剩余宝藏、双方累计收益、当前玩家。
3. minimax / alphabeta 在深度 H=2、H=4 下求 A 的最优首步与最优收益差；
   支持自然顺序与按即时收益排序两种子节点访问顺序，用于剪枝效率对照。
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple

from astar import SearchStats as AStarStats
from astar import astar, manhattan

# ---------------------------------------------------------------- 地图与宝藏

# X=障碍；数字=进入代价；A/B/T 格进入代价为 1
MAP: List[List[str]] = [
    ["A", "1", "1", "X", "2", "1", "T1"],
    ["1", "X", "6", "X", "1", "X", "1"],
    ["1", "1", "T2", "1", "1", "1", "1"],
    ["X", "1", "X", "8", "X", "1", "X"],
    ["1", "1", "1", "1", "T3", "1", "1"],
    ["1", "X", "9", "X", "1", "X", "1"],
    ["T4", "1", "1", "X", "1", "1", "B"],
]

Coord = Tuple[int, int]

START_A: Coord = (0, 0)
START_B: Coord = (6, 6)
TREASURE_POS: Dict[str, Coord] = {
    "T1": (0, 6),
    "T2": (2, 2),
    "T3": (4, 4),
    "T4": (6, 0),
}
TREASURE_VALUE: Dict[str, int] = {"T1": 9, "T2": 6, "T3": 7, "T4": 7}

# 距离矩阵的行/列顺序：A、B 起点 + 四个宝藏
POINTS: List[str] = ["A", "B", "T1", "T2", "T3", "T4"]
POINT_POS: Dict[str, Coord] = {"A": START_A, "B": START_B, **TREASURE_POS}

BLOCKED = "X"


# ------------------------------------------------------------ 1. A* 距离矩阵

def enter_cost(cell: str) -> int:
    """题目四的进入代价：数字取其值，A/B/T 格为 1。"""
    if cell == BLOCKED:
        raise ValueError("obstacle has no enter cost")
    if cell in ("A", "B") or cell.startswith("T"):
        return 1
    return int(cell)


def _neighbors(p: Coord) -> List[Coord]:
    r, c = p
    out = []
    for q in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if 0 <= q[0] < len(MAP) and 0 <= q[1] < len(MAP[0]) and MAP[q[0]][q[1]] != BLOCKED:
            out.append(q)
    return out


def astar_distance(src: Coord, dst: Coord, stats: Optional[AStarStats] = None) -> int:
    """单源单点 A* 最小代价；h 用曼哈顿（每步代价至少为 1，可采纳）。"""
    _, cost = astar(
        src,
        dst,
        _neighbors,
        cost_fn=lambda _a, b: enter_cost(MAP[b[0]][b[1]]),
        heuristic_fn=lambda p: manhattan(p, dst),
        stats=stats,
    )
    return int(cost)


def compute_distance_matrix() -> Dict[Tuple[str, str], int]:
    """6x6 两两距离矩阵，dist[(u, v)] = u 到 v 的最小移动代价。"""
    dist: Dict[Tuple[str, str], int] = {(p, p): 0 for p in POINTS}
    # 代价只与进入格有关、方向对称，故矩阵对称，15 对只需算一半
    for i, u in enumerate(POINTS):
        for v in POINTS[i + 1:]:
            d = astar_distance(POINT_POS[u], POINT_POS[v])
            dist[(u, v)] = d
            dist[(v, u)] = d
    return dist


def format_matrix(dist: Dict[Tuple[str, str], int]) -> str:
    header = "      " + "  ".join(f"{p:>3}" for p in POINTS)
    rows = [header]
    for u in POINTS:
        rows.append(f"{u:>4}  " + "  ".join(f"{dist[(u, v)]:>3}" for v in POINTS))
    return "\n".join(rows)


# ------------------------------------------------------------ 2. 博弈状态

@dataclass(frozen=True)
class GameState:
    """博弈状态：双方位置（点位名）、剩余宝藏、双方累计收益、当前玩家。"""

    a_pos: str           # A 当前所在点位（"A" 或某宝藏名）
    b_pos: str
    remaining: Tuple[str, ...]  # 尚未获取的宝藏，升序存放保证可哈希
    score_a: int = 0
    score_b: int = 0
    a_turn: bool = True          # 当前玩家：True=A(MAX)，False=B(MIN)

    @property
    def utility(self) -> int:
        return self.score_a - self.score_b


@dataclass
class GameStats:
    """博弈搜索统计。"""

    nodes: int = 0      # 进入递归的节点数
    evals: int = 0      # 到达评估（叶子/深度截断）次数
    pruned: int = 0     # 因剪枝而未访问的兄弟分支数


def _ordered_moves(state: GameState, order: str) -> List[str]:
    """生成当前玩家的可选宝藏顺序。

    order="natural" 按 T1..T4 自然序；
    order="greedy"  按当前玩家即时收益 Gain 从大到小（MAX 侧高收益优先，
                    MIN 侧 B 收益越高 U 越小，同样是“好棋优先”），
                    通常能让 Alpha-Beta 更早剪枝。
    """
    moves = list(state.remaining)
    if order == "greedy":
        pos = state.a_pos if state.a_turn else state.b_pos
        moves.sort(key=lambda t: TREASURE_VALUE[t] - DIST[(pos, t)], reverse=True)
    return moves


def _apply(state: GameState, target: str) -> GameState:
    """当前玩家沿最小代价路径移动到 target 并获取之，返回新状态。"""
    pos = state.a_pos if state.a_turn else state.b_pos
    gain = TREASURE_VALUE[target] - DIST[(pos, target)]
    remaining = tuple(t for t in state.remaining if t != target)
    if state.a_turn:
        return replace(
            state, a_pos=target, score_a=state.score_a + gain,
            remaining=remaining, a_turn=False,
        )
    return replace(
        state, b_pos=target, score_b=state.score_b + gain,
        remaining=remaining, a_turn=True,
    )


# ------------------------------------------------------------ 3. 博弈搜索

def minimax(state: GameState, depth: int, stats: GameStats, order: str = "natural") -> int:
    """深度受限 Minimax：MAX(A) 层取最大，MIN(B) 层取最小。"""
    stats.nodes += 1
    if depth == 0 or not state.remaining:
        stats.evals += 1
        return state.utility
    values = [minimax(_apply(state, t), depth - 1, stats, order) for t in _ordered_moves(state, order)]
    return max(values) if state.a_turn else min(values)


def alphabeta(
    state: GameState,
    depth: int,
    stats: GameStats,
    alpha: float = float("-inf"),
    beta: float = float("inf"),
    order: str = "natural",
) -> int:
    """深度受限 Alpha-Beta：值越出 [alpha, beta] 即剪掉剩余兄弟分支。"""
    stats.nodes += 1
    if depth == 0 or not state.remaining:
        stats.evals += 1
        return state.utility

    moves = _ordered_moves(state, order)
    if state.a_turn:
        value = float("-inf")
        for i, t in enumerate(moves):
            value = max(value, alphabeta(_apply(state, t), depth - 1, stats, alpha, beta, order))
            alpha = max(alpha, value)
            if value >= beta:
                stats.pruned += len(moves) - i - 1
                break
        return value
    value = float("inf")
    for i, t in enumerate(moves):
        value = min(value, alphabeta(_apply(state, t), depth - 1, stats, alpha, beta, order))
        beta = min(beta, value)
        if value <= alpha:
            stats.pruned += len(moves) - i - 1
            break
    return value


def best_first_move(
    state: GameState,
    depth: int,
    use_pruning: bool,
    order: str = "natural",
) -> Tuple[Optional[str], int, GameStats, Dict[str, int]]:
    """在根状态为 A 枚举每个首步，返回 (最优目标, 最优 U, 统计, 各首步 U)。

    A 是 MAX 玩家，取各首步对应子节点值的最大者。
    """
    stats = GameStats()
    stats.nodes = 1  # 根节点本身
    move_values: Dict[str, int] = {}
    best_t: Optional[str] = None
    best_v = float("-inf")
    alpha = float("-inf")
    for t in _ordered_moves(state, order):
        child = _apply(state, t)
        if use_pruning:
            v = alphabeta(child, depth - 1, stats, alpha, float("inf"), order)
        else:
            v = minimax(child, depth - 1, stats, order)
        move_values[t] = v
        if v > best_v:
            best_v, best_t = v, t
        alpha = max(alpha, best_v)  # 根节点同样按 Alpha-Beta 规则收紧下界
    return best_t, int(best_v), stats, move_values


# 模块加载时即计算距离矩阵（15 对，代价可忽略）
DIST: Dict[Tuple[str, str], int] = compute_distance_matrix()


def initial_state() -> GameState:
    return GameState(a_pos="A", b_pos="B", remaining=tuple(sorted(TREASURE_POS)))

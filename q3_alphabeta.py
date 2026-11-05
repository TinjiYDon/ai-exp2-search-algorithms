# -*- coding: utf-8 -*-
"""题目三：极大极小博弈树的 Alpha-Beta 剪枝。

TreeNode：叶子节点有 value，非叶子节点有 children。
根节点为 MAX 玩家，目标最大化得分；MIN 玩家最小化得分。
子节点默认从左到右评估。提供：
- minimax       朴素极大极小（作为基线，统计访问节点数）
- alphabeta     Alpha-Beta 剪枝（统计访问节点数与剪枝次数）
- build_tree    按题目给定 JSON 结构建树
- best_move     返回根节点处的最优走法下标与得分（供报告展示回传过程）
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Optional


class TreeNode:
    def __init__(self, value: Optional[float] = None, children=None):
        self.value = value  # 叶子节点的得分
        self.children = children if children is not None else []  # 子节点列表

    @property
    def is_leaf(self) -> bool:
        return not self.children


@dataclass
class SearchStats:
    """博弈树搜索统计。"""

    visited: int = 0   # 实际访问（进入递归）的节点总数
    leaves: int = 0    # 实际求值的叶子数
    pruned: int = 0    # 被剪掉的子树中“未访问的子节点”数量（按直接子节点计）


def minimax(node: TreeNode, is_max: bool, stats: Optional[SearchStats] = None) -> float:
    """朴素 Minimax：MAX 层取子值最大，MIN 层取子值最小，叶子回传 value。"""
    if stats is not None:
        stats.visited += 1
    if node.is_leaf:
        if stats is not None:
            stats.leaves += 1
        return node.value
    values = [minimax(c, not is_max, stats) for c in node.children]
    return max(values) if is_max else min(values)


def alphabeta(
    node: TreeNode,
    is_max: bool,
    alpha: float = float("-inf"),
    beta: float = float("inf"),
    stats: Optional[SearchStats] = None,
) -> float:
    """Alpha-Beta 剪枝。

    alpha：当前路径上 MAX 能保证的最好下界；
    beta ：MIN 能保证的最好上界。
    一旦某节点的值越出 [alpha, beta]（MAX 侧 >= beta 或 MIN 侧 <= alpha），
    其剩余兄弟子树不可能影响父节点决策，直接剪掉。
    """
    if stats is not None:
        stats.visited += 1
    if node.is_leaf:
        if stats is not None:
            stats.leaves += 1
        return node.value

    if is_max:
        value = float("-inf")
        for i, child in enumerate(node.children):
            value = max(value, alphabeta(child, False, alpha, beta, stats))
            alpha = max(alpha, value)
            if value >= beta:  # beta 剪枝：MIN 父节点不会选这条更差的支路
                if stats is not None:
                    stats.pruned += len(node.children) - i - 1
                break
        return value
    else:
        value = float("inf")
        for i, child in enumerate(node.children):
            value = min(value, alphabeta(child, True, alpha, beta, stats))
            beta = min(beta, value)
            if value <= alpha:  # alpha 剪枝：MAX 父节点不会选这条更差的支路
                if stats is not None:
                    stats.pruned += len(node.children) - i - 1
                break
        return value


def build_tree(spec: Dict[str, Any]) -> TreeNode:
    """按题目 JSON 结构建树：

    叶子：{"value": 数字}；内部节点：{"is_maximizing_player": bool, "children": [...]}
    建树后各层 MAX/MIN 身份由深度奇偶决定（根为 MAX），
    is_maximizing_player 字段用于校验输入一致性。
    """
    if "value" in spec:
        return TreeNode(value=spec["value"])
    return TreeNode(children=[build_tree(c) for c in spec["children"]])


def best_move(root: TreeNode, use_pruning: bool = True):
    """在根节点（MAX）处枚举每个首步，返回 (最优下标, 最优得分, 各首步得分)。"""
    scores: List[float] = []
    for child in root.children:
        stats = SearchStats()
        fn = alphabeta if use_pruning else minimax
        if use_pruning:
            s = fn(child, False, float("-inf"), float("inf"), stats)
        else:
            s = fn(child, False, stats)
        scores.append(s)
    best = max(range(len(scores)), key=lambda i: scores[i])
    return best, scores[best], scores


def reverse_children(node: TreeNode) -> None:
    """原地反转所有节点的子节点顺序（用于“最差访问顺序”对照实验）。"""
    node.children.reverse()
    for c in node.children:
        reverse_children(c)

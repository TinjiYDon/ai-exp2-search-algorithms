# -*- coding: utf-8 -*-
"""对照实验脚本（实验报告的实验数据来源）。

运行：python run_experiments.py
产出（均写入 results/）：
  summary.json                 全部数值结果汇总
  tables.md                    关键表格（Markdown，可直接贴进报告）
  fig_q1_heuristics.png        题目一：h=0 与曼哈顿启发的扩展节点数对比
  fig_q2_heuristics.png        题目二：三种启发函数对比 + 路径代价累计
  fig_q3_ordering.png          题目三：访问顺序对 Alpha-Beta 的影响
  fig_q4_pruning.png           题目四：H=2/H=4 下 Minimax 与 Alpha-Beta 开销
  fig_q4_sensitivity.png       题目四：深度 H 与宝藏价值 V3 的敏感性分析
"""

from __future__ import annotations

import json
import random
import time
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from astar import SearchStats as AStarStats
from astar import astar
from q1_maze import find_maze_path
from q2_weighted import enter_cost, four_neighbors, make_heuristic, min_cost_weighted
from q3_alphabeta import SearchStats, TreeNode, alphabeta, build_tree, minimax, reverse_children
from q4_treasure_game import (
    DIST, MAP, POINT_POS, POINTS, TREASURE_VALUE,
    astar_distance, best_first_move, compute_distance_matrix, format_matrix,
    initial_state,
)

plt.rcParams["font.sans-serif"] = ["Microsoft YaHei"]
plt.rcParams["axes.unicode_minus"] = False

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "results"
OUT.mkdir(exist_ok=True)

NAVY, BLUE, GREY, ORANGE = "#1f4e79", "#5b8db8", "#b0bac4", "#d9822b"
SUMMARY: dict = {}
MD_TABLES: list[str] = []


def save_fig(fig, name: str) -> None:
    fig.savefig(OUT / name, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  [fig] {name}")


# ---------------------------------------------------------------- 题目一

def exp_q1() -> None:
    print("E1 题目一：启发函数对 A* 扩展节点数的影响")
    start, end = (0, 0), (3, 4)
    grid = [
        ["S", ".", ".", "X", "."],
        [".", "X", ".", ".", "."],
        [".", "X", ".", "X", "."],
        [".", ".", ".", "X", "E"],
        ["X", "X", ".", ".", "."],
    ]
    rows = []
    for h in ("zero", "manhattan"):
        st = AStarStats()
        path = find_maze_path(start, end, grid, heuristic=h, stats=st)
        rows.append((h, st.expanded, st.generated, st.max_open, len(path)))
    SUMMARY["q1_given"] = [
        {"heuristic": h, "expanded": e, "generated": g, "max_open": m, "path_len": n}
        for h, e, g, m, n in rows
    ]

    # 拓展：20x20 随机迷宫（障碍率 0.25，固定种子，保证可解），比较平均扩展数
    rng = random.Random(42)
    agg = {"zero": [], "manhattan": []}
    n_maps = 20
    for k in range(n_maps):
        while True:
            g = [["." for _ in range(20)] for _ in range(20)]
            for r in range(20):
                for c in range(20):
                    if rng.random() < 0.25:
                        g[r][c] = "X"
            g[0][0], g[19][19] = "S", "E"
            probe = find_maze_path((0, 0), (19, 19), g)
            if probe:  # 保证可解
                break
        for h in ("zero", "manhattan"):
            st = AStarStats()
            t0 = time.perf_counter()
            find_maze_path((0, 0), (19, 19), g, heuristic=h, stats=st)
            _ = time.perf_counter() - t0
            agg[h].append(st.expanded)
    avg = {h: sum(v) / len(v) for h, v in agg.items()}
    SUMMARY["q1_random20"] = {"n_maps": n_maps, "avg_expanded": avg}

    MD_TABLES.append(
        "### 题目一：给定迷宫的启发函数对比\n\n"
        "| 启发函数 | 扩展节点数 | 生成节点数 | OPEN 峰值 | 路径长度 |\n|---|---|---|---|---|\n"
        + "\n".join(f"| {h} | {e} | {g} | {m} | {n} |" for h, e, g, m, n in rows)
        + f"\n\n20 个 20×20 随机迷宫（障碍率 0.25）平均扩展节点数："
          f"h=0 为 {avg['zero']:.1f}，曼哈顿为 {avg['manhattan']:.1f}。\n"
    )

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), dpi=160)
    ax = axes[0]
    labels = ["h=0\n(Dijkstra)", "曼哈顿"]
    vals = [r[1] for r in rows]
    ax.bar(labels, vals, color=[GREY, NAVY], width=0.5)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.1, str(v), ha="center", fontsize=9)
    ax.set_title("给定迷宫（5×5）")
    ax.set_ylabel("扩展节点数")
    ax.spines[["top", "right"]].set_visible(False)
    ax = axes[1]
    vals = [avg["zero"], avg["manhattan"]]
    ax.bar(labels, vals, color=[GREY, NAVY], width=0.5)
    for i, v in enumerate(vals):
        ax.text(i, v + 1, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_title(f"随机 20×20 迷宫（{n_maps} 个平均）")
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("题目一：启发函数显著减少 A* 扩展节点数", y=1.02, fontsize=11)
    save_fig(fig, "fig_q1_heuristics.png")


# ---------------------------------------------------------------- 题目二

def exp_q2() -> None:
    print("E2 题目二：加权地形的路径累计与启发函数可采纳性")
    start, end = (0, 0), (4, 4)
    grid = [
        ["S", 1, 1, 8, 1],
        [1, 8, 3, 1, 1],
        [1, 8, 1, 8, 1],
        [1, 1, 1, 8, 1],
        [8, 8, 1, 1, "E"],
    ]

    # 三种启发的效率对比（结果必须一致）
    rows = []
    for h in ("zero", "manhattan", "manhattan_fix"):
        st = AStarStats()
        cost = min_cost_weighted(start, end, grid, heuristic=h, stats=st)
        rows.append((h, cost, st.expanded, st.generated))
    SUMMARY["q2_heuristics"] = [
        {"heuristic": h, "cost": c, "expanded": e, "generated": g} for h, c, e, g in rows
    ]

    # 最优路径的代价累计过程（用可采纳启发重跑一次取回路径）
    path, cost = astar(
        start, end, four_neighbors(grid),
        cost_fn=lambda _a, b: enter_cost(grid, b),
        heuristic_fn=make_heuristic(grid, end, "manhattan_fix"),
    )
    acc, cum = [], 0
    for p in path[1:]:
        cum += enter_cost(grid, p)
        acc.append((p, grid[p[0]][p[1]], enter_cost(grid, p), cum))
    SUMMARY["q2_path"] = {"path": path, "cost": cost, "accumulate": acc}

    MD_TABLES.append(
        "### 题目二：三种启发函数对比（同一加权地图）\n\n"
        "| 启发函数 | 最小代价 | 扩展节点数 | 生成节点数 |\n|---|---|---|---|\n"
        + "\n".join(f"| {h} | {c} | {e} | {g} |" for h, c, e, g in rows)
        + "\n\n最优路径累计代价：\n\n| 进入格 | 地形 | 进入代价 | 累计 g |\n|---|---|---|---|\n"
        + "\n".join(f"| {p} | {v} | {c} | {s} |" for p, v, c, s in acc)
        + "\n"
    )

    # 可采纳性反例：S 与 E 相邻时，朴素曼哈顿 h=1 > 真实代价 0
    tiny = [["S", "E"]]
    h_plain = make_heuristic(tiny, (0, 1), "manhattan")((0, 0))
    h_fix = make_heuristic(tiny, (0, 1), "manhattan_fix")((0, 0))
    true_cost = min_cost_weighted((0, 0), (0, 1), tiny)
    SUMMARY["q2_admissibility_demo"] = {
        "grid": tiny, "h_manhattan_at_S": h_plain, "h_fix_at_S": h_fix, "true_cost": true_cost,
    }

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.2), dpi=160)
    ax = axes[0]
    labels = ["h=0", "曼哈顿", "曼哈顿修正\n(可采纳)"]
    vals = [r[2] for r in rows]
    ax.bar(labels, vals, color=[GREY, ORANGE, NAVY], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 0.15, str(v), ha="center", fontsize=9)
    ax.set_ylabel("扩展节点数")
    ax.set_title("三种启发函数的扩展节点数（代价均为 7）")
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    steps = list(range(1, len(acc) + 1))
    ax.plot(steps, [a[3] for a in acc], marker="o", color=NAVY)
    for i, (p, v, c, s) in enumerate(acc):
        ax.annotate(f"+{c}", (steps[i], s), textcoords="offset points",
                    xytext=(0, 7), ha="center", fontsize=8)
    ax.set_xlabel("步数")
    ax.set_ylabel("累计代价 g")
    ax.set_title("最优路径的代价累计（进入 E 的一步代价为 0）")
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("题目二：加权地形上的 A* 行为", y=1.02, fontsize=11)
    save_fig(fig, "fig_q2_heuristics.png")


# ---------------------------------------------------------------- 题目三

Q3_SPEC = {
    "is_maximizing_player": True,
    "children": [
        {"is_maximizing_player": False, "children": [
            {"is_maximizing_player": True, "children": [{"value": 3}, {"value": 5}]},
            {"is_maximizing_player": True, "children": [{"value": 6}, {"value": 9}]}]},
        {"is_maximizing_player": False, "children": [
            {"is_maximizing_player": True, "children": [{"value": 6}, {"value": 9}]},
            {"is_maximizing_player": True, "children": [{"value": 1}, {"value": 2}]}]},
    ],
}


def _random_tree(depth: int, branching: int, rng: random.Random) -> TreeNode:
    if depth == 0:
        return TreeNode(value=rng.randint(1, 9))
    return TreeNode(children=[_random_tree(depth - 1, branching, rng) for _ in range(branching)])


def _oracle_order(node: TreeNode, is_max: bool) -> None:
    """按子树真实 minimax 值排序子节点（MAX 降序/MIN 升序）——理论最优访问顺序。"""
    for c in node.children:
        _oracle_order(c, not is_max)
    node.children.sort(key=lambda c: minimax(c, not is_max), reverse=is_max)


def exp_q3() -> None:
    print("E3 题目三：Minimax 与 Alpha-Beta、访问顺序的影响")
    # 给定树上的三种访问顺序
    root = build_tree(Q3_SPEC)
    s_mm = SearchStats()
    v = minimax(root, True, s_mm)

    root = build_tree(Q3_SPEC)
    s_ab = SearchStats()
    v_ab = alphabeta(root, True, float("-inf"), float("inf"), s_ab)

    root = build_tree(Q3_SPEC)
    reverse_children(root)  # 最差顺序：从右到左
    s_rev = SearchStats()
    v_rev = alphabeta(root, True, float("-inf"), float("inf"), s_rev)

    root = build_tree(Q3_SPEC)
    _oracle_order(root, True)  # 理论最优顺序
    s_best = SearchStats()
    v_best = alphabeta(root, True, float("-inf"), float("inf"), s_best)

    assert v == v_ab == v_rev == v_best == 5
    given = [
        ("Minimax（无剪枝）", s_mm.leaves, s_mm.visited, 0),
        ("Alpha-Beta 从左到右", s_ab.leaves, s_ab.visited, s_ab.pruned),
        ("Alpha-Beta 从右到左", s_rev.leaves, s_rev.visited, s_rev.pruned),
        ("Alpha-Beta 最优顺序", s_best.leaves, s_best.visited, s_best.pruned),
    ]
    SUMMARY["q3_given_tree"] = [
        {"method": m, "leaves": l, "visited": v_, "pruned": p} for m, l, v_, p in given
    ]
    MD_TABLES.append(
        "### 题目三：给定树上的访问顺序对比\n\n"
        "| 方法 | 求值叶子数 | 访问节点总数 | 剪枝次数 |\n|---|---|---|---|\n"
        + "\n".join(f"| {m} | {l} | {v_} | {p} |" for m, l, v_, p in given) + "\n"
    )

    # 拓展：随机博弈树（分支 3，深度 2/4/6，30 棵平均）验证剪枝的规模效应
    rng = random.Random(7)
    scaling = []
    for depth in (2, 4, 6):
        mm_l = ab_l = best_l = 0.0
        trials = 30
        for _ in range(trials):
            t = _random_tree(depth, 3, rng)
            s1 = SearchStats(); minimax(t, True, s1)
            t = _random_tree(depth, 3, rng)
            s2 = SearchStats(); alphabeta(t, True, float("-inf"), float("inf"), s2)
            t = _random_tree(depth, 3, rng)
            _oracle_order(t, True)
            s3 = SearchStats(); alphabeta(t, True, float("-inf"), float("inf"), s3)
            mm_l += s1.leaves; ab_l += s2.leaves; best_l += s3.leaves
        scaling.append((depth, mm_l / trials, ab_l / trials, best_l / trials))
    SUMMARY["q3_random_scaling"] = [
        {"depth": d, "minimax": m, "alphabeta": a, "alphabeta_best_order": b}
        for d, m, a, b in scaling
    ]

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), dpi=160)
    ax = axes[0]
    names = ["Minimax", "AB 左到右", "AB 右到左", "AB 最优序"]
    vals = [g[1] for g in given]
    ax.bar(names, vals, color=[GREY, NAVY, ORANGE, BLUE], width=0.55)
    for i, v_ in enumerate(vals):
        ax.text(i, v_ + 0.1, str(v_), ha="center", fontsize=9)
    ax.set_ylabel("求值叶子数")
    ax.set_title("给定树（叶子 3,5,6,9,6,9,1,2）")
    ax.tick_params(axis="x", labelsize=8)
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    ds = [s[0] for s in scaling]
    ax.plot(ds, [s[1] for s in scaling], "o--", color=GREY, label="Minimax")
    ax.plot(ds, [s[2] for s in scaling], "s-", color=NAVY, label="Alpha-Beta 自然序")
    ax.plot(ds, [s[3] for s in scaling], "^-", color=BLUE, label="Alpha-Beta 最优序")
    ax.set_yscale("log")
    ax.set_xlabel("树深（分支因子 3）")
    ax.set_ylabel("平均求值叶子数（对数轴）")
    ax.set_title("随机树上剪枝的规模效应（30 棵平均）")
    ax.legend(fontsize=8)
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("题目三：Alpha-Beta 剪枝效率与访问顺序", y=1.02, fontsize=11)
    save_fig(fig, "fig_q3_ordering.png")


# ---------------------------------------------------------------- 题目四

def exp_q4() -> None:
    print("E4 题目四：距离矩阵、深度与剪枝效率")
    # 1) 距离矩阵 + A* 单次求解统计
    per_pair, total_expanded = [], 0
    for i, u in enumerate(POINTS):
        for v in POINTS[i + 1:]:
            st = AStarStats()
            astar_distance(POINT_POS[u], POINT_POS[v], stats=st)
            per_pair.append((u, v, DIST[(u, v)], st.expanded))
            total_expanded += st.expanded
    SUMMARY["q4_distance_matrix"] = {
        "points": POINTS,
        "matrix": {u: [DIST[(u, v)] for v in POINTS] for u in POINTS},
        "pair_expanded": per_pair,
        "total_expanded": total_expanded,
    }
    MD_TABLES.append(
        "### 题目四：6×6 距离矩阵（A* 两两最小代价）\n\n```\n" + format_matrix(DIST) + "\n```\n"
    )

    # 2) H ∈ {2,4} × {Minimax, AB 自然序, AB 按即时收益排序}
    rows = []
    for depth in (2, 4):
        for method, use_ab, order in (
            ("Minimax", False, "natural"),
            ("Alpha-Beta 自然序", True, "natural"),
            ("Alpha-Beta 收益排序", True, "greedy"),
        ):
            t, v_, stats, _ = best_first_move(initial_state(), depth, use_ab, order)
            rows.append((depth, method, t, v_, stats.nodes, stats.evals, stats.pruned))
    SUMMARY["q4_pruning"] = [
        {"H": d, "method": m, "best_target": t, "best_value": v_,
         "nodes": n, "evals": e, "pruned": p}
        for d, m, t, v_, n, e, p in rows
    ]
    MD_TABLES.append(
        "### 题目四：H=2/H=4 下三种搜索配置的开销\n\n"
        "| H | 方法 | 最优首步 | 最优 U | 访问节点 | 评估次数 | 剪枝数 |\n|---|---|---|---|---|---|---|\n"
        + "\n".join(f"| {d} | {m} | {t} | {v_} | {n} | {e} | {p} |"
                    for d, m, t, v_, n, e, p in rows) + "\n"
    )

    # 3) 深度敏感性 H=1..4
    depth_sweep = []
    for h_ in (1, 2, 3, 4):
        t, v_, _, _ = best_first_move(initial_state(), h_, False)
        depth_sweep.append((h_, t, v_))
    SUMMARY["q4_depth_sweep"] = [
        {"H": h_, "best_target": t, "best_value": v_} for h_, t, v_ in depth_sweep
    ]

    # 4) 宝藏价值敏感性：V3 从 1 到 12，观察 H=4 最优首步切换
    v3_sweep = []
    for v3 in range(1, 13):
        TREASURE_VALUE["T3"] = v3
        t, v_, _, _ = best_first_move(initial_state(), 4, False)
        v3_sweep.append((v3, t, v_))
    TREASURE_VALUE["T3"] = 7  # 还原
    SUMMARY["q4_v3_sweep"] = [
        {"V3": v3, "best_target": t, "best_value": v_} for v3, t, v_ in v3_sweep
    ]

    # 5) 距离缓存的收益：预计算 15 对 vs 搜索中每次转移都调用 A*
    t0 = time.perf_counter()
    compute_distance_matrix()
    t_matrix = time.perf_counter() - t0
    t0 = time.perf_counter()
    astar_distance(START := POINT_POS["A"], POINT_POS["T1"])
    t_single = time.perf_counter() - t0
    n_transitions = rows[3][4] - 1  # H=4 Minimax 的边数 = 节点数 - 1
    SUMMARY["q4_caching"] = {
        "matrix_time_ms": round(t_matrix * 1000, 3),
        "single_astar_ms": round(t_single * 1000, 3),
        "h4_minimax_transitions": n_transitions,
        "no_cache_estimate_ms": round(n_transitions * t_single * 1000, 3),
    }

    fig, axes = plt.subplots(1, 2, figsize=(8.4, 3.4), dpi=160)
    ax = axes[0]
    short = {"Minimax": "Minimax", "Alpha-Beta 自然序": "AB\n自然序", "Alpha-Beta 收益排序": "AB\n收益排序"}
    labels = [f"H={d}\n{short[m]}" for d, m, *_ in rows]
    vals = [r[4] for r in rows]
    colors = [GREY if "Minimax" in m else (NAVY if "自然" in m else BLUE)
              for _, m, *_ in rows]
    ax.bar(range(len(vals)), vals, color=colors, width=0.55)
    for i, v_ in enumerate(vals):
        ax.text(i, v_ + 0.8, str(v_), ha="center", fontsize=8)
    ax.set_xticks(range(len(vals)))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("访问节点数")
    ax.set_title("H=2 / H=4 的搜索开销")
    ax.spines[["top", "right"]].set_visible(False)

    ax = axes[1]
    ax.plot([s[0] for s in v3_sweep], [s[2] for s in v3_sweep], "o-", color=NAVY)
    for v3, t, v_ in v3_sweep:
        if v3 in (1, 6, 7, 12):
            ax.annotate(t, (v3, v_), textcoords="offset points", xytext=(0, 8),
                        ha="center", fontsize=8, color=ORANGE)
    ax.axvline(7, color=GREY, ls=":", lw=1)
    ax.set_xlabel("假设修改的 T3 价值 V3")
    ax.set_ylabel("H=4 最优收益差 U")
    ax.set_title("宝藏价值敏感性（标注为最优首步）")
    ax.spines[["top", "right"]].set_visible(False)
    fig.suptitle("题目四：剪枝效率与决策敏感性", y=1.02, fontsize=11)
    save_fig(fig, "fig_q4_pruning.png")

    # 深度扫描单独一张小图并入上面？为控制篇幅，深度扫描只入表
    MD_TABLES.append(
        "### 题目四：深度扫描（Minimax）\n\n| H | 最优首步 | 最优 U |\n|---|---|---|\n"
        + "\n".join(f"| {h_} | {t} | {v_} |" for h_, t, v_ in depth_sweep)
        + "\n\n### 题目四：V3 敏感性（H=4, Minimax）\n\n| V3 | 最优首步 | 最优 U |\n|---|---|---|\n"
        + "\n".join(f"| {v3} | {t} | {v_} |" for v3, t, v_ in v3_sweep) + "\n"
    )


def main() -> None:
    exp_q1()
    exp_q2()
    exp_q3()
    exp_q4()
    (OUT / "summary.json").write_text(
        json.dumps(SUMMARY, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
    )
    (OUT / "tables.md").write_text("\n".join(MD_TABLES), encoding="utf-8")
    print(f"\n已写入 {OUT}/summary.json 与 tables.md")


if __name__ == "__main__":
    main()

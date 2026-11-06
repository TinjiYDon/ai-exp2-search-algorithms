# 实验二：搜索算法（A* · Minimax · Alpha-Beta）

当代人工智能实验课 · 实验二。在网格地图上用 A* 求解最短路径与最小代价，
在博弈树上用 Minimax / Alpha-Beta 求解对抗决策，最后将二者结合解决
「竞争环境下的宝藏分配」综合题。

## 环境

Python ≥ 3.10；算法实现只用标准库（heapq / dataclasses / typing），
画对照实验的图需要 matplotlib：

```bash
pip install matplotlib
```

本机验证环境：`D:\ai-stack\venv`（Python 3.12.10，matplotlib 3.11.0）。

## 文件结构

| 文件 | 说明 |
|------|------|
| `astar.py` | 通用 A*：状态/g/h/f、最小堆 + 平局计数器、关闭表、过程统计 |
| `q1_maze.py` | 题目一：迷宫寻路，返回最短路径坐标序列（无解返回 `[]`） |
| `q2_weighted.py` | 题目二：加权地形，返回最小总代价（无解返回 `-1`） |
| `q3_alphabeta.py` | 题目三：`TreeNode`、Minimax、Alpha-Beta、JSON 建树 |
| `q4_treasure_game.py` | 题目四：A* 预计算 6×6 距离矩阵 + 博弈状态 + 深度受限 Minimax/Alpha-Beta |
| `run_tests.py` | 四个题目给定测试用例的一键回归（含无解用例） |
| `run_experiments.py` | 全部对照实验，输出到 `results/` |
| `results/summary.json` / `tables.md` / `fig_*.png` | 实验数据、表格与图 |
| `report.md` | 实验报告全文（Markdown） |

## 一键复现

```bash
python run_tests.py        # 回归四个给定用例，全部 PASS
python run_experiments.py  # 重新生成 results/ 下全部数据与图
```

## 给定用例的验证结果

| 题目 | 输入摘要 | 程序输出 | 预期 | 结果 |
|---|---|---|---|---|
| 一 迷宫寻路 | 5×5 网格，(0,0)→(3,4) | `[(0,0),(0,1),(0,2),(1,2),(1,3),(1,4),(2,4),(3,4)]` | 长度为 8 的最短路 | PASS |
| 二 加权地形 | 5×5 权值图，(0,0)→(4,4) | `7` | 7 | PASS |
| 三 Alpha-Beta | 题目给定 JSON 树 | `5`（叶子求值 7/8，剪枝 1 次） | 5 | PASS |
| 四 综合题 H=2 | 给定地图与宝藏价值 | `{"best_target":"T2","best_value":-1}` | T2 / -1 | PASS |
| 四 综合题 H=4 | 同上 | `{"best_target":"T3","best_value":3}` | T3 / 3 | PASS |

## 接口速查

```python
from q1_maze import find_maze_path
from q2_weighted import min_cost_weighted
from q3_alphabeta import build_tree, alphabeta, minimax
from q4_treasure_game import initial_state, best_first_move, DIST, format_matrix

find_maze_path((0, 0), (3, 4), grid)          # -> List[Tuple[int,int]]
min_cost_weighted((0, 0), (4, 4), grid)       # -> int
alphabeta(build_tree(spec), True)             # -> 5
best_first_move(initial_state(), depth=4, use_pruning=True)  # -> ('T3', 3, ...)
```

更多分析见 `report.md`。

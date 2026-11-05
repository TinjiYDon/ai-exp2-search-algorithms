# -*- coding: utf-8 -*-
"""生成《实验报告.pdf》：读取 results/summary.json 的实验数据排版。

运行：python build_report_pdf.py
依赖：fpdf2（字体用系统微软雅黑，保证中文显示）。
报告全文 Markdown 版见 report.md；PDF 为同内容的排版版。
"""

from __future__ import annotations

import json
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent
RESULTS = ROOT / "results"
PDF_PATH = ROOT / "实验报告.pdf"
FONT = r"C:\Windows\Fonts\msyh.ttc"

NAVY = (31, 78, 121)
INK = (33, 37, 41)
MUTED = (90, 98, 104)
PALE = (244, 247, 250)
WARN_BG = (255, 248, 230)

S = json.loads((RESULTS / "summary.json").read_text(encoding="utf-8"))


class Report(FPDF):
    def footer(self):
        self.set_y(-12)
        self.set_font("yh", size=8)
        self.set_text_color(*MUTED)
        self.cell(0, 8, f"实验二  搜索算法    {self.page_no()}/{{nb}}", align="C")


def heading(pdf: Report, text: str) -> None:
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("yh", size=12)
    pdf.cell(0, 8, f"  {text}", ln=1, fill=True)
    pdf.ln(1.5)
    pdf.set_text_color(*INK)


def sub(pdf: Report, text: str) -> None:
    pdf.set_font("yh", size=10.5)
    pdf.set_text_color(*NAVY)
    pdf.cell(0, 6.5, text, ln=1)
    pdf.set_text_color(*INK)


def para(pdf: Report, text: str, size: float = 9.5, fill=None) -> None:
    pdf.set_font("yh", size=size)
    pdf.set_text_color(*INK)
    if fill:
        pdf.set_fill_color(*fill)
    pdf.multi_cell(0, 5.0, text, fill=bool(fill), align="L")
    pdf.ln(1)


def table(pdf: Report, headers, rows, widths=None, size: float = 8.5) -> None:
    if widths is None:
        widths = [ (pdf.w - pdf.l_margin - pdf.r_margin) / len(headers) ] * len(headers)
    pdf.set_font("yh", size=size)
    pdf.set_fill_color(*NAVY)
    pdf.set_text_color(255, 255, 255)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, str(h), border=0, align="C", fill=True)
    pdf.ln()
    pdf.set_text_color(*INK)
    for i, row in enumerate(rows):
        if i % 2 == 0:
            pdf.set_fill_color(*PALE)
        else:
            pdf.set_fill_color(255, 255, 255)
        for cell, w in zip(row, widths):
            pdf.cell(w, 5.4, str(cell), border=0, align="C", fill=True)
        pdf.ln()
    pdf.ln(1.5)


def figure(pdf: Report, name: str, w: float = 182) -> None:
    img = RESULTS / name
    x = (pdf.w - w) / 2
    pdf.image(str(img), x=x, w=w)
    pdf.ln(2)


def main() -> None:
    pdf = Report(format="A4")
    pdf.alias_nb_pages()
    pdf.set_margins(14, 14, 14)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.add_font("yh", "", FONT)

    # ------------------------------------------------------------ 封面信息
    pdf.add_page()
    pdf.set_text_color(*NAVY)
    pdf.set_font("yh", size=18)
    pdf.cell(0, 11, "当代人工智能实验二：搜索算法", ln=1)
    pdf.set_fill_color(*PALE)
    pdf.set_text_color(*INK)
    pdf.set_font("yh", size=9.5)
    pdf.multi_cell(
        0, 5.4,
        "  内容：A*（迷宫寻路 / 加权地形）· Minimax 与 Alpha-Beta（博弈树）· "
        "综合题（竞争环境下的宝藏分配）。代码仓库 search-Project2，"
        "一键复现：python run_tests.py / run_experiments.py。",
        fill=True, align="L")
    pdf.ln(3)

    heading(pdf, "1  算法设计与实验设置")
    sub(pdf, "A*（astar.py，四道题共用）")
    para(pdf,
         "状态为网格坐标 (row, col)，通行规则、进入代价、启发函数通过回调注入。"
         "g 为起点到当前节点的累计实际代价，h 为到终点的下界估计，f=g+h；"
         "最小堆按 f 弹出，堆内附自增计数器做平局裁决（先入先出），保证扩展顺序可复现；"
         "关闭表记录各状态最优 g，过期副本弹出时跳过。搜索统计扩展数、生成数、OPEN 峰值。"
         "当 h 永不高估真实剩余代价（可采纳）时，A* 首次弹出终点即最优。")
    sub(pdf, "Minimax 与 Alpha-Beta（q3_alphabeta.py）")
    para(pdf,
         "Minimax：叶子回传评估值，MAX 层取最大、MIN 层取最小。"
         "Alpha-Beta：递归中维护 [alpha, beta] 区间——MAX 侧 value>=beta 或 "
         "MIN 侧 value<=alpha 时，剩余兄弟子树不影响任何祖先决策，直接剪掉。"
         "剪枝只减少访问量、不改变返回值；报告用“两算法输出一致”验证正确性，"
         "用“求值叶子数/访问节点数”量化剪枝收益。")
    sub(pdf, "综合题状态设计（q4_treasure_game.py）")
    para(pdf,
         "GameState = (A位置, B位置, 剩余宝藏, Score_A, Score_B, 当前玩家)。"
         "每回合当前玩家沿最小代价路径移动到所选宝藏，Gain = V_i - d(p, T_i) 入账；"
         "到达深度上限或宝藏取完时以 U = Score_A - Score_B 评估。"
         "玩家每回合必停在六个点位之一，故先用 A* 预计算 6×6 距离矩阵，"
         "博弈搜索中转移代价全部 O(1) 查表。")

    # ------------------------------------------------------------ 题目一
    heading(pdf, "2  题目一：迷宫寻路")
    para(pdf,
         "给定 5×5 迷宫 (0,0)→(3,4)，每步代价 1，h 取曼哈顿距离。最优路径长 7 步、"
         "恰等于曼哈顿距离，因此最优路径上每个节点 f 恒为 7，A* 几乎直线推进到终点；"
         "偏航节点（如 (1,0)，f=9）被压在堆底。程序输出 "
         "[(0,0),(0,1),(0,2),(1,2),(1,3),(1,4),(2,4),(3,4)]，与题目预期一致；"
         "终点被围死的用例返回空列表。")
    q1 = S["q1_given"]
    table(pdf,
          ["启发函数", "扩展节点数", "生成节点数", "OPEN 峰值", "路径长度"],
          [[r["heuristic"], r["expanded"], r["generated"], r["max_open"], r["path_len"]]
           for r in q1])
    para(pdf,
         f"放大到 20 个 20×20 随机迷宫（障碍率 0.25，固定种子）：h=0 平均扩展 "
         f"{S['q1_random20']['avg_expanded']['zero']:.1f} 个节点，曼哈顿 "
         f"{S['q1_random20']['avg_expanded']['manhattan']:.1f} 个，减少约 33%。"
         "h=0 退化为 Dijkstra，无方向性地层层外扩；曼哈顿把搜索压成朝向终点的椭圆。"
         "两种启发找到的路径长度相同——可采纳性保证最优性，差异只在效率。")
    figure(pdf, "fig_q1_heuristics.png")

    # ------------------------------------------------------------ 题目二
    heading(pdf, "3  题目二：加权地形")
    para(pdf,
         "进入代价等于地形权值，进入 E 按题目规定计 0。A* 找到的路径与题目预期完全一致："
         "(0,0)→(1,0)→(2,0)→(3,0)→(3,1)→(3,2)→(4,2)→(4,3)→(4,4)，总代价 7。"
         "路径绕开 8、9 高代价格：加权地形上“最短”不等于“最便宜”，"
         "g 的真实累计与 h 的下界估计缺一不可。")
    acc = S["q2_path"]["accumulate"]
    half = len(acc)
    table(pdf,
          ["进入格", "地形", "进入代价", "累计 g"],
          [[tuple(r[0]), r[1], r[2], r[3]] for r in acc],
          widths=[40, 40, 40, 40])
    pdf.set_fill_color(*WARN_BG)
    para(pdf,
         "可采纳性讨论：地图最小权值为 1，看似曼哈顿可采纳；但“进入 E 免费”使朴素曼哈顿"
         "最多高估 1——反例 [[S,E]]：h(S)=1 而真实剩余代价为 0。修正为 "
         "h'(n)=max(manhattan-1, 0)×min_cost，任意 L 步路径代价 ≥ (L-1)×1+0，"
         "故 h' 严格可采纳。给定地图上三种启发结果一致（均为 7，扩展数 14/10/10），"
         "高估未改变扩展顺序，但只有修正版提供最优性的理论保证。",
         fill=WARN_BG)
    figure(pdf, "fig_q2_heuristics.png")

    # ------------------------------------------------------------ 题目三
    heading(pdf, "4  题目三：Alpha-Beta 剪枝")
    para(pdf,
         "给定树（叶子从左到右 3,5,6,9,6,9,1,2）：三个 MAX 节点回传 5、9、2，"
         "两个 MIN 节点回传 min(5,9)=5、min(9,2)=2，根 MAX 取 max(5,2)=5，符合预期。"
         "剪枝过程：左 MIN 子树定值 5 后根 alpha=5；进入右 MIN 子树，其第二个 MAX 孩子"
         "先看到叶子 1，右 MIN ≤1 ≤ alpha，根不会选右侧，叶子 2 被剪掉。"
         "Alpha-Beta 返回 5，与 Minimax 相同，少求值 1 个叶子。")
    table(pdf,
          ["方法", "求值叶子数", "访问节点总数", "剪枝次数"],
          [[r["method"], r["leaves"], r["visited"], r["pruned"]] for r in S["q3_given_tree"]],
          widths=[62, 40, 40, 40])
    sc = S["q3_random_scaling"]
    para(pdf,
         "放大到随机博弈树（分支因子 3、叶子随机 1–9、30 棵平均）："
         f"深度 2/4/6 时 Minimax 求值 {sc[0]['minimax']:.0f}/{sc[1]['minimax']:.0f}/"
         f"{sc[2]['minimax']:.0f} 个叶子，Alpha-Beta 自然序 "
         f"{sc[0]['alphabeta']:.1f}/{sc[1]['alphabeta']:.1f}/{sc[2]['alphabeta']:.1f}，"
         f"最优序 {sc[0]['alphabeta_best_order']:.0f}/{sc[1]['alphabeta_best_order']:.0f}/"
         f"{sc[2]['alphabeta_best_order']:.0f}。深度 6 时自然序只访问约 24% 叶子、"
         "最优序仅约 7%——若总先访问好棋，叶子访问量约 O(b^(d/2))，"
         "相当于把有效搜索深度翻倍。访问顺序是剪枝收益的开关。")
    figure(pdf, "fig_q3_ordering.png")

    # ------------------------------------------------------------ 题目四
    heading(pdf, "5  题目四：竞争环境下的宝藏分配（综合题）")
    para(pdf,
         "进入代价：数字格取其值，A/B/T 格为 1；h=曼哈顿（每步至少花 1，可采纳）。"
         "15 对点位各跑一次 A*（矩阵对称只算一半），共扩展 "
         f"{S['q4_distance_matrix']['total_expanded']} 个节点。例如 A→T1 因 (0,3)=X "
         "绕行第 2 行全 1 通道，代价 10；A—B、T1—T4 的 12 恰等于曼哈顿距离，"
         "说明绕行未产生额外代价。")
    pts = S["q4_distance_matrix"]["points"]
    mat = S["q4_distance_matrix"]["matrix"]
    table(pdf, [""] + pts,
          [[u] + mat[u] for u in pts],
          widths=[22] + [160 / 6] * 6)
    para(pdf,
         "状态 GameState 记录双方位置、剩余宝藏、双方累计收益与当前玩家（见第 1 节）。"
         "H=2 与 H=4 下，Minimax 与 Alpha-Beta 输出完全一致，并与题目预期一致：")
    table(pdf,
          ["H", "方法", "最优首步", "最优 U", "访问节点", "评估次数", "剪枝数"],
          [[r["H"], r["method"], r["best_target"], r["best_value"], r["nodes"], r["evals"], r["pruned"]]
           for r in S["q4_pruning"]],
          widths=[14, 52, 26, 22, 24, 24, 20])
    para(pdf,
         "决策差异：H=2 只看两步，A 首步拿即时收益最高的 T2（6-4=+2），随后 B 必拿 "
         "家门口的 T3（7-4=+3），U=-1；H=4 看到全局——T3 卡在 B 家门口，不只是收益，"
         "更是必须抢走的战略点，A→T3 后终局 U=+3（逐首步：T1→-5, T2→+1, T3→+3, T4→-7）。"
         "深度扫描 H=1,2,3 最优首步均为 T2，只有完整对局让 T3 的战略价值显形："
         "评估函数的短视无法被更聪明的搜索弥补，深度本身就是信息。")
    para(pdf,
         "剪枝效果：收益排序（当前玩家按即时 Gain 从大到小生成走法）把 H=4 访问节点从 "
         "47 降到 37（-21%），较 Minimax 的 65 累计减少 43%；输出不变，是纯效率优化。")
    figure(pdf, "fig_q4_pruning.png")

    # ------------------------------------------------------------ 拓展与结论
    heading(pdf, "6  自设对照实验与拓展")
    para(pdf,
         "决策边界：把 V3 从 1 扫到 12（H=4, Minimax），V3≤6 时最优首步为 T2、"
         "V3≥7 时为 T3——题目给定值 V3=7 恰好落在决策边界上，差 1 分答案就换成 T2，"
         "说明题目参数经过设计（上图右）。")
    c = S["q4_caching"]
    para(pdf,
         f"距离缓存：预计算 15 对 A* 距离共约 {c['matrix_time_ms']:.2f} ms；若在博弈搜索中"
         f"每次转移重新调用 A*，H=4 Minimax 的 {c['h4_minimax_transitions']} 次转移约需 "
         f"{c['no_cache_estimate_ms']:.2f} ms，且随深度成倍增长。预计算把转移代价降为 "
         "O(1) 查表——玩家位置只可能落在 6 个点位上，距离查询集合是封闭的，"
         "这是状态空间结构化带来的红利。")
    para(pdf,
         "健壮性用例（自设，均纳入 run_tests.py 回归）：终点被障碍围死时题目一返回 []、"
         "题目二返回 -1；[[S,E]] 反例验证朴素曼哈顿高估而修正启发 h'=0 恰等于真实代价；"
         "题目三在左到右/右到左/最优序下 Alpha-Beta 返回值均与 Minimax 一致。")

    heading(pdf, "7  结论")
    para(pdf,
         "1）A* 的效率来自启发的方向性：可采纳的 h 保证最优，h 越紧扩展越少"
         "（给定迷宫 16→13，随机迷宫 -33%）。")
    para(pdf,
         "2）加权地形把“最短”变成“最便宜”；终点免费的规则会使朴素曼哈顿失去可采纳性，"
         "需要 -1 修正，给定地图上修正前后结果一致但只有修正版提供理论保证。")
    para(pdf,
         "3）Alpha-Beta 与 Minimax 输出恒等，收益全在访问量：给定树 8→7 叶子，"
         "随机深 6 树 -76%，最优访问序 -93%；先访问好棋是剪枝的杠杆。")
    para(pdf,
         "4）综合题展示两种搜索的分工：A* 把地图压缩成 6×6 代价矩阵，博弈搜索在矩阵上"
         "做决策。H=2 的短视最优（T2, -1）不同于 H=4 的全局最优（T3, +3）——"
         "对手的存在让“近在咫尺的高收益”成为诱饵，而 V3=7 恰在决策边界上。")
    pdf.set_fill_color(*PALE)
    para(pdf,
         "可复现性：python run_tests.py（8 项断言全部 PASS）；python run_experiments.py "
         "重新生成 results/ 下全部数据与图；随机实验固定种子（迷宫 42、博弈树 7），"
         "多次运行数值一致。算法实现仅依赖 Python 标准库。",
         fill=PALE)

    pdf.output(PDF_PATH)
    print(f"pages={pdf.pages_count}")
    print(f"pdf={PDF_PATH}")


if __name__ == "__main__":
    main()

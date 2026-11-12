# -*- coding: utf-8 -*-
"""各分析页面的 PDF 报告导出（中文，黑体，含图表）。"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
from fpdf import FPDF

FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
APP_NAME = "好好好用的直播日志分析工具"

plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

METRICS_CFG = [
    ("在线人数", "#E63946"),
    ("总观看人数", "#457B9D"),
    ("点赞数", "#2A9D8F"),
    ("新增粉丝数", "#F9C74F"),
]


def _new_pdf(title: str, landscape: bool = False) -> FPDF:
    pdf = FPDF(orientation="L" if landscape else "P", unit="mm", format="A4")
    pdf.add_font("SimHei", "", str(FONT_PATH))
    pdf.add_font("SimHei", "B", str(FONT_PATH))  # 黑体无独立粗体文件，同文件代用
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.add_page()
    pdf.set_font("SimHei", size=18)
    pdf.cell(0, 12, f"{APP_NAME} · {title}", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_font("SimHei", size=9)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
             new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(4)
    return pdf


def _table(pdf: FPDF, headers, rows, widths=None, font_size=9):
    pdf.set_font("SimHei", size=font_size)
    with pdf.table(col_widths=widths, text_align="LEFT", line_height=5.5) as table:
        head = table.row()
        for h in headers:
            head.cell(h)
        for row in rows:
            r = table.row()
            for v in row:
                r.cell(str(v))
    pdf.ln(4)


def _section(pdf: FPDF, text: str, size=11):
    pdf.set_font("SimHei", size=size)
    pdf.cell(0, 7, text, new_x="LMARGIN", new_y="NEXT")


def _embed_image(pdf: FPDF, caption: str, png_bytes: bytes):
    if png_bytes:
        pdf.ln(2)
        pdf.image(BytesIO(png_bytes), w=pdf.epw)
        pdf.set_font("SimHei", size=9)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 5, caption, new_x="LMARGIN", new_y="NEXT", align="C")
        pdf.set_text_color(0, 0, 0)
    pdf.ln(3)


def _footer(pdf: FPDF, note: str):
    pdf.set_font("SimHei", size=9)
    if note:
        pdf.multi_cell(0, 6, note, new_x="LMARGIN", new_y="NEXT")
    pdf.set_x(pdf.l_margin)  # 无论前面内容如何，页脚都从左边界开始
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"由 {APP_NAME} 生成", new_x="LMARGIN", new_y="NEXT", align="C")
    pdf.set_text_color(0, 0, 0)


def _fmt(v):
    return v.strftime('%Y-%m-%d %H:%M:%S') if v is not None else "无数据"


# ---------------------- 图表渲染（matplotlib → PNG） ----------------------

def _chart_single(df_x) -> bytes:
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), tight_layout=True)
    axes = axes.flatten()
    x = df_x['日志时间']
    for ax, (name, color) in zip(axes, METRICS_CFG):
        ax.plot(x, df_x[name], color=color, linewidth=1.8)
        ax.fill_between(x, 0, df_x[name], color=color, alpha=0.2)
        ax.set_title(f"{name}趋势", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


def _chart_compare(cmp_df: pd.DataFrame) -> bytes:
    labels = [f"{r['日期'][5:]} {r['开播'][6:]}" for _, r in cmp_df.iterrows()]
    fig, ax = plt.subplots(figsize=(11, 4), tight_layout=True)
    width = 0.38
    idx = range(len(cmp_df))
    ax.bar([i - width / 2 for i in idx], cmp_df['峰值在线'], width, color="#457B9D", label="峰值在线")
    ax.bar([i + width / 2 for i in idx], cmp_df['涨粉'], width, color="#F9C74F", label="涨粉")
    ax.set_xticks(list(idx))
    ax.set_xticklabels(labels, fontsize=8, rotation=30, ha='right')
    ax.set_title("各场次 峰值在线 vs 涨粉", fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


def _chart_period(period_stat: pd.DataFrame) -> bytes:
    fig, ax = plt.subplots(figsize=(10, 4), tight_layout=True)
    width = 0.38
    idx = range(len(period_stat))
    ax.bar([i - width / 2 for i in idx], period_stat["平均峰值在线"], width,
           color="#457B9D", label="平均峰值在线")
    ax.bar([i + width / 2 for i in idx], period_stat["平均涨粉"], width,
           color="#F9C74F", label="平均涨粉")
    ax.set_xticks(list(idx))
    ax.set_xticklabels(period_stat["时段"], fontsize=9)
    ax.set_title("各时段平均表现", fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=150)
    plt.close(fig)
    return buf.getvalue()


# ---------------------- 三个报告 ----------------------

def pdf_single_session(anchor, date_label, session_label, info, metric_rows,
                       funnel_rows, event_rows, df_x):
    """单场分析报告（含波形图）。"""
    pdf = _new_pdf("单场分析报告")
    pdf.set_font("SimHei", size=12)
    pdf.cell(0, 8, f"主播：{anchor}    日期：{date_label}    {session_label}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    _section(pdf, "一、基础信息")
    _table(pdf, ["项目", "内容"],
           [("房间号", info["房间号"]),
            ("开播时间", _fmt(info["开播时间"])),
            ("下播时间", _fmt(info["下播时间"])),
            ("直播时长", info["直播时长"] or "无数据")], widths=[40, 130])

    _section(pdf, "二、核心指标")
    _table(pdf, ["指标", "数值", "备注"], metric_rows, widths=[50, 50, 80])

    _section(pdf, "三、粉丝转化漏斗")
    _table(pdf, ["指标", "数值", "观看转化率"], funnel_rows, widths=[50, 50, 80])

    _section(pdf, "四、关键事件（在线人数骤增/骤降）")
    if event_rows:
        _table(pdf, ["时间", "类型", "前值", "后值"],
               [(t.strftime('%H:%M:%S'), k, p, c) for t, k, p, c in event_rows],
               widths=[50, 40, 40, 50])
    else:
        pdf.set_font("SimHei", size=9)
        pdf.cell(0, 6, "本场未检测到关键事件。", new_x="LMARGIN", new_y="NEXT")

    _section(pdf, "五、核心指标波形趋势图")
    _embed_image(pdf, "核心指标波形趋势图", _chart_single(df_x))

    _footer(pdf, "")
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def pdf_session_compare(anchor, cmp_df, best_note):
    """场次对比报告（含对比柱状图，横向页）。"""
    pdf = _new_pdf(f"场次对比报告 · {anchor}", landscape=True)
    cols = ["日期", "开播", "结束", "时长", "峰值在线", "总观看", "点赞", "涨粉",
            "观看→点赞率", "观看→涨粉率"]
    rows = [[r[c] for c in cols] for _, r in cmp_df.iterrows()]
    _table(pdf, cols, rows, font_size=8)
    _embed_image(pdf, "各场次峰值在线 vs 涨粉", _chart_compare(cmp_df))
    _footer(pdf, best_note)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def pdf_period_analysis(anchor, period_stat, best_note):
    """时段分析报告（含柱状图，横向页）。"""
    pdf = _new_pdf(f"开播时段效果分析 · {anchor}", landscape=True)
    cols = list(period_stat.columns)
    rows = [[r[c] for c in cols] for _, r in period_stat.iterrows()]
    _table(pdf, cols, rows, font_size=9)
    _embed_image(pdf, "各时段平均表现", _chart_period(period_stat))
    _footer(pdf, best_note)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()

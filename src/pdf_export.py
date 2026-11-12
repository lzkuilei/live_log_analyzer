# -*- coding: utf-8 -*-
"""PDF 导出（reportlab 纯 Python 方案，不依赖外部浏览器，exe 内可靠运行）。"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager

FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
font_manager.fontManager.addfont(str(FONT_PATH))  # 显式注册，避免依赖字体缓存
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False
import pandas as pd
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (HRFlowable, Image, Paragraph, SimpleDocTemplate,
                                Spacer, Table, TableStyle)

APP_NAME = "好好好用的直播日志分析工具"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")

pdfmetrics.registerFont(TTFont("SimHei", str(FONT_PATH)))

GRID = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dde3ea")),
    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1d3557")),
    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
    ("FONTNAME", (0, 0), (-1, -1), "SimHei"),
    ("FONTSIZE", (0, 0), (-1, -1), 9),
    ("TOPPADDING", (0, 0), (-1, -1), 3),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f5f8fb")]),
])

H2_STYLE = ParagraphStyle("h2", fontName="SimHei", fontSize=12, spaceAfter=4,
                          borderColor=colors.HexColor("#e63946"), borderWidth=0,
                          textColor=colors.HexColor("#1d3557"))
META_STYLE = ParagraphStyle("meta", fontName="SimHei", fontSize=9,
                            textColor=colors.HexColor("#888888"), alignment=1)
TITLE_STYLE = ParagraphStyle("title", fontName="SimHei", fontSize=16,
                             textColor=colors.HexColor("#1d3557"), alignment=1, spaceAfter=2)
NOTE_STYLE = ParagraphStyle("note", fontName="SimHei", fontSize=9,
                            textColor=colors.HexColor("#1d3557"), spaceBefore=6)
FOOT_STYLE = ParagraphStyle("foot", fontName="SimHei", fontSize=8,
                            textColor=colors.HexColor("#aaaaaa"), alignment=1, spaceBefore=10)


def _fmt(v):
    return v.strftime('%Y-%m-%d %H:%M:%S') if v is not None else "无数据"


def _doc(title: str, landscape_mode: bool = False):
    buf = BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=landscape(A4) if landscape_mode else A4,
        leftMargin=18 * mm, rightMargin=18 * mm,
        topMargin=14 * mm, bottomMargin=14 * mm,
        title=f"{APP_NAME} · {title}", author=APP_NAME,
    )
    story = [
        Paragraph(f"{APP_NAME} · {title}", TITLE_STYLE),
        Paragraph(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", META_STYLE),
        Spacer(1, 4),
        HRFlowable(width="100%", thickness=0.7, color=colors.HexColor("#e63946")),
        Spacer(1, 6),
    ]
    return buf, doc, story


def _table(df: pd.DataFrame, font_size=9, col_widths=None):
    data = [list(df.columns)] + [[str(v) for v in row] for row in df.values]
    t = Table(data, colWidths=col_widths, style=GRID, repeatRows=1)
    if font_size != 9:
        t.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), font_size)]))
    return t


def _chart_single(df_x) -> Image:
    fig, axes = plt.subplots(2, 2, figsize=(11, 6.5), tight_layout=True)
    axes = axes.flatten()
    x = df_x['日志时间']
    for ax, (name, color) in zip(axes, [
        ("在线人数", "#E63946"), ("总观看人数", "#457B9D"),
        ("点赞数", "#2A9D8F"), ("新增粉丝数", "#F9C74F"),
    ]):
        ax.plot(x, df_x[name], color=color, linewidth=1.8)
        ax.fill_between(x, 0, df_x[name], color=color, alpha=0.2)
        ax.set_title(f"{name}趋势", fontsize=12, fontweight='bold')
        ax.grid(True, alpha=0.3)
        ax.tick_params(labelsize=8)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return Image(buf)


def _chart_bars(labels, series: list, title: str) -> Image:
    fig, ax = plt.subplots(figsize=(11, 3.6), tight_layout=True)
    n = len(series)
    width = 0.8 / n
    idx = range(len(labels))
    colors_list = ["#457B9D", "#F9C74F", "#2A9D8F"]
    for k, (name, values) in enumerate(series):
        offset = (k - (n - 1) / 2) * width
        ax.bar([i + offset for i in idx], values, width, color=colors_list[k % 3], label=name)
    ax.set_xticks(list(idx))
    ax.set_xticklabels(labels, fontsize=8, rotation=30, ha='right')
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    buf.seek(0)
    return Image(buf)


def _finish(buf: BytesIO, doc, story, note=""):
    if note:
        story.append(Spacer(1, 6))
        story.append(Paragraph(note, NOTE_STYLE))
    story.append(Paragraph(f"由 {APP_NAME} 生成", FOOT_STYLE))
    doc.build(story)
    return buf.getvalue()


# ---------------------- 三种报告 ----------------------

def pdf_single_session(anchor, date_label, session_label, info, metric_rows,
                       funnel_rows, event_rows, df_x):
    buf, doc, story = _doc(f"单场分析报告 · {anchor}")
    story.append(Paragraph(f"主播：{anchor}　　日期：{date_label}　　{session_label}", H2_STYLE))
    story.append(Spacer(1, 2))

    story.append(Paragraph("一、基础信息", H2_STYLE))
    story.append(_table(pd.DataFrame(
        [{"项目": "房间号", "内容": info["房间号"]},
         {"项目": "开播时间", "内容": _fmt(info["开播时间"])},
         {"项目": "下播时间", "内容": _fmt(info["下播时间"])},
         {"项目": "直播时长", "内容": info["直播时长"] or "无数据"}])))

    story.append(Paragraph("二、核心指标", H2_STYLE))
    story.append(_table(pd.DataFrame(metric_rows, columns=["指标", "数值", "备注"])))

    story.append(Paragraph("三、粉丝转化漏斗", H2_STYLE))
    story.append(_table(pd.DataFrame(funnel_rows, columns=["指标", "数值", "观看转化率"])))

    story.append(Paragraph("四、关键事件（在线人数骤增/骤降）", H2_STYLE))
    if event_rows:
        story.append(_table(pd.DataFrame(
            [{"时间": t.strftime('%H:%M:%S'), "类型": k, "前值": p, "后值": c}
             for t, k, p, c in event_rows])))
    else:
        story.append(Paragraph("本场未检测到关键事件。", H2_STYLE))

    story.append(Paragraph("五、核心指标波形趋势图", H2_STYLE))
    img = _chart_single(df_x)
    img._restrictSize(174 * mm, 110 * mm)
    story.append(img)
    return _finish(buf, doc, story)


def pdf_session_compare(anchor, cmp_df, best_note):
    buf, doc, story = _doc(f"场次对比报告 · {anchor}", landscape_mode=True)
    story.append(_table(cmp_df, font_size=8))
    story.append(Spacer(1, 4))
    labels = [f"{r['日期'][5:]} {r['开播'][6:]}" for _, r in cmp_df.iterrows()]
    img = _chart_bars(labels, [("峰值在线", cmp_df['峰值在线']), ("涨粉", cmp_df['涨粉'])],
                      "各场次 峰值在线 vs 涨粉")
    img._restrictSize(255 * mm, 85 * mm)
    story.append(img)
    return _finish(buf, doc, story, best_note)


def pdf_period_analysis(anchor, period_stat, best_note):
    buf, doc, story = _doc(f"开播时段效果分析 · {anchor}", landscape_mode=True)
    story.append(_table(period_stat, font_size=9))
    story.append(Spacer(1, 4))
    img = _chart_bars(list(period_stat["时段"]),
                      [("平均峰值在线", period_stat["平均峰值在线"]),
                       ("平均涨粉", period_stat["平均涨粉"])],
                      "各时段平均表现")
    img._restrictSize(255 * mm, 80 * mm)
    story.append(img)
    return _finish(buf, doc, story, best_note)

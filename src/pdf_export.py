# -*- coding: utf-8 -*-
"""各分析页面的 PDF 报告导出（中文，使用 Windows 黑体）。"""
from datetime import datetime
from io import BytesIO
from pathlib import Path

from fpdf import FPDF

FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
APP_NAME = "好好好用的直播日志分析工具"


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


def _footer(pdf: FPDF, note: str):
    pdf.set_font("SimHei", size=9)
    if note:
        pdf.multi_cell(0, 6, note)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, f"由 {APP_NAME} 生成", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)


def _fmt(v):
    return v.strftime('%Y-%m-%d %H:%M:%S') if v is not None else "无数据"


def pdf_single_session(anchor, date_label, session_label, info, metric_rows,
                       funnel_rows, event_rows):
    """单场分析报告。"""
    pdf = _new_pdf("单场分析报告")
    pdf.set_font("SimHei", size=12)
    pdf.cell(0, 8, f"主播：{anchor}    日期：{date_label}    {session_label}",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)

    pdf.set_font("SimHei", size=11)
    pdf.cell(0, 7, "一、基础信息", new_x="LMARGIN", new_y="NEXT")
    _table(pdf, ["项目", "内容"],
           [("房间号", info["房间号"]),
            ("开播时间", _fmt(info["开播时间"])),
            ("下播时间", _fmt(info["下播时间"])),
            ("直播时长", info["直播时长"] or "无数据")], widths=[40, 130])

    pdf.set_font("SimHei", size=11)
    pdf.cell(0, 7, "二、核心指标", new_x="LMARGIN", new_y="NEXT")
    _table(pdf, ["指标", "数值", "备注"], metric_rows, widths=[50, 50, 80])

    pdf.set_font("SimHei", size=11)
    pdf.cell(0, 7, "三、粉丝转化漏斗", new_x="LMARGIN", new_y="NEXT")
    _table(pdf, ["指标", "数值", "观看转化率"], funnel_rows, widths=[50, 50, 80])

    pdf.set_font("SimHei", size=11)
    pdf.cell(0, 7, "四、关键事件（在线人数骤增/骤降）", new_x="LMARGIN", new_y="NEXT")
    if event_rows:
        _table(pdf, ["时间", "类型", "前值", "后值"],
               [(t.strftime('%H:%M:%S'), k, p, c) for t, k, p, c in event_rows],
               widths=[50, 40, 40, 50])
    else:
        pdf.set_font("SimHei", size=9)
        pdf.cell(0, 6, "本场未检测到关键事件。", new_x="LMARGIN", new_y="NEXT")

    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def pdf_session_compare(anchor, cmp_df, best_note):
    """场次对比报告（横向页面容纳更多列）。"""
    pdf = _new_pdf(f"场次对比报告 · {anchor}", landscape=True)
    cols = ["日期", "开播", "结束", "时长", "峰值在线", "总观看", "点赞", "涨粉",
            "观看→点赞率", "观看→涨粉率"]
    rows = [[r[c] for c in cols] for _, r in cmp_df.iterrows()]
    _table(pdf, cols, rows, font_size=8)
    _footer(pdf, best_note)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()


def pdf_period_analysis(anchor, period_stat, best_note):
    """时段分析报告（横向页面）。"""
    pdf = _new_pdf(f"开播时段效果分析 · {anchor}", landscape=True)
    cols = list(period_stat.columns)
    rows = [[r[c] for c in cols] for _, r in period_stat.iterrows()]
    _table(pdf, cols, rows, font_size=9)
    _footer(pdf, best_note)
    out = BytesIO()
    pdf.output(out)
    return out.getvalue()

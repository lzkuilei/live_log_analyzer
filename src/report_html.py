# -*- coding: utf-8 -*-
"""分析报告导出：生成 HTML，再用 Edge 无头模式打印成 PDF（无需额外 Python 依赖）。"""
import base64
import subprocess
import tempfile
from datetime import datetime
from io import BytesIO
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

APP_NAME = "好好好用的直播日志分析工具"
FONT_PATH = Path(r"C:\Windows\Fonts\simhei.ttf")
plt.rcParams["font.sans-serif"] = ["SimHei"]
plt.rcParams["axes.unicode_minus"] = False

METRICS_CFG = [
    ("在线人数", "#E63946"),
    ("总观看人数", "#457B9D"),
    ("点赞数", "#2A9D8F"),
    ("新增粉丝数", "#F9C74F"),
]

CSS = """
body { font-family: "Microsoft YaHei", sans-serif; color: #1d3557; margin: 24px; }
h1 { font-size: 22px; text-align: center; margin: 0 0 4px; }
h2 { font-size: 15px; border-left: 4px solid #e63946; padding-left: 8px; margin: 18px 0 8px; }
.meta { text-align: center; color: #888; font-size: 11px; margin-bottom: 12px; }
table { border-collapse: collapse; width: 100%; font-size: 12px; }
th { background: #1d3557; color: #fff; padding: 5px 8px; }
td { border: 1px solid #dde3ea; padding: 4px 8px; }
tr:nth-child(even) td { background: #f5f8fb; }
img { width: 100%; margin-top: 6px; }
.caption { text-align: center; color: #888; font-size: 11px; margin: 2px 0 10px; }
.footer { text-align: center; color: #aaa; font-size: 11px; margin-top: 20px; }
.note { background: #fff8e6; padding: 8px 12px; border-radius: 6px; font-size: 12px; }
"""


def _fmt(v):
    return v.strftime('%Y-%m-%d %H:%M:%S') if v is not None else "无数据"


def _df_table(df: pd.DataFrame) -> str:
    return df.to_html(index=False, border=0, classes="tbl", justify="left")


def _chart_single_png(df_x) -> str:
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
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _chart_bars_png(labels, series: list, title: str) -> str:
    fig, ax = plt.subplots(figsize=(11, 3.6), tight_layout=True)
    n = len(series)
    width = 0.8 / n
    idx = range(len(labels))
    colors = ["#457B9D", "#F9C74F", "#2A9D8F"]
    for k, (name, values) in enumerate(series):
        offset = (k - (n - 1) / 2) * width
        ax.bar([i + offset for i in idx], values, width, color=colors[k % 3], label=name)
    ax.set_xticks(list(idx))
    ax.set_xticklabels(labels, fontsize=8, rotation=30, ha='right')
    ax.set_title(title, fontsize=13, fontweight='bold')
    ax.legend()
    ax.grid(True, axis='y', alpha=0.3)
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=130)
    plt.close(fig)
    return base64.b64encode(buf.getvalue()).decode()


def _html(title, body, note=""):
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    footer = f'<div class="footer">由 {APP_NAME} 生成 · {now}</div>'
    note_html = f'<div class="note">{note}</div>' if note else ""
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<style>{CSS}</style></head><body>
<h1>{APP_NAME} · {title}</h1>
<div class="meta">生成时间：{now}</div>
{body}
{note_html}
{footer}
</body></html>"""


def html_to_pdf_bytes(html: str) -> bytes:
    """Edge 无头模式把 HTML 打印成 PDF，返回 PDF 字节流。"""
    edge = Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe")
    if not edge.exists():
        edge = Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe")
    with tempfile.TemporaryDirectory(prefix="pdfexp_") as tmp:
        html_path = Path(tmp) / "report.html"
        pdf_path = Path(tmp) / "report.pdf"
        html_path.write_text(html, encoding="utf-8")
        subprocess.run(
            [str(edge), "--headless", "--disable-gpu",
             f"--print-to-pdf={pdf_path}",
             "--no-pdf-header-footer",
             # 独立用户数据目录：避免与正在运行的 Edge 互相干扰导致打印被转交而失败
             f"--user-data-dir={Path(tmp) / 'edgeprofile'}",
             "--no-first-run", "--no-default-browser-check",
             html_path.resolve().as_uri()],
            check=True, timeout=60,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return pdf_path.read_bytes()


# ---------------------- 三种报告 ----------------------

def pdf_single_session(anchor, date_label, session_label, info, metric_rows,
                       funnel_rows, event_rows, df_x):
    rows_html = _df_table(pd.DataFrame(metric_rows, columns=["指标", "数值", "备注"]))
    funnel_html = _df_table(pd.DataFrame(funnel_rows, columns=["指标", "数值", "观看转化率"]))
    if event_rows:
        ev_df = pd.DataFrame(
            [{"时间": t.strftime('%H:%M:%S'), "类型": k, "前值": p, "后值": c}
             for t, k, p, c in event_rows]
        )
        events_html = _df_table(ev_df)
    else:
        events_html = "<p>本场未检测到关键事件。</p>"
    base_html = _df_table(pd.DataFrame(
        [{"项目": "房间号", "内容": info["房间号"]},
         {"项目": "开播时间", "内容": _fmt(info["开播时间"])},
         {"项目": "下播时间", "内容": _fmt(info["下播时间"])},
         {"项目": "直播时长", "内容": info["直播时长"] or "无数据"}]))
    body = f"""
    <h2>一、基础信息</h2>{base_html}
    <h2>二、核心指标</h2>{rows_html}
    <h2>三、粉丝转化漏斗</h2>{funnel_html}
    <h2>四、关键事件（在线人数骤增/骤降）</h2>{events_html}
    <h2>五、核心指标波形趋势图</h2>
    <img src="data:image/png;base64,{_chart_single_png(df_x)}">
    <div class="caption">核心指标波形趋势图</div>
    """
    html = _html(f"单场分析报告 · {anchor}", body)
    return html_to_pdf_bytes(html)


def pdf_session_compare(anchor, cmp_df, best_note):
    labels = [f"{r['日期'][5:]} {r['开播'][6:]}" for _, r in cmp_df.iterrows()]
    chart = _chart_bars_png(labels, [("峰值在线", cmp_df['峰值在线']), ("涨粉", cmp_df['涨粉'])],
                            "各场次 峰值在线 vs 涨粉")
    body = f"""
    {_df_table(cmp_df)}
    <img src="data:image/png;base64,{chart}">
    <div class="caption">各场次峰值在线 vs 涨粉</div>
    """
    html = _html(f"场次对比报告 · {anchor}", body, best_note)
    return html_to_pdf_bytes(html)


def pdf_period_analysis(anchor, period_stat, best_note):
    chart = _chart_bars_png(list(period_stat["时段"]),
                            [("平均峰值在线", period_stat["平均峰值在线"]),
                             ("平均涨粉", period_stat["平均涨粉"])],
                            "各时段平均表现")
    body = f"""
    {_df_table(period_stat)}
    <img src="data:image/png;base64,{chart}">
    <div class="caption">各时段平均表现</div>
    """
    html = _html(f"开播时段效果分析 · {anchor}", body, best_note)
    return html_to_pdf_bytes(html)

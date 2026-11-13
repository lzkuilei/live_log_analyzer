# -*- coding: utf-8 -*-
"""直播日志分析工具 — Streamlit 界面。

标签页：单场分析 / 场次对比 / 时段分析 / 导出报告
"""
import base64
import sys
from io import BytesIO
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analyzer import parse_live_log, build_dataframe, detect_key_events
from pdf_export import (pdf_single_session, pdf_session_compare, pdf_period_analysis,
                        _fmt_hms, _fmt_text, _is_missing)

ICON_PATH = Path(__file__).parent / "assets" / "icon.png"
ICON_B64 = base64.b64encode(ICON_PATH.read_bytes()).decode()

st.set_page_config(page_title="好好好用的直播日志分析工具", page_icon=str(ICON_PATH), layout="wide")
st.markdown(
    f'<h1 style="display:flex;align-items:center;gap:14px;">'
    f'<img src="data:image/png;base64,{ICON_B64}" style="width:52px;border-radius:10px;">'
    f'好好好用的直播日志分析工具</h1>',
    unsafe_allow_html=True,
)
st.markdown(
    """
    <style>
    /* 文件上传控件中文化 */
    [data-testid="stFileUploaderDropzoneInstructions"] { visibility: hidden; height: 0 !important; margin: 0 !important; }
    [data-testid="stFileUploaderDropzone"]::before {
        content: "将文件拖到这里";
        display: block; text-align: center; font-size: 15px;
        color: #1d3557; padding-top: 22px;
    }
    [data-testid="stFileUploaderDropzone"]::after {
        content: "单个文件最大 200MB · 支持 TXT";
        display: block; text-align: center; font-size: 12px;
        color: #8a94a6; padding-bottom: 10px;
    }
    [data-testid="stFileUploaderDropzoneButton"] { position: relative; }
    [data-testid="stFileUploaderDropzoneButton"] p { visibility: hidden; font-size: 0; }
    [data-testid="stFileUploaderDropzoneButton"]::after {
        content: "选择文件";
        position: absolute; inset: 0;
        display: flex; align-items: center; justify-content: center;
        font-size: 14px; color: #1d3557; font-weight: 600;
    }
    </style>
    """,
    unsafe_allow_html=True,
)
st.divider()
APP_VERSION = "v1.0.9"
try:
    CHANGELOG_TEXT = (Path(__file__).parent / "CHANGELOG.md").read_text(encoding="utf-8")
    CHANGELOG_TEXT = CHANGELOG_TEXT.replace("# 更新记录", "").strip()
except Exception:
    CHANGELOG_TEXT = "未找到更新记录文件"


metrics_cfg = [
    ("在线人数", "#E63946"),
    ("总观看人数", "#457B9D"),
    ("点赞数", "#2A9D8F"),
    ("新增粉丝数", "#F9C74F"),
]


# ---------------------- 解析（带缓存，切换筛选条件不再重复解析） ----------------------
@st.cache_data(show_spinner="解析日志中…")
def cached_parse(raw: bytes):
    return parse_live_log(raw.decode("utf-8"))


def build_figure(df_x, anchor_name, events=None):
    """四指标交互波形图（悬停可看具体时间与数值，可叠加关键事件标注线）。"""
    fig = make_subplots(rows=2, cols=2, subplot_titles=[name for name, _ in metrics_cfg])
    x = df_x['日志时间']
    positions = [(1, 1), (1, 2), (2, 1), (2, 2)]
    for (name, color), (r, c) in zip(metrics_cfg, positions):
        fig.add_trace(go.Scatter(
            x=x, y=df_x[name], name=name,
            mode='lines', line=dict(color=color, width=2),
            hovertemplate='%{x|%H:%M:%S}<br>' + name + '：%{y}<extra></extra>',
        ), row=r, col=c)
        fig.update_xaxes(title_text="时间", row=r, col=c)
        fig.update_yaxes(title_text=name, row=r, col=c)
    if events:
        for t, kind, prev, cur in events:
            t = t.to_pydatetime() if hasattr(t, "to_pydatetime") else t
            color = "#E63946" if kind == "骤增" else "#2A9D8F"
            # plotly 的 add_vline 在日期轴上做标注会崩（int+datetime），
            # 改用底层 add_shape + add_annotation 手动画线
            for r, c in [(1, 1), (1, 2), (2, 1), (2, 2)]:
                fig.add_shape(
                    type="line", x0=t, x1=t, y0=0, y1=1,
                    yref="y domain", line_width=1, line_dash="dot", line_color=color,
                    row=r, col=c,
                )
            fig.add_annotation(
                x=t, y=1, yref="y domain", text=kind, showarrow=False,
                font=dict(size=10, color=color), row=1, col=1,
            )
    fig.update_layout(
        height=700, showlegend=False,
        title=dict(text=f"主播{anchor_name} 直播指标趋势", font=dict(size=18)),
        hovermode="x unified",
    )
    return fig


def session_summary(s_df):
    """单场汇总指标。"""
    return {
        "开播": s_df['开播时间'].iloc[0],
        "下播": s_df['下播时间'].iloc[0],
        "时长": s_df['直播时长'].iloc[0],
        "峰值在线": int(s_df['在线人数'].max()),
        "总观看": int(s_df['总观看人数'].iloc[-1]),
        "点赞": int(s_df['点赞数'].iloc[-1]),
        "涨粉": int(s_df['新增粉丝数'].iloc[-1]),
    }


def to_excel_bytes(sheets: dict):
    """把多张表打包成 Excel 字节流。"""
    buf = BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        for name, df_sheet in sheets.items():
            df_sheet.to_excel(writer, sheet_name=name[:31], index=False)
    return buf.getvalue()


if "uploader_version" not in st.session_state:
    st.session_state["uploader_version"] = 0

st.sidebar.header("📁 文件上传")
uploaded_file = st.sidebar.file_uploader(
    "选择直播日志TXT文件", type=["txt"],
    key=f"log_file_{st.session_state['uploader_version']}",
)

# 返回主页：给上传控件换新 key 彻底重建，并清空筛选状态
if st.sidebar.button("🏠 返回主页", key="back_home"):
    st.session_state["uploader_version"] += 1
    for k in ["anchor", "date", "session", "export_scope"]:
        st.session_state.pop(k, None)
    st.rerun()

# 版本 / 更新记录 / 关于（模态对话框，内容完整可滚动）

@st.dialog("📜 更新记录")
def _changelog_dialog():
    st.markdown(CHANGELOG_TEXT, unsafe_allow_html=True)

@st.dialog("👤 关于")
def _about_dialog():
    st.markdown(
        "工具作者：[好好好Tyn✰⋆⁺₊⋆](https://www.douyin.com/user/MS4wLjABAAAAB8-gPsEihGt8Q321hVQN-s-Qy86mZiRKDzlvl8jDP04)"  # noqa: E501
    )
    st.caption("点击名字可打开作者的抖音主页。")

if st.sidebar.button(f"ℹ️ {APP_VERSION}", key="ver_btn"):
    _changelog_dialog()
if st.sidebar.button("👤 关于", key="about_btn"):
    _about_dialog()

st.sidebar.divider()

if uploaded_file is None:
    st.info("💡 请在左侧侧边栏**上传直播日志TXT文件**（格式与样本一致），工具将自动解析并生成分析报告")
    st.divider()
    st.subheader("📌 日志格式要求（与样本一致）")
    st.code("""
    2026-03-30 14:06:16	主播“某某主播”（房间号：1234567890123456） 03-30 14:05:48 已开播
    2026-03-30 14:06:16	主播“某某主播”实时数据（房间号：1234567890123456），在线人数：0，总观看人数：0，点赞数：0，新增粉丝数：0
    2026-03-30 16:22:47	主播“某某主播”已下播（房间号：1234567890123456），下播时间：03-30 16:22:37，直播时长：2小时16分49秒，本场直播总观看人数：0，点赞数：0，新增粉丝数：
    """, language="txt")
    st.caption("🔒 上例中的主播名、房间号均为脱敏占位，不指向任何真实主播。")
    st.stop()

data, sessions = cached_parse(uploaded_file.read())
if not data:
    st.error("❌ 日志文件解析失败，格式与样本不一致！")
    st.stop()
st.success(f"✅ 解析成功！共提取 {len(data)} 条日志数据，{len(sessions)} 场直播")
st.sidebar.divider()

df = build_dataframe(data)

# ---------------------- 侧边栏筛选 ----------------------
st.sidebar.header("🔍 筛选条件")
selected_anchor = st.sidebar.selectbox("选择主播", df['主播名'].unique(), key="anchor")
df_anchor = df[df['主播名'] == selected_anchor]
unique_dates = sorted(df_anchor['直播日期'].unique())
selected_date = st.sidebar.selectbox("选择直播日期", unique_dates, key="date")

df_day = df[
    (df['主播名'] == selected_anchor) & (df['直播日期'] == selected_date)
].reset_index(drop=True)

# 场次选项：按开播时间顺序编号为当天第几场
all_option = "全部场次"
session_labels = {}
day_sessions = sorted(
    df_day['场次号'].unique(),
    key=lambda sid: df_day[df_day['场次号'] == sid].iloc[0]['开播时间'],
)
for n, sid in enumerate(day_sessions, start=1):
    s_row = df_day[df_day['场次号'] == sid].iloc[0]
    start_t = s_row['开播时间'].strftime('%H:%M') if s_row['开播时间'] is not None and not pd.isna(s_row['开播时间']) else '--:--'
    end_t = s_row['下播时间'].strftime('%H:%M') if s_row['下播时间'] is not None and not pd.isna(s_row['下播时间']) else '进行中'
    session_labels[f"第{n}场（{start_t} – {end_t}）"] = sid

selected_session_label = st.sidebar.selectbox(
    "选择场次", [all_option] + list(session_labels.keys()), key="session"
)
if selected_session_label == all_option:
    df_filtered = df_day
else:
    df_filtered = df_day[df_day['场次号'] == session_labels[selected_session_label]].reset_index(drop=True)

if df_filtered.empty:
    st.warning("该主播在此日期没有数据")
    st.stop()


def fmt_time(v):
    return v.strftime('%Y-%m-%d %H:%M:%S') if not _is_missing(v) and hasattr(v, 'strftime') else '无数据'


def fmt_hm(v):
    return v.strftime('%H:%M') if not _is_missing(v) and hasattr(v, 'strftime') else '进行中'


def _session_row(s_df):
    r = s_df.iloc[0]
    peak = int(s_df['在线人数'].max())
    view = int(s_df['总观看人数'].iloc[-1])
    like = int(s_df['点赞数'].iloc[-1])
    fans = int(s_df['新增粉丝数'].iloc[-1])
    start = r['开播时间']
    return {
        "日期": str(r['直播日期']),
        "开播": start.strftime('%m-%d %H:%M') if start is not None and not pd.isna(start) else '推断',
        "结束": fmt_hm(r['下播时间']),
        "时长": r['直播时长'] if r['直播时长'] is not None and not pd.isna(r['直播时长']) else '—',
        "峰值在线": peak,
        "总观看": view,
        "点赞": like,
        "涨粉": fans,
        "观看→点赞率": f"{like / view * 100:.1f}%" if view else "—",
        "观看→涨粉率": f"{fans / view * 100:.2f}%" if view else "—",
        "场次号": r['场次号'],
    }


def period_of(dt):
    if dt is None or pd.isna(dt):
        return "未知"
    h = dt.hour
    if 6 <= h < 12:
        return "早场 (6-12点)"
    if 12 <= h < 18:
        return "下午场 (12-18点)"
    if 18 <= h < 24:
        return "晚场 (18-24点)"
    return "深夜场 (0-6点)"


# ---- 各页面共用数据（提前计算，供展示与 PDF 导出共享） ----
first = df_filtered.iloc[0]
new_fans_final = int(df_filtered['新增粉丝数'].iloc[-1])
view_final = int(df_filtered['总观看人数'].iloc[-1])
like_final = int(df_filtered['点赞数'].iloc[-1])
events = detect_key_events(df_filtered)

cmp_df = pd.DataFrame([_session_row(df_anchor[df_anchor['场次号'] == sid])
                       for sid in sorted(df_anchor['场次号'].unique())]).drop(columns=["场次号"])
best = cmp_df.loc[cmp_df['峰值在线'].idxmax()]
cmp_best_note = f"🏆 峰值在线最高的一场：{best['日期']} {best['开播']}开播（峰值 {best['峰值在线']}，涨粉 {best['涨粉']}）"

all_rows = []
for sid in sorted(df['场次号'].unique()):
    s_df = df[df['场次号'] == sid]
    row = _session_row(s_df)
    row["时段"] = period_of(s_df.iloc[0]['开播时间'])
    row["主播"] = s_df.iloc[0]['主播名']
    all_rows.append(row)
all_df = pd.DataFrame(all_rows)

period_stat = all_df.groupby("时段").agg(
    场次数=("峰值在线", "size"),
    平均峰值在线=("峰值在线", "mean"),
    平均总观看=("总观看", "mean"),
    平均点赞=("点赞", "mean"),
    平均涨粉=("涨粉", "mean"),
    最高峰值=("峰值在线", "max"),
).round(1).reset_index()
_order = ["早场 (6-12点)", "下午场 (12-18点)", "晚场 (18-24点)", "深夜场 (0-6点)", "未知"]
period_stat["_o"] = period_stat["时段"].map({p: i for i, p in enumerate(_order)})
period_stat = period_stat.sort_values("_o").drop(columns="_o")
stat_valid = period_stat[period_stat["时段"] != "未知"]
period_best_note = ""
if not stat_valid.empty:
    _bp = stat_valid.loc[stat_valid["平均峰值在线"].idxmax()]
    period_best_note = f"💡 当前数据中「{_bp['时段']}」平均峰值在线最高（{_bp['平均峰值在线']}），共 {_bp['场次数']} 场。"

tab_single, tab_compare, tab_period, tab_export = st.tabs(
    ["📊 单场分析", "📋 场次对比", "⏰ 时段分析", "⬇️ 导出报告"]
)

# ==================== 单场分析 ====================
with tab_single:
    tcol1, tcol2 = st.columns([4, 1])
    with tcol1:
        st.subheader(f"🎙️ 主播：{selected_anchor} | 直播日期：{selected_date} | {selected_session_label}")
    with tcol2:
        st.download_button(
            "⬇️ 导出 PDF",
            data=pdf_single_session(
                selected_anchor, str(selected_date), selected_session_label,
                info={"房间号": first['房间号'], "开播时间": first['开播时间'],
                      "下播时间": first['下播时间'], "直播时长": first['直播时长']},
                metric_rows=[
                    ("在线人数峰值", int(df_filtered['在线人数'].max()), f"均值 {df_filtered['在线人数'].mean():.1f}"),
                    ("总观看人数最终值", view_final,
                     f"增量 {view_final - int(df_filtered['总观看人数'].iloc[0])}"),
                    ("点赞数最终值", like_final,
                     f"增量 {like_final - int(df_filtered['点赞数'].iloc[0])}"),
                    ("新增粉丝数累计", new_fans_final, f"峰值 {int(df_filtered['新增粉丝数'].max())}"),
                ],
                funnel_rows=[
                    ("总观看", view_final, "—"),
                    ("点赞", like_final, f"{like_final / view_final * 100:.1f}%" if view_final else "—"),
                    ("涨粉", new_fans_final, f"{new_fans_final / view_final * 100:.2f}%" if view_final else "—"),
                ],
                event_rows=events,
                df_x=df_filtered,
            ),
            file_name=f"单场分析_{selected_anchor}_{selected_date}.pdf",
            mime="application/pdf",
            key="pdf_single",
            use_container_width=True,
        )
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.info(f"**房间号**：{first['房间号']}")
    with col2:
        st.info(f"**开播时间**：{fmt_time(first['开播时间'])}")
    with col3:
        st.info(f"**下播时间**：{fmt_time(first['下播时间'])}")
    with col4:
        st.info(f"**直播时长**：{first['直播时长'] if first['直播时长'] is not None and not pd.isna(first['直播时长']) else '无数据'}")

    # 核心指标
    st.subheader("📈 核心指标统计")
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("在线人数峰值", int(df_filtered['在线人数'].max()), f"均值 {df_filtered['在线人数'].mean():.1f}")
    with col2:
        st.metric("总观看人数最终值", int(df_filtered['总观看人数'].iloc[-1]),
                  f"增量 {int(df_filtered['总观看人数'].iloc[-1] - df_filtered['总观看人数'].iloc[0])}")
    with col3:
        st.metric("点赞数最终值", int(df_filtered['点赞数'].iloc[-1]),
                  f"增量 {int(df_filtered['点赞数'].iloc[-1] - df_filtered['点赞数'].iloc[0])}")
    with col4:
        st.metric("新增粉丝数累计", new_fans_final, f"峰值 {int(df_filtered['新增粉丝数'].max())}")

    # 粉丝转化漏斗
    st.subheader("🔻 粉丝转化漏斗")
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric("总观看", view_final)
    with c2:
        st.metric("点赞（观看转化）", like_final,
                  f"{like_final / view_final * 100:.1f}%" if view_final else "—")
    with c3:
        st.metric("涨粉（观看转化）", new_fans_final,
                  f"{new_fans_final / view_final * 100:.2f}%" if view_final else "—")
    st.caption("转化率 = 该指标最终值 ÷ 总观看人数，衡量内容吸引力；跨场次对比时看「场次对比」页更直观。")
    st.divider()

    # 波形图 + 关键事件
    st.subheader("📊 核心指标波形趋势图")
    if events:
        with st.expander(f"⚡ 检测到 {len(events)} 个关键事件（人数骤增/骤降）", expanded=False):
            ev_df = pd.DataFrame(
                [{"时间": _fmt_hms(t), "类型": k, "前值": p, "后值": c}
                 for t, k, p, c in events]
            )
            st.dataframe(ev_df, use_container_width=True)
    st.plotly_chart(build_figure(df_filtered, selected_anchor, events), use_container_width=True)

    with st.expander("📋 查看筛选后原始日志数据（前50行）", expanded=False):
        st.dataframe(df_filtered.head(50), use_container_width=True)

# ==================== 场次对比 ====================
with tab_compare:
    tcol1, tcol2 = st.columns([4, 1])
    with tcol1:
        st.subheader(f"📋 主播 {selected_anchor} 全部场次对比")
    with tcol2:
        st.download_button(
            "⬇️ 导出 PDF",
            data=pdf_session_compare(selected_anchor, cmp_df, cmp_best_note),
            file_name=f"场次对比_{selected_anchor}.pdf",
            mime="application/pdf",
            key="pdf_compare",
            use_container_width=True,
        )
    st.dataframe(cmp_df, use_container_width=True)

    # 峰值在线对比柱状图
    fig = go.Figure()
    labels = [f"{r['日期'][5:]} {r['开播'][6:]}" for _, r in cmp_df.iterrows()]
    fig.add_bar(x=labels, y=cmp_df['峰值在线'], marker_color="#457B9D", name="峰值在线")
    fig.add_bar(x=labels, y=cmp_df['涨粉'], marker_color="#F9C74F", name="涨粉")
    fig.update_layout(
        barmode="group", height=420,
        title="各场次 峰值在线 vs 涨粉",
        xaxis_title="场次", yaxis_title="数值",
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

    best_note = cmp_best_note
    st.success(best_note)

# ==================== 时段分析 ====================
with tab_period:
    tcol1, tcol2 = st.columns([4, 1])
    with tcol1:
        st.subheader("⏰ 开播时段效果分析")
    with tcol2:
        st.download_button(
            "⬇️ 导出 PDF",
            data=pdf_period_analysis(selected_anchor, period_stat, period_best_note),
            file_name=f"时段分析_{selected_anchor}.pdf",
            mime="application/pdf",
            key="pdf_period",
            use_container_width=True,
        )
    st.caption("把所有场次按开播时间归入时段，比较各时段的平均表现，回答「几点开播收益最高」。")

    st.dataframe(period_stat, use_container_width=True)

    fig = go.Figure()
    fig.add_bar(x=period_stat["时段"], y=period_stat["平均峰值在线"], marker_color="#457B9D", name="平均峰值在线")
    fig.add_bar(x=period_stat["时段"], y=period_stat["平均涨粉"], marker_color="#F9C74F", name="平均涨粉")
    fig.update_layout(barmode="group", height=400, title="各时段平均表现", hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)

    stat_valid = period_stat[period_stat["时段"] != "未知"]
    if not stat_valid.empty:
        st.info(period_best_note)

    with st.expander("查看全部场次明细", expanded=False):
        st.dataframe(all_df.drop(columns=["场次号"]), use_container_width=True)

# ==================== 导出报告 ====================
with tab_export:
    st.subheader("⬇️ 导出分析报告（Excel）")
    scope = st.radio("导出范围", ["当前场次", "当前主播当日全部场次", "当前主播全部数据"], key="export_scope")

    if scope == "当前场次":
        sheets = {
            "场次汇总": pd.DataFrame([_session_row(df_filtered)]).drop(columns=["场次号"]),
            "原始数据": df_filtered.drop(columns=["场次号"]),
            "关键事件": pd.DataFrame(
                [{"时间": _fmt_hms(t, '未知时间'), "类型": k, "前值": p, "后值": c}
                 for t, k, p, c in detect_key_events(df_filtered)]
            ),
        }
        fname = f"直播分析_{selected_anchor}_{selected_date}_{selected_session_label.replace('（', '_').replace('）', '')}.xlsx"
    elif scope == "当前主播当日全部场次":
        sheets = {
            "场次汇总": pd.DataFrame([_session_row(df_day[df_day['场次号'] == sid])
                                     for sid in day_sessions]).drop(columns=["场次号"]),
            "原始数据": df_day.drop(columns=["场次号"]),
        }
        fname = f"直播分析_{selected_anchor}_{selected_date}_全部场次.xlsx"
    else:
        # 只导出当前主播的全部场次，不含其他主播
        anchor_all_df = all_df[all_df['主播'] == selected_anchor]
        anchor_ids = anchor_all_df['场次号'].tolist()
        sheets = {
            "场次汇总": anchor_all_df.drop(columns=["场次号"]),
            "原始数据": df[df['场次号'].isin(anchor_ids)].drop(columns=["场次号"]),
        }
        fname = f"直播分析_{selected_anchor}_全部数据.xlsx"

    st.caption(f"将导出：{'、'.join(sheets.keys())}")
    if st.button("生成并下载 Excel", key="download"):
        st.download_button(
            label="点击保存文件",
            data=to_excel_bytes(sheets),
            file_name=fname,
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key="download_btn",
        )

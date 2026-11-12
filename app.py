# -*- coding: utf-8 -*-
"""直播日志分析工具 — Streamlit 界面。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

from analyzer import parse_live_log, build_dataframe

st.set_page_config(page_title="直播日志分析工具", page_icon="📊", layout="wide")
st.title("📊 直播日志分析工具")
st.divider()

metrics_cfg = [
    ("在线人数", "#E63946"),
    ("总观看人数", "#457B9D"),
    ("点赞数", "#2A9D8F"),
    ("新增粉丝数", "#F9C74F"),
]


def build_figure(df_x, anchor_name):
    """四指标交互波形图（悬停可看具体时间与数值）。"""
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
    fig.update_layout(
        height=700, showlegend=False,
        title=dict(text=f"主播{anchor_name} 直播指标趋势", font=dict(size=18)),
        hovermode="x unified",
    )
    return fig


st.sidebar.header("📁 文件上传")
uploaded_file = st.sidebar.file_uploader("选择直播日志TXT文件", type=["txt"], key="log_file")

if uploaded_file is None:
    st.info("💡 请在左侧侧边栏**上传直播日志TXT文件**（格式与样本一致），工具将自动解析并生成分析报告")
    st.divider()
    st.subheader("📌 日志格式要求（与样本一致）")
    st.code("""
    2026-03-30 14:06:16	主播“画祺”（房间号：7622925808390261519） 03-30 14:05:48 已开播
    2026-03-30 14:06:16	主播“画祺”实时数据（房间号：7622925808390261519），在线人数：0，总观看人数：0，点赞数：0，新增粉丝数：0
    2026-03-30 16:22:47	主播“画祺”已下播（房间号：7622925808390261519），下播时间：03-30 16:22:37，直播时长：2小时16分49秒，本场直播总观看人数：3843，点赞数：19072，新增粉丝数：
    """, language="txt")
    st.stop()

data, sessions = parse_live_log(uploaded_file.read().decode('utf-8'))
if not data:
    st.error("❌ 日志文件解析失败，格式与样本不一致！")
    st.stop()
st.success(f"✅ 解析成功！共提取 {len(data)} 条日志数据，{len(sessions)} 场直播")
st.sidebar.divider()

df = build_dataframe(data)

# ---------------------- 筛选条件 ----------------------
st.sidebar.header("🔍 筛选条件")
selected_anchor = st.sidebar.selectbox("选择主播", df['主播名'].unique(), key="anchor")
# 日期选项只显示当前主播有数据的日期
df_anchor = df[df['主播名'] == selected_anchor]
unique_dates = sorted(df_anchor['直播日期'].unique())
selected_date = st.sidebar.selectbox("选择直播日期", unique_dates, key="date")
df_day = df[
    (df['主播名'] == selected_anchor) & (df['直播日期'] == selected_date)
].reset_index(drop=True)

# 场次选项：该主播当天的每一场（含跨天未结束的场次）
all_option = "全部场次"
session_labels = {}
for sid in sorted(df_day['场次号'].unique()):
    s_row = df_day[df_day['场次号'] == sid].iloc[0]
    start_t = s_row['开播时间'].strftime('%H:%M') if s_row['开播时间'] is not None and not pd.isna(s_row['开播时间']) else '--:--'
    end_t = s_row['下播时间'].strftime('%H:%M') if s_row['下播时间'] is not None and not pd.isna(s_row['下播时间']) else '进行中'
    session_labels[f"第{sid + 1}场（{start_t} – {end_t}）"] = sid

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

# ---------------------- 直播基础信息 ----------------------
st.subheader(f"🎙️ 主播：{selected_anchor} | 直播日期：{selected_date} | {selected_session_label}")
first = df_filtered.iloc[0]

def _fmt_time(v):
    """时间列里的 None/NaT 显示为“无数据”。"""
    return v.strftime('%Y-%m-%d %H:%M:%S') if v is not None and not pd.isna(v) else '无数据'

col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info(f"**房间号**：{first['房间号']}")
with col2:
    st.info(f"**开播时间**：{_fmt_time(first['开播时间'])}")
with col3:
    st.info(f"**下播时间**：{_fmt_time(first['下播时间'])}")
with col4:
    st.info(f"**直播时长**：{first['直播时长'] if first['直播时长'] is not None and not pd.isna(first['直播时长']) else '无数据'}")

# ---------------------- 核心指标统计 ----------------------
st.subheader("📈 核心指标统计")
new_fans_final = int(df_filtered['新增粉丝数'].iloc[-1])  # 累计值取最后一条，不做求和
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
st.divider()

# ---------------------- 波形趋势图（交互式，悬停查看数值） ----------------------
st.subheader("📊 核心指标波形趋势图")
st.plotly_chart(build_figure(df_filtered, selected_anchor), use_container_width=True)

# ---------------------- 原始数据 ----------------------
with st.expander("📋 查看筛选后原始日志数据（前50行）", expanded=False):
    st.dataframe(df_filtered.head(50), use_container_width=True)

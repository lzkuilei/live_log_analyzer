# -*- coding: utf-8 -*-
"""直播日志分析工具 — Streamlit 界面。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / "src"))

import pandas as pd
import matplotlib.pyplot as plt
import streamlit as st

from analyzer import parse_live_log, build_dataframe

plt.rcParams['font.sans-serif'] = ['SimHei']  # Windows 中文字体
plt.rcParams['axes.unicode_minus'] = False

st.set_page_config(page_title="直播日志分析工具", page_icon="📊", layout="wide")
st.title("📊 直播日志分析工具")
st.divider()


def adaptive_ticks(max_minutes: int, step_target: int = 10, max_ticks: int = 20):
    """x 轴刻度自适应：最长约 20 个刻度。"""
    if max_minutes <= 0:
        return [0]
    step = step_target
    while (max_minutes // step) + 1 > max_ticks:
        step *= 2
    return list(range(0, int(max_minutes) + step, step))


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
unique_dates = sorted(df['直播日期'].unique())
selected_date = st.sidebar.selectbox("选择直播日期", unique_dates, key="date")
df_filtered = df[
    (df['主播名'] == selected_anchor) & (df['直播日期'] == selected_date)
].reset_index(drop=True)

if df_filtered.empty:
    st.warning("该主播在此日期没有数据")
    st.stop()

# ---------------------- 直播基础信息 ----------------------
st.subheader(f"🎙️ 主播：{selected_anchor} | 直播日期：{selected_date}")
first = df_filtered.iloc[0]
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.info(f"**房间号**：{first['房间号']}")
with col2:
    st.info(f"**开播时间**：{first['开播时间'].strftime('%Y-%m-%d %H:%M:%S') if first['开播时间'] is not None else '无数据'}")
with col3:
    st.info(f"**下播时间**：{first['下播时间'].strftime('%Y-%m-%d %H:%M:%S') if first['下播时间'] is not None else '无数据'}")
with col4:
    st.info(f"**直播时长**：{first['直播时长'] or '无数据'}")

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

# ---------------------- 波形趋势图 ----------------------
st.subheader("📊 核心指标波形趋势图")
fig, axes = plt.subplots(2, 2, figsize=(16, 10), tight_layout=True)
axes = axes.flatten()
metrics = [
    ("在线人数", "#E63946"),
    ("总观看人数", "#457B9D"),
    ("点赞数", "#2A9D8F"),
    ("新增粉丝数", "#F9C74F"),
]
x = df_filtered['相对时间(分钟)']
for idx, (name, color) in enumerate(metrics):
    ax = axes[idx]
    ax.plot(x, df_filtered[name], color=color, linewidth=2, label=name)
    ax.fill_between(x, 0, df_filtered[name], color=color, alpha=0.2)
    ax.set_title(f"{name}趋势", fontsize=14, fontweight='bold', pad=10)
    ax.set_xlabel("相对时间（分钟，开播后）", fontsize=12)
    ax.set_ylabel(name, fontsize=12)
    ax.grid(True, alpha=0.3, linestyle='-')
    ax.legend(loc='upper right')
    ax.set_xticks(adaptive_ticks(x.max()))

fig.suptitle(f"主播{selected_anchor} {selected_date} 直播指标趋势", fontsize=18, fontweight='bold', y=1.02)
st.pyplot(fig)

# ---------------------- 原始数据 ----------------------
with st.expander("📋 查看筛选后原始日志数据（前50行）", expanded=False):
    st.dataframe(df_filtered.head(50), use_container_width=True)

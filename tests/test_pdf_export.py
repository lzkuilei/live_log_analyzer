# -*- coding: utf-8 -*-
"""回归测试：未下播的场次（下播时间为 NaT）导出 PDF 不应崩溃。

复现的崩溃：
    ValueError: NaTType does not support strftime
    （pdf_export._fmt → v.strftime(...)）
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pandas as pd

from analyzer import parse_live_log, build_dataframe
from pdf_export import pdf_single_session

T = "\t"
LOG = "\n".join([
    f"2026-03-30 14:06:16{T}主播“画祺”（房间号：111） 03-30 14:05:48 已开播",
    f"2026-03-30 14:10:00{T}主播“画祺”实时数据（房间号：111），在线人数：5，总观看人数：30，点赞数：10，新增粉丝数：2",
    f"2026-03-30 15:00:00{T}主播“画祺”实时数据（房间号：111），在线人数：9，总观看人数：80，点赞数：40，新增粉丝数：6",
    # 故意不给“已下播”行 → 该场没有下播时间 → 进入 DataFrame 后变成 NaT
])

data, sessions = parse_live_log(LOG)
df = build_dataframe(data)
row = df.iloc[0]

assert pd.isna(row["下播时间"]), "本用例应构造出下播时间缺失（NaT）的场次"
assert row["直播时长"] is None or pd.isna(row["直播时长"]), "直播时长同样应为空"

info = {
    "房间号": row["房间号"],
    "开播时间": row["开播时间"],
    "下播时间": row["下播时间"],   # NaT —— 就是崩溃的元凶
    "直播时长": row["直播时长"],
}

pdf = pdf_single_session(
    "画祺",
    "2026-03-30",
    "第1场",
    info,
    metric_rows=[("在线人数峰值", 9, "均值 7.0")],
    funnel_rows=[("总观看", 80, "—"), ("点赞", 40, "50.0%")],
    event_rows=[],
    df_x=df,
)

assert pdf[:4] == b"%PDF", "应正常生成 PDF"
print("PDF 导出回归测试通过 ✔（下播时间为 NaT 时不再崩溃，输出为“仍在播”）")

# -*- coding: utf-8 -*-
"""直播日志解析核心模块（与 UI 解耦，便于单独测试）。"""
import re
from datetime import datetime

# 行首时间戳
pattern_line_time = re.compile(r'^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})')
# 主播“xx”（房间号：yy）...已开播
pattern_start = re.compile(r'主播“(.*?)”（房间号：(\d+)）.*已开播')
# 在线人数：a，总观看人数：b，点赞数：c，新增粉丝数：d（d 允许为空）
pattern_data = re.compile(
    r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}).*在线人数：(\d+).*总观看人数：(\d+)'
    r'.*点赞数：(\d+).*新增粉丝数：(\d*)'
)
# 主播“xx”已下播（房间号：yy），下播时间：MM-DD HH:MM:SS，直播时长：zz，...
pattern_end = re.compile(
    r'主播“(.*?)”已下播（房间号：(\d+)），下播时间：(\d{2}-\d{2} \d{2}:\d{2}:\d{2})'
    r'.*直播时长：(.*?)，'
)


def _parse_end_time(start_dt: datetime, raw: str) -> datetime:
    """把 'MM-DD HH:MM:SS' 与开播日期合成完整下播时间；跨年自动进位。"""
    end_dt = datetime.strptime(f'{start_dt.year}-{raw}', '%Y-%m-%d %H:%M:%S')
    if end_dt < start_dt:
        # 下播早于开播 → 跨年
        end_dt = end_dt.replace(year=end_dt.year + 1)
    return end_dt


def parse_live_log(text: str):
    """解析直播日志文本。

    返回 (DataFrame 行列表, 场次列表)。
    每行数据带 session_idx 指向所属场次，多场直播互不干扰。
    """
    lines = text.split('\n')
    data = []
    sessions = []  # 每场直播的基础信息

    current = None  # 当前场次
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if '已开播' in line:
            m = pattern_start.search(line)
            if not m:
                continue
            tm = pattern_line_time.match(line)
            start_dt = datetime.strptime(tm.group(1), '%Y-%m-%d %H:%M:%S') if tm else None
            current = {
                "主播名": m.group(1),
                "房间号": m.group(2),
                "开播时间": start_dt,
                "下播时间": None,
                "直播时长": None,
            }
            sessions.append(current)

        elif '在线人数：' in line:
            m = pattern_data.search(line)
            if not m or current is None:
                continue
            new_fans_raw = m.group(5).strip()
            data.append({
                "日志时间": datetime.strptime(m.group(1), '%Y-%m-%d %H:%M:%S'),
                "主播名": current["主播名"],
                "房间号": current["房间号"],
                "session_idx": len(sessions) - 1,
                "在线人数": int(m.group(2)),
                "总观看人数": int(m.group(3)),
                "点赞数": int(m.group(4)),
                "新增粉丝数": int(new_fans_raw) if new_fans_raw else 0,
            })

        elif '已下播' in line:
            m = pattern_end.search(line)
            if m and current is not None and current["开播时间"] is not None:
                current["下播时间"] = _parse_end_time(current["开播时间"], m.group(3))
                current["直播时长"] = m.group(4)

    # 按所属场次回填基础信息与相对时间
    for row in data:
        s = sessions[row.pop("session_idx")]
        start = s["开播时间"]
        row["直播日期"] = row["日志时间"].date()
        row["相对时间(分钟)"] = (
            (row["日志时间"] - start).total_seconds() / 60 if start else None
        )
        row["开播时间"] = start
        row["下播时间"] = s["下播时间"]
        row["直播时长"] = s["直播时长"]
    return data, sessions


def build_dataframe(data):
    """把解析结果转成 pandas DataFrame；无 pandas 时返回 None。"""
    import pandas as pd
    df = pd.DataFrame(data)
    if not df.empty:
        df = df.sort_values("日志时间").reset_index(drop=True)
    return df

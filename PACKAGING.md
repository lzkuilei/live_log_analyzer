# 打包与发布检查清单（PACKAGING.md）

本项目的 exe 打包流程、必查项和历史踩坑记录。每次重新打包前请通读一遍。

## 一、打包流程

```bash
python pack.py
```

一条命令完成：

1. **源码混淆**：`app.py`、`src/*.py` 用随机密钥异或加密成 `.enc`（每次打包密钥都换）
2. **资源收集**：`assets/`（图标）、`.streamlit/`（主题配置）、`CHANGELOG.md` 拷入打包目录
3. **生成加载器** `loader.py`：exe 启动时把 `.enc` 解密到临时目录 `lla_xxx` 运行
4. **PyInstaller 构建**（onedir 模式）：`--collect-all streamlit plotly fpdf2 openpyxl altair reportlab`

产物：`build_pack/dist/LiveLogAnalyzer/`（**整个文件夹**一起分发，不能只拷 exe）。

## 二、打包前必查项

- [ ] `app.py` 顶部 `APP_VERSION` 已递增（v1.0.9 → v1.0.10 …）
- [ ] `CHANGELOG.md` 顶部已新增本版本条目（exe 内侧边栏「ℹ️ 版本号」点开能看到）
- [ ] `assets/icon.png` 存在（favicon 和标题图标都读它）
- [ ] `python -m py_compile app.py src/*.py` 全部通过
- [ ] `python tests/test_analyzer.py` 全部通过

## 三、打包后必验项（缺一不可）

1. **服务能启动**：运行 exe，控制台显示「服务端口： xxxx」，HTTP 健康检查返回 `ok`
2. **资源文件已复制**：检查最新的 `%TEMP%\lla_xxx` 文件夹里是否有 `assets/icon.png`、`CHANGELOG.md`、`src/analyzer.py`——加载器会从 `_internal` 复制这三类文件到运行目录，新增资源文件时**必须同步修改 loader 的复制逻辑**
3. **页面无报错**：浏览器打开后标题、图标、中文界面正常
4. **核心功能抽查**：上传一份真实日志，场次数量、筛选、导出各点一遍

## 四、历史踩坑记录（新增功能前先看这里）

| 坑 | 教训 |
|---|---|
| 数据行 `session_idx` 用了 `len(sessions)-1` | 跨主播交错时数据串场（10-20 出现 3 场假场次）。归属必须用**当前主播所在场次**，已有回归测试 |
| PDF `_fmt` 未防 `pd.isna` | 无下播时间的场次导出 PDF 即崩。所有时间格式化都要走 `pd.isna` 检查 |
| fpdf2 未打进 exe / Edge 无头打印不可靠 | PDF 方案最终定为 **reportlab**（纯 Python，随 exe 打包）。不要换回 fpdf2 或依赖外部浏览器 |
| 加载器漏复制 `assets/` | exe 启动即报 icon `FileNotFoundError`。**新增资源文件夹时，pack.py 的 add-data 和 loader 复制逻辑要同时改** |
| loader.py 含中文未指定编码 | 默认 GBK 写入导致 PyInstaller UTF-8 读取失败。写文件必须 `encoding="utf-8"` |
| plotly `add_vline` 在日期轴上崩溃 | 事件标注线改用 `add_shape` + `add_annotation` |
| 端口 8501 被占 | 加载器已实现 `_free_port` 自动顺延；不要再写死端口 |
| 只换 exe 不换 `_internal` | exe 与数据包密钥、内容必须配套，**永远整文件夹替换** |

## 五、版本管理

- 每次修改：`APP_VERSION` 递增 + `CHANGELOG.md` 顶部加条目
- 确认稳定后：`git commit` → `git tag -f stable-baseline` → 推送
- exe 用户更新：整文件夹替换，侧边栏版本号核对为最新

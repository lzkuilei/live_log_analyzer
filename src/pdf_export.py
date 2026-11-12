# -*- coding: utf-8 -*-
"""PDF 导出（Edge 无头打印方案，无需 fpdf2）。

函数签名与原 fpdf2 版本一致，内部委托 report_html（HTML + Edge print-to-pdf）。
"""
from report_html import (  # noqa: F401
    _chart_single_png as _chart_single_png,
)
from report_html import pdf_single_session, pdf_session_compare, pdf_period_analysis  # noqa: F401

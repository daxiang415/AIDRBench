# 审计范围

- data_audit.json：69项核对、5,772个数值通过，涵盖保留的原生图表与11个重绘面板。
- portable_rebuild.txt：从ZIP解压到独立临时目录后运行panels-only入口，11张面板PNG与交付时逐字节一致；此项未再次执行LibreOffice导出。
- crop_log.json：考虑最终PDF缩放变换后的字体和裁剪检查，最小可提取字号约6.06 pt。
- pdf_text_audit.json：六张PDF都有文本操作符，未发现小于5pt的原始Tf字形。每图的9条提示来自扫描器不支持的压缩过滤器；实际字号由PyMuPDF应用坐标变换后复核，并辅以目视检查。
- static_preflight.txt：15项通过、4项提示、1项字体风格规则未通过。通用脚本要求无衬线字体，本轮为保留作者设计使用Liberation Serif及原生衬线字体；这项属有记录的风格例外。未据此声称通过全部自动风格规则或获得期刊终稿规范认证。

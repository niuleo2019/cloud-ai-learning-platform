# PDF 词根词缀截图接入

单词详情页已经支持显示 PDF 词根词缀截图。

后端读取：

```text
backend/data/pdf_roots_index.json
backend/data/pdf-root-images/
```

索引里有当前单词时，前端会在 `词根词缀书籍` 一栏展示对应截图。

## 渲染一页

```powershell
python backend\scripts\render_pdf_root_entry.py --word arbitrary --pdf hanbing_vol1 --page 120
```

## 渲染页面中的一块区域

`--clip` 使用归一化坐标：`x0 y0 x1 y1`，范围都是 `0` 到 `1`。

```powershell
python backend\scripts\render_pdf_root_entry.py `
  --word arbitrary `
  --pdf hanbing_vol1 `
  --page 120 `
  --clip 0.08 0.20 0.92 0.62 `
  --note "PDF root and affix explanation"
```

可用 PDF id：

```text
liuyinan
hanbing_vol1
hanbing_vol2
```

## 当前限制

这三本 PDF 基本是扫描图，当前电脑没有安装 Tesseract OCR，所以不能可靠自动判断某个单词在哪一页。

当前实现采用更稳定的方式：

1. 用 OCR 或人工找到单词所在页。
2. 用脚本把该页或该区域渲染成图片。
3. 脚本自动写入 `pdf_roots_index.json`。
4. 重新部署后，线上页面就能显示该单词的 PDF 截图。

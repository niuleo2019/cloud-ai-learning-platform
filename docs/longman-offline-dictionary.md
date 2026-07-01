# Longman 离线词典接入说明

这个项目现在已经有了 Longman 离线词典接口：

```text
GET /api/dictionary/lookup?word=evidence
```

前端搜索单词时会优先请求这个接口；如果本地 Longman 数据没有命中，再退回在线词典接口。

## 当前状态

后端默认读取：

```text
backend/data/longman_dictionary.json
```

现在仓库里先放了少量样例数据，方便页面和接口先跑通。你的完整 `.mdx/.mdd` 文件还没有全部导入，因为 Windows 本地安装 `python-lzo` 时缺少 LZO C 依赖。

## JSON 数据格式

导入后的 JSON 推荐长这样：

```json
{
  "evidence": {
    "html": "<b>evidence</b> ...",
    "text": "evidence noun. Facts or signs that show clearly that something exists or is true.",
    "audio": ""
  }
}
```

字段含义：

- `html`：Longman 原始解释 HTML，用于以后做更精细的排版。
- `text`：去掉 HTML 后的纯文本，当前页面主要显示这个字段。
- `audio`：发音文件地址，后续从 `.mdd` 提取音频后可以填入。

## 用 Docker 导出 MDX

因为 Windows 上编译 `python-lzo` 容易失败，推荐用 Docker 临时跑一次导出工具。

在项目根目录执行：

```powershell
docker build -f backend/scripts/Dockerfile.longman-export -t longman-mdx-export backend
```

然后把你的 MDX 文件挂进容器，导出为后端 JSON：

```powershell
docker run --rm `
  -v "D:\:/dict:ro" `
  -v "${PWD}\backend\data:/output" `
  longman-mdx-export `
  --mdx "/dict/Longman Dictionary of Contemporary English.mdx" `
  --output "/output/longman_dictionary.json"
```

先小规模测试 100 个词：

```powershell
docker run --rm `
  -v "D:\:/dict:ro" `
  -v "${PWD}\backend\data:/output" `
  longman-mdx-export `
  --mdx "/dict/Longman Dictionary of Contemporary English.mdx" `
  --output "/output/longman_dictionary.sample.json" `
  --limit 100
```

## 服务器部署

`docker-compose.server.yml` 已经设置：

```text
LONGMAN_DICTIONARY_PATH=/app/data/longman_dictionary.json
```

所以只要 `backend/data/longman_dictionary.json` 被导出并重新部署，服务器后端会自动读取完整词典。

部署后验证：

```powershell
curl.exe --noproxy "*" "http://devjourney868.tech/api/dictionary/lookup?word=evidence"
```

## 后续可做

`.mdd` 主要用于图片、CSS、音频等资源。当前阶段先接入 `.mdx` 的解释文本；下一步可以增加 `.mdd` 音频提取，把 `audio` 字段填成 `/api/dictionary/audio/...`，前端发音按钮就能播放 Longman 原始音频。

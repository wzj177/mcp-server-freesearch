# MCP Server FreeSearch

基于 SearXNG 的免费搜索 MCP 服务器，提供多种类型的网络搜索功能，无需 API 密钥。

## 功能特性

- **综合搜索** - 通用网页搜索，适用于查找信息、网站、文章等
- **新闻搜索** - 专门搜索新闻内容，获取最新事件和时事信息
- **图片搜索** - 搜索图片和视觉内容
- **视频搜索** - 搜索视频内容，包括教程、电影、直播等
- **地图搜索** - 地理位置查询，查找地点、地标或导航信息
- **音乐搜索** - 搜索音乐、歌曲、专辑或音频资源
- **IT搜索** - 专门搜索信息技术相关内容，适用于编程、系统、网络等技术问题
- **科学搜索** - 搜索科学信息，适用于物理、化学、生物、数学等学术内容
- **文件搜索** - 搜索可下载的公共文件，如 PDF、PPT、DOC 等格式
- **社交媒体搜索** - 搜索社交媒体平台的公开内容
- **速率限制** - 防止 API 滥用
- **全面的错误处理** - 提供详细的错误信息和故障排除建议
- **多种输出格式** - 支持 HTML 和 JSON 格式输出

## 系统要求

- Python 3.10 或更高版本
- MCP 兼容客户端（如 Claude Desktop、Cursor）
- 可访问的 SearXNG 实例

## 安装步骤

### 方式一：通过 uvx 安装（推荐）

```bash
uvx mcp-server-freesearch
```

### 方式二：从源码安装

1. 克隆此仓库：
   ```bash
   git clone <repository-url>
   cd mcp-server-freesearch
   ```

2. 安装依赖：
   ```bash
   uv venv
   source .venv/bin/activate  # Windows 系统: .venv\Scripts\activate
   uv pip install -e .
   ```

## 配置

### **建议** docker 搭建searx

- 构建
```shell
docker pull docker.io/searxng/searxng:latest
# Create directories for configuration and persistent data
$ mkdir -p ./searxng/config/ ./searxng/data/
$ cd ./searxng/

# Run the container
$ docker run --name searxng --replace -d \
    -p 8888:8080 \
    -v "./config/:/etc/searxng/" \
    -v "./data/:/var/cache/searxng/" \
    docker.io/searxng/searxng:latest
```
- 配置支持json输出
```shell
vim ./searxng/config/settings.yml
```

找到下面的format配置项，添加json
```yaml
  ...
  # formats: [html, csv, json, rss]
  formats:
    - html
    - json
```
---

### 设置所需的环境变量：

```bash
export SEARXNG_API_URL="https://searx.bndkt.io"  # SearXNG 实例 URL
export SEARXNG_COOKIE=""  # 可选：SearXNG Cookie
export SEARXNG_USER_AGENT="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"  # 可选：用户代理
export SEARXNG_REQUEST_TIMEOUT="10"  # 可选：请求超时时间（秒）
export ENV_FASTMCP_LOG_LEVEL="WARNING"  # 可选：日志级别
```

Windows 系统：
```cmd
set SEARXNG_API_URL=https://searx.bndkt.io
set SEARXNG_COOKIE=
set SEARXNG_USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
set SEARXNG_REQUEST_TIMEOUT=10
set ENV_FASTMCP_LOG_LEVEL=WARNING
```

## 使用方法

### 运行服务器

通过 uvx 运行（推荐）：
```bash
uvx mcp-server-freesearch
```

或者从源码直接运行：
```bash
python main.py
```

### 开发和测试

使用 MCP Inspector 进行测试：
```bash
npx @modelcontextprotocol/inspector python main.py
```

### 配置 Claude Desktop

将以下配置添加到 Claude Desktop 配置文件中：
- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "free-search": {
      "command": "uvx",
      "args": [
        "mcp-server-freesearch"
      ],
      "env": {
        "SEARXNG_API_URL": "https://searx.bndkt.io"
      }
    }
  }
}
```

如果你是从源码运行，则使用：
```json
{
  "mcpServers": {
    "free-search": {
      "command": "python",
      "args": [
        "/path/to/your/mcp-server-freesearch/main.py"
      ],
      "env": {
        "SEARXNG_API_URL": "https://searx.bndkt.io"
      }
    }
  }
}
```

## 可用工具

### 1. free_general_search
用于综合性搜索，最适合查找信息、网站、文章和一般内容。

示例："法国的首都是什么？" 或 "巧克力曲奇食谱"

### 2. free_news_search
专门用于新闻相关查询，最适合时事、最新发展和时效性信息。

示例："气候变化最新新闻" 或 "最新科技公告"

### 3. free_image_search
用于查找图片，最适合视觉内容查询。

示例："金毛犬图片" 或 "埃菲尔铁塔照片"

### 4. free_video_search
用于搜索视频内容，最适合教程、电影、直播或短视频。

示例："Python 入门视频" 或 "最新 NASA 纪录片"

### 5. free_map_search
用于地理位置查询，最适合查找地点、地标或导航相关信息。

示例："上海外滩在哪里？" 或 "最近的地铁站"

### 6. free_music_search
用于查找音乐、歌曲、专辑或音频资源。

示例："周杰伦青花瓷" 或 "贝多芬月光奏鸣曲"

### 7. free_it_search
用于搜索信息技术相关内容，最适合编程、系统、网络和安全等技术问题。

示例："如何修复蓝屏错误？" 或 "查看内存的 Linux 命令"

### 8. free_science_search
用于查找科学信息，适用于物理、化学、生物和数学等学术内容。

示例："光合作用的过程" 或 "黑洞是如何形成的"

### 9. free_file_search
用于查找可下载的公共文件，如 PDF、PPT、DOC 等格式。

示例："机器学习入门 PDF" 或 "年度财务报告下载"

### 10. free_social_media_search
用于搜索社交媒体平台的公开内容，适合捕获推文、讨论和社交活动。

示例："关于 AI 的热门推文" 或 "Reddit 远程工作讨论"

## 参数说明

所有搜索工具都支持以下参数：

- `query` (string, 必需): 搜索查询字符串
- `language` (string, 可选): 搜索语言，默认为 "zh"（中文）
- `safe_search` (int, 可选): 安全搜索等级，默认为 1（除图片、视频等为 0）
- `time_range` (string, 可选): 时间范围过滤器，默认为空
- `output_format` (string, 可选): 输出格式，"html" 或 "json"，默认为 "html"

## 输出格式

所有搜索结果都格式化为文本，每个结果项包含不同的字段：

- **综合搜索**: 标题、URL 和描述
- **新闻搜索**: 标题、URL、描述、发布日期和提供者
- **图片搜索**: 标题、来源 URL、图片 URL 和尺寸
- **视频搜索**: 标题、链接、描述、发布平台和时长（如适用）
- **其他类别**: 标题、链接、描述（以及与类别相关的附加信息）

## 故障排除

1. **"未找到搜索结果"** - 检查网络连接和 SearXNG 实例状态
2. **"Rate limit exceeded"** - 等待一段时间后重试，或检查速率限制设置
3. **连接错误** - 验证 SEARXNG_API_URL 是否正确且可访问
4. **JSON 解析错误** - 检查 SearXNG 实例是否返回有效的响应格式

## 发布到 PyPI

如果你想发布此包到 PyPI：

1. 安装构建工具：
   ```bash
   uv pip install build twine
   ```

2. 构建包：
   ```bash
   python -m build
   ```

3. 上传到 PyPI：
   ```bash
   python -m twine upload dist/*
   ```

注意：请确保在 `pyproject.toml` 中更新版本号和仓库 URL。


## 许可证

本项目基于 MIT 许可证开源。

## 贡献

欢迎提交 Issue 和 Pull Request 来改进此项目。

## 支持

如果遇到问题，请检查：
1. Python 版本是否符合要求
2. 所有依赖是否正确安装
3. 环境变量是否正确设置
4. SearXNG 实例是否可访问

更多技术支持，请提交 Issue 到项目仓库。
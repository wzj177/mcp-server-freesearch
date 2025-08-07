import asyncio
import os
import sys
import time
import logging
import json
import re
from html import escape

import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.types import TextContent
from bs4 import BeautifulSoup

load_dotenv()

# Ensure logs directory exists
logs_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "logs")
os.makedirs(logs_dir, exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(os.path.join(logs_dir, f"{time.strftime('%Y-%m-%d')}.log")),
        logging.StreamHandler(sys.stdout),
    ],
)
logger = logging.getLogger(__name__)

API_URL = os.environ.get("SEARXNG_API_URL", "https://searx.bndkt.io")
COOKIE = os.environ.get("SEARXNG_COOKIE", "")
USER_AGENT = os.environ.get(
    "SEARXNG_USER_AGENT",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
)
REQUEST_TIMEOUT = os.environ.get("SEARXNG_REQUEST_TIMEOUT", "10")
fastmcp_log_level = os.environ.get("ENV_FASTMCP_LOG_LEVEL", "WARNING")

# Initialize the FastMCP server
mcp = FastMCP(
    "free-search",
    log_level=fastmcp_log_level,
    instructions="""
# SearXNG Search MCP Server

This server provides tools for web search using a SearXNG instance.

It allows you to search web pages, news, images, videos, maps, music, IT information, scientific literature, documents, and social media content.

## Available Tools

### 1. free_general_search
Use this tool for general, comprehensive searches. It's best suited for finding information, websites, articles, and general content.

For example, "What is the capital of France?" or "Chocolate chip cookie recipes."

### 2. free_news_search
Use this tool specifically for news-related queries. Best for current events, latest developments, and timely information.

For example: "Latest news on climate change" or "Latest tech announcements"

### 3. free_image_search
Use this tool to find images. Best for visual content queries.

For example: "Pictures of golden retrievers" or "Pictures of the Eiffel Tower"

### 4. free_video_search
Use this tool to search for video content. Best for tutorials, movies, live streams, or short videos.

For example: "Python introductory video" or "Latest NASA documentaries"

### 5. free_map_search
Use this tool for geolocation queries. Best for finding places, landmarks, or navigation-related information.

For example: "Where is the Bund in Shanghai?" or "Nearest subway station"

### 6. free_music_search
Use this tool to find music, songs, albums, or audio resources.

For example: "Jay Chou's Blue and White Porcelain" or "Beethoven's Moonlight Sonata"

### 7. free_it_search
Use this tool to search for information technology-related content. Best for technical questions like programming, systems, networking, and security.

For example, "How do I fix a blue screen error?" or "Linux command to view memory."

### 8. free_science_search
Use this tool to find scientific information. Ideal for academic content like physics, chemistry, biology, and mathematics.

For example, "The process of photosynthesis" or "How black holes are formed."

### 9. free_file_search
Use this tool to find downloadable public files in formats like PDF, PPT, and DOC.

For example, "Introduction to Machine Learning PDF" or "Annual Financial Report Download."

### 10. free_social_media_search
Use this tool to search for public content on social media platforms. Ideal for capturing tweets, discussions, and social activity.

For example: "Top tweets about AI" or "Reddit discussions about remote work"

## Usage Guidelines

- Always check if your query is better suited for General, News, Images, or other specialized search categories.

- For current events and recent developments, prioritize News Search.
- For visual content, use Image Search; for video content, use Video Search.
- For technical questions, IT Search is recommended; for academic questions, use Science Search.
- For best results, keep your query concise and specific.
- All searches are forwarded through the SearXNG instance; performance depends on the instance status (typically, there is no rate limit).

## Output Format

All search results are formatted as text, with each result item having distinct sections, including:

- General Search: Title, URL, and Description
- News Search: Title, URL, Description, Publication Date, and Provider
- Image Search: Title, Source URL, Image URL, and Size
- Video Search: Title, Link, Description, Publication Platform, and Duration (if applicable)
- Other Categories: Title, Link, Description (and additional information related to the category)

If SEARXNG_API_URL is not configured or is invalid, a corresponding error message will be returned.

---
    """,
)

# Validate timeout value
REQUEST_TIMEOUT = int(REQUEST_TIMEOUT)

HEADERS = {
    "User-Agent": USER_AGENT,
    "content-type": "application/x-www-form-urlencoded",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
    "Cookie": COOKIE,
}

# Rate limiting
RATE_LIMIT = {"per_second": 1, "per_month": 15000}
request_count = {"second": 0, "month": 0, "last_reset": time.time()}


def check_rate_limit():
    """
    Check if the rate limit has been exceeded.
    Returns True if request is allowed, False otherwise.
    """
    now = time.time()
    current_month = time.strftime("%Y-%m", time.localtime(now))
    last_reset_month = time.strftime(
        "%Y-%m", time.localtime(request_count["last_reset"])
    )

    # Reset second counter every second
    if now - request_count["last_reset"] >= 1:
        request_count["second"] = 0
        request_count["last_reset"] = now

    # Reset monthly counter when month changes
    if current_month != last_reset_month:
        request_count["month"] = 0

    if (
        request_count["second"] >= RATE_LIMIT["per_second"]
        or request_count["month"] >= RATE_LIMIT["per_month"]
    ):
        return False

    request_count["second"] += 1
    request_count["month"] += 1
    return True


def merge_headers(headers):
    """
    Merge headers with default headers.
    """
    return {**HEADERS, **headers}


def validate_environment_vars():
    """
    Validate that all required environment variables are set.
    """
    required_vars = ["SEARXNG_API_URL"]
    missing_vars = [var for var in required_vars if not os.environ.get(var)]

    if missing_vars:
        raise EnvironmentError(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )


# Tool definitions
@mcp.tool(
    description="""
综合搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认1
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the search results.
"""
)
async def free_general_search(
    query: str,
    language="auto",
    safe_search=1,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "general", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
新闻搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认1
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the news search results.
"""
)
async def free_news_search(
    query: str,
    language="auto",
    safe_search=1,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "news", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
图片搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the image search results.
"""
)
async def free_image_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "images", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
视频搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the video search results.
"""
)
async def free_video_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "videos", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
地图搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the map search results.
"""
)
async def free_map_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "map", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
音乐搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the music search results.
"""
)
async def free_music_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "music", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
信息技术搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the IT search results.
"""
)
async def free_it_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "it", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
科学搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the science search results.
"""
)
async def free_science_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "science", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
文件搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the file search results.
"""
)
async def free_file_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "files", language, safe_search, time_range, output_format
    )


@mcp.tool(
    description="""
社交媒体搜索
    Args:
        query (str): 搜索查询
        language (str): 搜索语言，默认中文
        safe_search (int): 安全搜索等级，默认0
        time_range (str): 时间范围，默认空
        output_format (str): 输出格式，默认html
    Returns:
        Text content with the social media search results.
"""
)
async def free_social_media_search(
    query: str,
    language="auto",
    safe_search=0,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    return await _perform_search(
        query, "social media", language, safe_search, time_range, output_format
    )


# 通用搜索函数，避免代码重复
async def _perform_search(
    query: str,
    category: str,
    language="auto",
    safe_search=1,
    time_range="",
    output_format: str = "html",
) -> TextContent:
    """
    通用搜索处理函数
    """
    if not query or not isinstance(query, str):
        raise ValueError("Query parameter is required and must be a string")

    if not API_URL:
        raise ValueError("SEARXNG_API_URL environment variable is not set")

    if not check_rate_limit():
        raise RuntimeError("Rate limit exceeded")

    headers = merge_headers({})
    params = {
        "q": query,
        "language": language,
        "time_range": time_range,
        "safe_search": safe_search,
        "categories": category,
        "theme": "simple",
        "format": "html" if "searx.bndkt.io" in API_URL else "json",
    }

    api_url = API_URL
    if api_url.endswith("/"):
        api_url = api_url[:-1]

    search_url = f"{api_url}/search"

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                search_url, data=params, headers=headers, timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()
            if params["format"] == "json":
                data = response.json()
            else:
                data = response.text

        if params["format"] == "json":
            return _parse_response_json(data, output_format, category)
        else:
            # 解析HTML响应
            return _parse_response_html(data, output_format, category)

    except httpx.HTTPError as e:
        logger.error(f"HTTP Error in {category} search: {str(e)}")
        raise RuntimeError(f"HTTP Error: {str(e)}")
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in {category} search: {str(e)}")
        raise RuntimeError(f"JSON decode failed: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error in {category} search: {str(e)}")
        raise RuntimeError(f"Unexpected error: {str(e)}")


def _parse_response_json(data: dict, output_format: str, category: str) -> TextContent:
    """
    解析JSON响应数据
    """
    if "results" not in data or not data["results"]:
        return TextContent(type="text", text="未找到相关结果")

    # 根据不同类别解析结果
    if category in [
        "images",
        "videos",
        "map",
        "music",
        "news",
        "it",
        "science",
        "files",
        "social media",
    ]:
        return _parse_specialized_json_results(data["results"], category, output_format)
    else:
        # 通用搜索结果解析（适用于general等）
        return _parse_general_json_results(data["results"], output_format)


def _parse_response_html(data: str, output_format: str, category: str) -> TextContent:
    """
    解析HTML响应数据
    """
    # 检查是否为无结果页面
    if """<div class="dialog-error-block" role="alert">""" in data:
        return TextContent(
            type="text",
            text="未找到相关结果。您可以尝试：\n- 使用不同的关键词\n- 简化搜索查询\n- 检查拼写错误",
        )

    # 使用 BeautifulSoup 解析 HTML
    soup = BeautifulSoup(data, "html.parser")

    # 找到 id="urls" 的 div
    urls_div = soup.find("div", id="urls")
    if not urls_div:
        return TextContent(type="text", text="未找到搜索结果")

    # 提取所有 article 标签
    articles = urls_div.find_all("article", class_="result")

    if not articles:
        return TextContent(type="text", text="未找到搜索结果")

    # 根据不同类别解析结果
    if category in [
        "images",
        "videos",
        "map",
        "music",
        "news",
        "it",
        "science",
        "files",
        "social media",
    ]:
        return _parse_specialized_html_results(articles, category, output_format)
    else:
        # 通用搜索结果解析（适用于general等）
        return _parse_general_html_results(articles, output_format)


def _parse_general_html_results(articles: list, output_format: str) -> TextContent:
    """
    解析通用搜索结果（适用于general、it、science、files、social media等）
    """
    parsed_results = []

    for article in articles:
        # 提取标题和链接 - 查找 h3 > a 结构
        title_link = article.find("h3")
        if title_link:
            link_tag = title_link.find("a", href=True)
            if link_tag:
                url = link_tag["href"]
                title = link_tag.get_text(strip=True)
            else:
                continue
        else:
            continue

        # 提取描述/内容 - 查找 p.content
        description = ""
        content_p = article.find("p", class_="content")
        if content_p:
            description = content_p.get_text(strip=True)

        # 提取引擎信息
        engines = []
        engines_div = article.find("div", class_="engines")
        if engines_div:
            engine_spans = engines_div.find_all("span")
            engines = [
                span.get_text(strip=True)
                for span in engine_spans
                if span.get_text(strip=True)
            ]

        if output_format == "json":
            result_data = {
                "title": escape(title),
                "url": escape(url),
                "description": escape(description),
            }
            if engines:
                result_data["engines"] = engines
            parsed_results.append(result_data)
        else:
            # HTML格式输出
            engines_info = (
                f"<small>搜索引擎: {', '.join(engines)}</small><br>" if engines else ""
            )
            html = (
                f"<div style='margin-bottom: 1.5em; border-left: 3px solid #007acc; padding-left: 15px;'>"
                f"<h3><a href='{escape(url)}' target='_blank' style='color: #007acc; text-decoration: none;'>{escape(title)}</a></h3>"
                f"<p style='color: #666; margin: 5px 0;'>{escape(description)}</p>"
                f"{engines_info}"
                f"<small style='color: #999;'>{escape(url)}</small>"
                f"</div>"
            )
            parsed_results.append(html)

    if output_format == "json":
        return TextContent(
            type="text", text=json.dumps(parsed_results, ensure_ascii=False, indent=2)
        )
    else:
        return TextContent(type="text", text="\n".join(parsed_results))


def _parse_specialized_html_results(
    articles: list, category: str, output_format: str
) -> TextContent:
    """
    解析专门类别的搜索结果（图片、视频、地图、音乐、新闻）
    """
    parsed_results = []

    for article in articles:
        if category == "images":
            parsed_result = _parse_image_result(article, output_format)
        elif category == "videos":
            parsed_result = _parse_video_result(article, output_format)
        elif category == "map":
            parsed_result = _parse_map_result(article, output_format)
        elif category == "music":
            parsed_result = _parse_music_result(article, output_format)
        elif category == "news":
            parsed_result = _parse_news_result(article, output_format)
        elif category == "it":
            parsed_result = _parse_it_result(article, output_format)
        elif category == "science":
            parsed_result = _parse_science_result(article, output_format)
        elif category == "files":
            parsed_result = _parse_files_result(article, output_format)
        elif category == "social media":
            parsed_result = _parse_social_media_result(article, output_format)
        else:
            continue

        if parsed_result:
            parsed_results.append(parsed_result)

    if output_format == "json":
        return TextContent(
            type="text", text=json.dumps(parsed_results, ensure_ascii=False, indent=2)
        )
    else:
        return TextContent(type="text", text="\n".join(parsed_results))


def _parse_image_result(article, output_format: str) -> dict | str:
    """解析图片搜索结果 - 基于实际 HTML 结构"""
    # 提取主链接
    main_link = article.find("a", href=True)
    if not main_link:
        return None

    url = main_link["href"]

    # 提取图片信息
    img_tag = article.find("img", class_="image_thumbnail")
    if not img_tag:
        return None

    thumbnail_url = img_tag.get("src", "")
    title = img_tag.get("alt", "")

    # 提取来源信息
    source_span = article.find("span", class_="source")
    source = source_span.get_text(strip=True) if source_span else ""

    # 提取标题（如果alt为空，尝试从title span获取）
    if not title:
        title_span = article.find("span", class_="title")
        if title_span:
            title = title_span.get_text(strip=True)

    # 提取引擎信息
    engine = ""
    result_engine = article.find("p", class_="result-engine")
    if result_engine:
        engine_span = result_engine.find("span")
        if engine_span and engine_span.next_sibling:
            engine = engine_span.next_sibling.strip()

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail_url),
            "source": escape(source),
            "engine": engine,
            "type": "image",
        }
    else:
        meta_info = []
        if source:
            meta_info.append(f"来源: {source}")
        if engine:
            meta_info.append(f"引擎: {engine}")

        meta_html = f"<small>{' | '.join(meta_info)}</small><br>" if meta_info else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<img src='{escape(thumbnail_url)}' style='max-width: 200px; max-height: 200px; display: block; margin: 10px 0;' alt='{escape(title)}' />"
            f"{meta_html}"
            f"</div>"
        )


def _parse_video_result(article, output_format: str) -> dict | str:
    """解析视频搜索结果 - 基于videos.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取缩略图
    img_tag = article.find("img", class_="thumbnail")
    thumbnail = img_tag["src"] if img_tag else ""

    # 提取时长
    length = ""
    length_div = article.find("div", class_="result_length")
    if length_div:
        length = length_div.get_text(strip=True).replace("长度: ", "")

    # 提取作者
    author = ""
    author_div = article.find("div", class_="result_author")
    if author_div:
        author = author_div.get_text(strip=True).replace("作者: ", "")

    # 提取引擎信息
    # engine = ""
    # engines_div = article.find("div", class_="engines")
    # if engines_div:
    #     engine_span = engines_div.find("span")
    #     if engine_span:
    #         engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail),
            # "engine": engine,
            "type": "video",
        }
        if length:
            result["length"] = length
        if author:
            result["author"] = author
        return result
    else:
        thumbnail_html = (
            f"<img src='{escape(thumbnail)}' style='width:120px;height:90px;float:left;margin-right:10px;'>"
            if thumbnail
            else ""
        )

        meta_info = []
        if length:
            meta_info.append(f"时长: {length}")
        if author:
            meta_info.append(f"作者: {author}")
        # if engine:
        #     meta_info.append(f"引擎: {engine}")

        meta_html = f"<small>{' | '.join(meta_info)}</small><br>" if meta_info else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px; clear: both;'>"
            f"{thumbnail_html}"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{meta_html}"
            f"<div style='clear: both;'></div>"
            f"</div>"
        )


def _parse_news_result(article, output_format: str) -> dict | str:
    """解析新闻搜索结果 - 基于news.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取日期和来源
    date_source = ""
    highlight_div = article.find("div", class_="highlight")
    if highlight_div:
        date_source = highlight_div.get_text(strip=True)

    # 提取内容描述
    content = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content = content_p.get_text(strip=True)

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "dateSource": escape(date_source),
            "engine": engine,
            "type": "news",
        }
    else:
        date_source_html = (
            f"<small>{escape(date_source)}</small><br>" if date_source else ""
        )
        engine_html = f"<small>引擎: {engine}</small><br>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{date_source_html}"
            f"<p>{escape(content)}</p>"
            f"{engine_html}"
            f"</div>"
        )


def _parse_music_result(article, output_format: str) -> dict | str:
    """解析音乐搜索结果 - 基于music.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取缩略图
    img_tag = article.find("img")
    thumbnail = img_tag["src"] if img_tag else ""

    # 提取发布日期 - 在content中查找Published:
    published = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content_text = content_p.get_text()
        if "Published:" in content_text:
            published = content_text.split("Published:")[1].strip()

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail),
            "engine": engine,
            "type": "music",
        }
        if published:
            result["published"] = published
        return result
    else:
        img_html = (
            f"<img src='{thumbnail}' style='width: 80px; height: 80px; float: left; margin-right: 10px;' alt='{escape(title)}' />"
            if thumbnail
            else ""
        )

        meta_info = []
        if published:
            meta_info.append(f"发布: {published}")
        if engine:
            meta_info.append(f"引擎: {engine}")

        meta_html = f"<small>{' | '.join(meta_info)}</small>" if meta_info else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px; overflow: hidden;'>"
            f"{img_html}"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{meta_html}"
            f"<div style='clear: both;'></div>"
            f"</div>"
        )


def _parse_map_result(article, output_format: str) -> dict | str:
    """解析地图搜索结果 - 基于map.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取表格中的详细信息
    table_data = {}
    table = article.find("table")
    if table:
        rows = table.find_all("tr")
        for row in rows:
            cells = row.find_all("td")
            if len(cells) >= 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                if key and value:
                    table_data[key] = value

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "engine": engine,
            "type": "map",
        }
        if table_data:
            result["details"] = table_data
        return result
    else:
        # 构建详细信息显示
        details_html = ""
        if table_data:
            details_parts = []
            for key, value in table_data.items():
                details_parts.append(f"{escape(key)}: {escape(value)}")
            details_html = f"<p><small>{' | '.join(details_parts)}</small></p>"

        engine_html = f"<small>引擎: {engine}</small>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{details_html}"
            f"{engine_html}"
            f"</div>"
        )


def _parse_it_result(article, output_format: str) -> dict | str:
    """解析IT搜索结果 - 基于it.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取内容描述
    content = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content = content_p.get_text(strip=True)

    # 提取attributes部分（IT特有的包信息）
    attributes = {}
    attr_div = article.find("div", class_="attributes")
    if attr_div:
        attr_text = attr_div.get_text()

        # 从文本中提取信息
        import re

        package_match = re.search(r"package:\s*([^\n]+)", attr_text)
        if package_match:
            attributes["package"] = package_match.group(1).strip()

        maintainer_match = re.search(r"maintainer:\s*([^\n]+)", attr_text)
        if maintainer_match:
            attributes["maintainer"] = maintainer_match.group(1).strip()

        version_match = re.search(r"version:\s*([^\n]+)", attr_text)
        if version_match:
            attributes["version"] = version_match.group(1).strip()

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "engine": engine,
            "type": "it",
        }
        if attributes:
            result["attributes"] = attributes
        return result
    else:
        # 构建属性信息显示
        attr_html = ""
        if attributes:
            attr_parts = []
            for key, value in attributes.items():
                attr_parts.append(f"{key}: {escape(value)}")
            attr_html = f"<p><small>{' | '.join(attr_parts)}</small></p>"

        engine_html = f"<small>引擎: {engine}</small>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"{attr_html}"
            f"{engine_html}"
            f"</div>"
        )


def _parse_science_result(article, output_format: str) -> dict | str:
    """解析科学搜索结果 - 基于science.html实际结构（类似通用搜索）"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取内容描述
    content = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content = content_p.get_text(strip=True)

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "engine": engine,
            "type": "science",
        }
    else:
        engine_html = f"<small>引擎: {engine}</small>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"{engine_html}"
            f"</div>"
        )


def _parse_files_result(article, output_format: str) -> dict | str:
    """解析文件搜索结果 - 基于files.html实际结构"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取内容描述
    content = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content = content_p.get_text(strip=True)

    # 提取文件特有信息（如磁力链接、文件大小、种子信息等）
    file_info = {}

    # 从整个article文本中搜索信息
    article_text = article.get_text()

    # 提取Seeds信息
    import re

    seeds_match = re.search(r"Seeds:\s*(\d+)", article_text)
    if seeds_match:
        file_info["seeds"] = seeds_match.group(1)

    # 提取Leeches信息
    leeches_match = re.search(r"Leeches:\s*(\d+)", article_text)
    if leeches_match:
        file_info["leeches"] = leeches_match.group(1)

    # 提取文件大小
    size_match = re.search(r"Size:\s*([^\n]+)", article_text)
    if size_match:
        file_info["size"] = size_match.group(1).strip()

    # 检查是否包含磁力链接
    if "magnet:" in article_text:
        file_info["has_magnet"] = True

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "engine": engine,
            "type": "file",
        }
        if file_info:
            result["fileInfo"] = file_info
        return result
    else:
        # 构建文件信息显示
        file_info_html = ""
        if file_info:
            info_parts = []
            if file_info.get("size"):
                info_parts.append(f"大小: {file_info['size']}")
            if file_info.get("seeds"):
                info_parts.append(f"种子: {file_info['seeds']}")
            if file_info.get("leeches"):
                info_parts.append(f"下载: {file_info['leeches']}")
            if file_info.get("has_magnet"):
                info_parts.append("包含磁力链接")

            if info_parts:
                file_info_html = f"<p><small>{' | '.join(info_parts)}</small></p>"

        engine_html = f"<small>引擎: {engine}</small>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"{file_info_html}"
            f"{engine_html}"
            f"</div>"
        )


def _parse_social_media_result(article, output_format: str) -> dict | str:
    """解析社交媒体搜索结果 - 基于social media.html实际结构（类似通用搜索）"""
    # 提取标题和链接
    title_link = article.find("h3")
    if not title_link:
        return None

    link_tag = title_link.find("a", href=True)
    if not link_tag:
        return None

    url = link_tag["href"]
    title = link_tag.get_text(strip=True)

    # 提取内容描述
    content = ""
    content_p = article.find("p", class_="content")
    if content_p:
        content = content_p.get_text(strip=True)

    # 提取hashtag信息（如果有的话）
    import re

    hashtags = re.findall(r"#(\w+)", content)

    # 提取引擎信息
    engine = ""
    engines_div = article.find("div", class_="engines")
    if engines_div:
        engine_span = engines_div.find("span")
        if engine_span:
            engine = engine_span.get_text(strip=True)

    if output_format == "json":
        result = {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "engine": engine,
            "type": "social_media",
        }
        if hashtags:
            result["hashtags"] = hashtags
        return result
    else:
        hashtags_html = ""
        if hashtags:
            hashtags_html = f"<p><small>标签: {', '.join(['#' + tag for tag in hashtags])}</small></p>"

        engine_html = f"<small>引擎: {engine}</small>" if engine else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"{hashtags_html}"
            f"{engine_html}"
            f"</div>"
        )


def _parse_general_json_results(results: list, output_format: str) -> TextContent:
    """
    解析通用JSON搜索结果（适用于general、it、science、files、social media等）
    """
    parsed_results = []

    for result in results:
        title = result.get("title", "")
        url = result.get("url", "")
        description = result.get("content", "")
        engines = result.get("engines", [])

        if output_format == "json":
            result_data = {
                "title": escape(title),
                "url": escape(url),
                "description": escape(description),
            }
            if engines:
                result_data["engines"] = engines
            parsed_results.append(result_data)
        else:
            # HTML格式输出
            engines_info = (
                f"<small>搜索引擎: {', '.join(engines)}</small><br>" if engines else ""
            )
            html = (
                f"<div style='margin-bottom: 1.5em; border-left: 3px solid #007acc; padding-left: 15px;'>"
                f"<h3><a href='{escape(url)}' target='_blank' style='color: #007acc; text-decoration: none;'>{escape(title)}</a></h3>"
                f"<p style='color: #666; margin: 5px 0;'>{escape(description)}</p>"
                f"{engines_info}"
                f"<small style='color: #999;'>{escape(url)}</small>"
                f"</div>"
            )
            parsed_results.append(html)

    if output_format == "json":
        return TextContent(
            type="text", text=json.dumps(parsed_results, ensure_ascii=False, indent=2)
        )
    else:
        return TextContent(type="text", text="\n".join(parsed_results))


def _parse_specialized_json_results(
    results: list, category: str, output_format: str
) -> TextContent:
    """
    解析专门类别的JSON搜索结果（图片、视频、地图、音乐、新闻）
    """
    parsed_results = []

    for result in results:
        if category == "images":
            parsed_result = _parse_image_json_result(result, output_format)
        elif category == "videos":
            parsed_result = _parse_video_json_result(result, output_format)
        elif category == "map":
            parsed_result = _parse_map_json_result(result, output_format)
        elif category == "music":
            parsed_result = _parse_music_json_result(result, output_format)
        elif category == "news":
            parsed_result = _parse_news_json_result(result, output_format)
        elif category == "it":
            parsed_result = _parse_it_json_result(result, output_format)
        elif category == "science":
            parsed_result = _parse_science_json_result(result, output_format)
        elif category == "files":
            parsed_result = _parse_files_json_result(result, output_format)
        elif category == "social media":
            parsed_result = _parse_social_media_json_result(result, output_format)
        else:
            continue

        if parsed_result:
            parsed_results.append(parsed_result)

    if output_format == "json":
        return TextContent(
            type="text", text=json.dumps(parsed_results, ensure_ascii=False, indent=2)
        )
    else:
        return TextContent(type="text", text="\n".join(parsed_results))


def _parse_image_json_result(result: dict, output_format: str) -> dict | str:
    """解析图片JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    img_src = result.get("img_src", "")
    thumbnail_src = result.get("thumbnail_src", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail_src),
            "img_src": escape(img_src),
            "type": "image",
        }
    else:
        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<img src='{escape(thumbnail_src)}' style='max-width: 200px; max-height: 200px; display: block; margin: 10px 0;' alt='{escape(title)}' />"
            f"</div>"
        )


def _parse_video_json_result(result: dict, output_format: str) -> dict | str:
    """解析视频JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    thumbnail = result.get("thumbnail", "")
    length = result.get("length", "")
    published_date = result.get("publishedDate", "")

    if output_format == "json":
        result_data = {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail),
            "type": "video",
        }
        if length:
            result_data["length"] = length
        if published_date:
            result_data["published"] = published_date
        return result_data
    else:
        thumbnail_html = (
            f"<img src='{escape(thumbnail)}' style='width:120px;height:90px;float:left;margin-right:10px;'>"
            if thumbnail
            else ""
        )

        meta_info = []
        if length:
            meta_info.append(f"时长: {length}")
        if published_date:
            meta_info.append(f"发布: {published_date}")

        meta_html = f"<small>{' | '.join(meta_info)}</small><br>" if meta_info else ""

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px; clear: both;'>"
            f"{thumbnail_html}"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{meta_html}"
            f"<div style='clear: both;'></div>"
            f"</div>"
        )


def _parse_news_json_result(result: dict, output_format: str) -> dict | str:
    """解析新闻JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")
    published_date = result.get("publishedDate", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "published": published_date,
            "type": "news",
        }
    else:
        date_html = (
            f"<small>{escape(published_date)}</small><br>" if published_date else ""
        )

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{date_html}"
            f"<p>{escape(content)}</p>"
            f"</div>"
        )


def _parse_music_json_result(result: dict, output_format: str) -> dict | str:
    """解析音乐JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    thumbnail = result.get("thumbnail", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "thumbnail": escape(thumbnail),
            "type": "music",
        }
    else:
        img_html = (
            f"<img src='{thumbnail}' style='width: 80px; height: 80px; float: left; margin-right: 10px;' alt='{escape(title)}' />"
            if thumbnail
            else ""
        )

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px; overflow: hidden;'>"
            f"{img_html}"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<div style='clear: both;'></div>"
            f"</div>"
        )


def _parse_map_json_result(result: dict, output_format: str) -> dict | str:
    """解析地图JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    address = result.get("address", {})
    longitude = result.get("longitude", "")
    latitude = result.get("latitude", "")

    if output_format == "json":
        result_data = {
            "title": escape(title),
            "url": escape(url),
            "type": "map",
        }
        if address:
            result_data["address"] = address
        if longitude:
            result_data["longitude"] = longitude
        if latitude:
            result_data["latitude"] = latitude
        return result_data
    else:
        # 构建详细信息显示
        details_html = ""
        if address or longitude or latitude:
            details_parts = []
            if address:
                details_parts.append(f"地址: {escape(str(address))}")
            if longitude and latitude:
                details_parts.append(f"坐标: {longitude}, {latitude}")
            details_html = f"<p><small>{' | '.join(details_parts)}</small></p>"

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"{details_html}"
            f"</div>"
        )


def _parse_it_json_result(result: dict, output_format: str) -> dict | str:
    """解析IT JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "type": "it",
        }
    else:
        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"</div>"
        )


def _parse_science_json_result(result: dict, output_format: str) -> dict | str:
    """解析科学JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "type": "science",
        }
    else:
        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"</div>"
        )


def _parse_files_json_result(result: dict, output_format: str) -> dict | str:
    """解析文件JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")

    if output_format == "json":
        return {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "type": "file",
        }
    else:
        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"</div>"
        )


def _parse_social_media_json_result(result: dict, output_format: str) -> dict | str:
    """解析社交媒体JSON搜索结果"""
    title = result.get("title", "")
    url = result.get("url", "")
    content = result.get("content", "")

    # 提取hashtag信息（如果有的话）
    import re

    hashtags = re.findall(r"#(\w+)", content)

    if output_format == "json":
        result_data = {
            "title": escape(title),
            "url": escape(url),
            "content": escape(content),
            "type": "social_media",
        }
        if hashtags:
            result_data["hashtags"] = hashtags
        return result_data
    else:
        hashtags_html = ""
        if hashtags:
            hashtags_html = f"<p><small>标签: {', '.join(['#' + tag for tag in hashtags])}</small></p>"

        return (
            f"<div style='margin-bottom: 1.5em; border: 1px solid #ddd; padding: 10px;'>"
            f"<h4><a href='{escape(url)}' target='_blank'>{escape(title)}</a></h4>"
            f"<p>{escape(content)}</p>"
            f"{hashtags_html}"
            f"</div>"
        )

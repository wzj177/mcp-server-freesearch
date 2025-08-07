## 文本搜索

```
http://localhost:28087/search?q=%E5%9B%9B%E5%B7%9D%E6%B1%9F%E6%B2%B9%E9%9C%B8%E5%87%8C%E4%BA%8B%E4%BB%B6&language=auto&time_range=&safesearch=0&categories=general
```

```
搜索接口
curl 'http://localhost:28087/search' \
  -H 'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Cache-Control: max-age=0' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: application/x-www-form-urlencoded' \
  -b 'Pycharm-14e1ce71=212e4f48-4ab1-44ce-aaca-d8d5e6ec2aeb' \
  -H 'Origin: null' \
  -H 'Sec-Fetch-Dest: document' \
  -H 'Sec-Fetch-Mode: navigate' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'Sec-Fetch-User: ?1' \
  -H 'Upgrade-Insecure-Requests: 1' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw 'q=%E5%9B%9B%E5%B7%9D%E6%B1%9F%E6%B2%B9%E9%9C%B8%E5%87%8C%E4%BA%8B%E4%BB%B6&categories=images&language=auto&time_range=day&safesearch=0&theme=simple&format=json'
```


### 支持的category

- general: 综合搜索
- images：图片搜索
- videos：视频搜索
- news： 新闻搜索
- map: 地图搜索
- music: 音乐搜索
- it: 信息技术搜索
- science：科学搜索
- files：文件搜索
- social media: 社交媒体搜索

### 没有结果的返回


```
抱歉！

未找到结果，您可以尝试：

刷新页面。
（在上方）对其他查询进行搜索，或选择其他类别。
更改“首选项”中使用的搜索引擎： /preferences
切换至另一个 SearXNG 实例： https://searx.space
```

### 自动补全接口


```
curl 'http://localhost:28087/autocompleter' \
  -H 'Accept: */*' \
  -H 'Accept-Language: zh-CN,zh;q=0.9' \
  -H 'Connection: keep-alive' \
  -H 'Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryUfAJXWP8je2ODXWe' \
  -b 'Pycharm-14e1ce71=212e4f48-4ab1-44ce-aaca-d8d5e6ec2aeb; categories=images; language=zh; locale=zh-Hans-CN; autocomplete=baidu; favicon_resolver=; image_proxy=0; method=POST; safesearch=0; theme=simple; results_on_new_tab=0; doi_resolver=oadoi.org; simple_style=auto; center_alignment=0; advanced_search=0; query_in_title=0; infinite_scroll=0; search_on_category_select=1; hotkeys=default; url_formatting=pretty; disabled_engines=; enabled_engines=; disabled_plugins=; enabled_plugins=; tokens=' \
  -H 'Origin: http://localhost:28087' \
  -H 'Sec-Fetch-Dest: empty' \
  -H 'Sec-Fetch-Mode: cors' \
  -H 'Sec-Fetch-Site: same-origin' \
  -H 'User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36' \
  -H 'sec-ch-ua: "Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"' \
  -H 'sec-ch-ua-mobile: ?0' \
  -H 'sec-ch-ua-platform: "macOS"' \
  --data-raw $'------WebKitFormBoundaryUfAJXWP8je2ODXWe\r\nContent-Disposition: form-data; name="q"\r\n\r\nma s\r\n------WebKitFormBoundaryUfAJXWP8je2ODXWe--\r\n'
```
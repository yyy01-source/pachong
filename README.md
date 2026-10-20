# CCTV 新闻爬虫项目

本项目是一个基于 Python 的新闻爬虫，支持定时抓取与数据库存储。

## 当前版本 (v1 基础版)
- 文件：`news.py`
- 功能：使用 `urllib` 与 `BeautifulSoup` 静态抓取 RSS 源，存入 SQLite。

## 使用方法
- 手动抓取：`python news.py crawl`
- 查看数据：`python news.py show`
- 定时任务：`python news.py daemon`
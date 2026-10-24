# 新闻与热搜爬虫项目

本项目是一个基于 Python 的综合爬虫项目，包含基础静态网页抓取与进阶动态接口抓取及反爬策略。

## 版本迭代说明

### v1 基础版 (`news.py`)
- **功能**：使用 `urllib` 与 `BeautifulSoup` 静态抓取中新网 RSS 源。
- **特性**：支持存入 SQLite 数据库，命令行参数解析（crawl/show/daemon），以及后台定时调度。

### v2 进阶版 (`news_v2.py`)
- **功能**：针对动态网页进行升级，逆向分析并抓取 Bilibili 动态热搜接口数据。
- **反爬机制**：
  1. 完善 `Headers` 伪装。
  2. 基于时间戳取模的动态随机休眠，防频率检测。
  3. 引入 `tenacity` 库实现网络异常指数退避重试。

## 使用方法

**运行 v1 基础版 (静态抓取)：**
- 手动抓取：`python news.py crawl`
- 查看数据：`python news.py show`
- 定时任务：`python news.py daemon`

**运行 v2 进阶版 (动态接口抓取)：**
- 手动抓取：`python news_v2.py crawl`
- 查看数据：`python news_v2.py show`

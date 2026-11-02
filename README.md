# 爬虫项目

本项目是一个基于 Python 的综合爬虫实战项目。涵盖了从基础静态网页抓取、API 逆向接口请求、到复杂动态网页渲染及浏览器交互式操作的全流程。

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

### v3 交互版 (`news_v3.py`)
- **功能**：使用 Selenium 模拟真实用户在当当网进行“搜索”交互，自动翻页抓取前 5 页的搜索结果。
- **技术点**：
  1. 使用 send_keys 模拟打字，click 模拟点击。
  2. WebDriverWait 显式等待（配合 staleness_of 防抖翻页）。
  3. CDP 注入抹除 webdriver 自动化特征。
- **数据存储**：数据去重后存入 dangdang_books.db 数据库。



## 使用方法

**运行 v1 基础版 (静态抓取)：**
- 手动抓取：`python news.py crawl`
- 查看数据：`python news.py show`
- 定时任务：`python news.py daemon`

**运行 v2 进阶版 (动态接口抓取)：**
- 手动抓取：`python news_v2.py crawl`
- 查看数据：`python news_v2.py show`

**运行 v3 交互版 (模拟用户操作)：**
- 运行命令：`python news_v3.py crawl`
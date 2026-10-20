import time
from datetime import datetime
import logging #日志模块
import argparse #命令行参数解析模块
import sqlite3 #数据库工具
from urllib.request import urlopen, Request #发请求、构造请求对象
from urllib.error import URLError, HTTPError
from bs4 import BeautifulSoup #网络解析工具


# ------------------------配置----------------------
# TARGET_URL = "https://news.cctv.com/china/"
# TARGET_URL = "https://news.cctv.com/roll/index.shtml"
TARGET_URL = "https://www.chinanews.com.cn/rss/scroll-news.xml"
DB_PATH = 'cctv_news.db'
TIMEOUT = 10 #如果对方服务器不响应，没有timeout的程序会一直等下去

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(message)s',
                    handlers=[logging.FileHandler('news.log',encoding='utf-8'),#写入文件
                              logging.StreamHandler(),]#写在终端
                    )
logger = logging.getLogger(__name__) #创建日志对象

# 定义一个请求函数，接受一个URL字符串
def fetch(url):
    # 构造一个请求对象
    req = Request(url,
                  headers={'User-Agent': 'Mozilla/5.0'
                           })
    try:
        # 发送请求，拿到响应对象 req上面构造的请求，10s没响应就抛异常，，用完自动关闭连接
        with urlopen(req, timeout=TIMEOUT) as response:
            # 返回字节，将字节返回字符串
            return response.read().decode('utf-8',errors='ignore')#手动解码，遇到解不了的就跳过
    except HTTPError as e:
        logger.error(f'HTTPError: {e}')
    except URLError as e:
        logger.error(f'URLError: {e}')
    return None

# 如果当前文件夹没有 news.db 文件：会自动生成 cctv_news.db 文件
def init_db():
    """建表，返回连接"""
    conn = sqlite3.connect(DB_PATH)
    # conn.execute("DROP TABLE IF EXISTS cctv_news")
    conn.execute('''
    CREATE TABLE IF NOT EXISTS cctv_news (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        news_url TEXT UNIQUE NOT NULL, 
        title TEXT,
        pub_time TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now', 'localtime')))
    ''')
    conn.commit()
    return conn

def save_news(conn,news_url,title,pub_time):
    """插入新闻，链接重复直接跳过"""
    before = conn.total_changes
    cursor = conn.execute(
        # OR IGNORE：遇到唯一约束冲突时不报错，直接跳过
        "INSERT OR IGNORE INTO cctv_news (news_url,title,pub_time) VALUES (?, ?, ?)",
        (news_url,title,pub_time)
    # 第二个参数是元组，按顺序替换 ? 防止URL自身含单引号，SQL被破坏
    )
    conn.commit()
    after = conn.total_changes
    return after - before
    # return cursor.rowcount #受影响的行数


def crawl_task():
    """爬取新闻 RSS"""
    logger.info(f"开始爬取 {TARGET_URL}")
    html = fetch(TARGET_URL)

    logger.info(f"长度: {len(html)}")
    logger.info(f"前 300 字: {html[:300]}")

    if not html:
        logger.error("页面获取失败，本次爬取结束")
        return

    soup = BeautifulSoup(html, 'xml')   # 建树，用xml解析器
    conn = init_db() #连接数据库
    add_num = 0

    news_list = soup.find_all("item")
    if not news_list:
        logger.warning("未抓取到新闻列表，结构可能变化！")
        conn.close()
        return

    for li in news_list:
        try:
            title_tag = li.find("title")
            link_tag = li.find("link")
            if not title_tag or not link_tag:
                continue

            title = title_tag.get_text(strip=True)
            news_url = link_tag.get_text(strip=True) # 提取文字

            pub_tag = li.find("pubDate") #找到发布时间
            pub_time = pub_tag.get_text(strip=True) if pub_tag else ""

            if news_url and title:
                cnt = save_news(conn, news_url, title, pub_time) #save返回受影响行数1/0
                add_num += cnt
        except Exception as e:
            logger.warning(f"单条解析失败：{e}")
            continue

    conn.close()
    logger.info(f"爬取完成！本次新增新闻 {add_num} 条")

def show_records(limit=15):
    conn = init_db()
    cursor = conn.execute("SELECT id, news_url, title,pub_time, created_at FROM cctv_news ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    print('\n已爬新闻')
    for row in cursor:
        print(f"【{row[0]}】{row[2]}") #id，标题
        print(f"    链接: {row[1]}")
        print(f"    时间: {row[3] or '未知'}")
        print(f"    爬取: {row[4]}\n")

def daemon(hour=7):
    """
    每天hour点抓一次
    判断逻辑：已过设定时间且今天还没跑过 执行
    """
    logger.info(f"定时器启动，每天{hour}点抓取，ctrl+c退出")
    last_day = None #记录今天是否跑过
    while True:
        try:
            now = datetime.now()
            if now.hour >= hour and last_day != now.date():
                logger.info(f"到达{hour}点，触发抓")
                crawl_task()
                last_day = now.date()
                logger.info(f"{last_day}已执行，等待明天{hour}点")
            time.sleep(60)
        except KeyboardInterrupt:
            logger.info("收到 Ctrl+C，退出定时器")
            break
        except Exception as e:
            logger.error(f"循环异常：{e}")
            time.sleep(60)

def main():
    parser = argparse.ArgumentParser()#创建一个对象，接受命令行传进来的参数
    parser.add_argument('opt',help="命令：crawl执行爬取；show 查看新闻；deamon 定时抓取") #位置参数
    parser.add_argument('--hour', type=int, default=7, help="daemon 模式下每天几点执行，默认 7") #可选参数
    args = parser.parse_args()
    # 基于命令词进行路由分发
    # python news.py crawl
    if args.opt == "crawl":
        crawl_task()
    # python news.py show
    elif args.opt == "show":
        show_records()
    elif args.opt == "daemon":
        daemon(hour=args.hour)
    else:
        print("参数错误，请输入crawl / show / daemon")

if __name__ == '__main__':
    main()
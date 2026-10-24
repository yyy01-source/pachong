import sys
import time
import logging
import argparse
import sqlite3
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DB_PATH = "bilibili_hot.db"
TIMEOUT = 10
API_TPL = "https://api.bilibili.com/x/web-interface/wbi/search/square"
params = {
    "limit": "10",
    "platform": "web",
    "web_location": "333.1007",
    "x-bili-locale-json": '{"c_locale":{"language":"zh","script":"Hans"},"always_translate":false}',
    "x-bili-device-req-json": '{"platform":"web","device":"pc","spmid":"333.1007","mobi_app":"web_cn"}',
    "w_rid": "0d8a42c97401b018360bf8e889e5c44f",
    "wts": "1792757925"
}
FETCH_LIMIT = 20

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(message)s',
    handlers=[
        logging.FileHandler("bilibili_hot.log", encoding="utf-8"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

HEADERS = {
    "user-agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36 SLBrowser/9.0.8.9131 SLBChan/111 SLBVPV/64-bit",
    "referer":"https://www.bilibili.com/",
    "Accept":"*/*",
    "accept-language":"zh-CN,zh;q=0.9"
}

session = requests.Session()
session.headers.update(HEADERS)

# tenacity:网络异常自动重试，指数退避，最多重试3次
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=2, min=2, max=8),
    # 指数退避等待时间。
    retry=retry_if_exception_type(requests.exceptions.RequestException),
    # 精准打击。只有当发生网络请求异常（比如超时、连接错误、DNS解析失败）时才重试
    reraise=True
)
def fetch_api(url):
    """底层网络请求函数：发请求把拿到的JSON数据交回来，如果失败抛出异常"""
    sleep_sec = round(1.0 + (time.time() % 1.5), 2)
    time.sleep(sleep_sec)
    # 动态随机休眠（1.0到2.5秒之间），利用当前时间戳取模来实现随机化，防止请求过于规律被反爬
    resp = session.get(url, params=params , timeout=TIMEOUT)
    resp.raise_for_status()
    # 主动爆雷，如果服务器返回了 404（找不到页面）或 500（服务器错误），这行代码会直接抛出异常（结束这个函数）
    # data = resp.json()
    # print(data)
    return resp.json()
    # JSON格式字符串转成Python字典并返回

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS bili_hot (
        id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
        hot_word TEXT UNIQUE NOT NULL,
        heat INTEGER,
        rank INTEGER,
        created_at TIMESTAMP NOT NULL DEFAULT (datetime('now', 'localtime'))
        )
    """)
    conn.commit()
    return conn

def save_hot(conn, hot_word, heat, rank):
    before = conn.total_changes
    conn.execute('''
        INSERT OR IGNORE INTO bili_hot
        (hot_word, heat, rank)
        VALUES (?,?,?)
    ''', (hot_word, heat, rank))
    conn.commit()
    after = conn.total_changes
    return after - before

def crawl_task():
    logger.info("开始抓取B站热搜动态接口")
    conn = init_db()
    total_add = 0
    api_url = API_TPL
    logger.info(f"请求接口{api_url}")
    try:
        json_data = fetch_api(api_url)
    except requests.exceptions.RequestException as e:
        logger.error(f"接口请求彻底失败：{e}")
        conn.close()
        return

    data = json_data.get("data",{})
    trending = data.get("trending",{})
    hot_list = trending.get("list",[])

    if not hot_list:
        logger.warning("没有拿到热搜列表，接口结构可能变更！")
        conn.close()
        return
    for idx, item in enumerate(hot_list):
        word = item.get("keyword","")
        heat_score = item.get("heat_score",0)
        rank = idx + 1
        if not word:
            continue
        cnt = save_hot(conn, word, heat_score, rank)
        total_add += cnt
        logger.debug(f"热搜：{word} 热度：{heat_score}")
    conn.close()
    logger.info(f"抓取结束！本次新增{total_add}条热搜记录")

def show_records(limit = 25):
    conn = init_db()
    rows = conn.execute('''
        SELECT rank,hot_word,heat,created_at 
        FROM bili_hot ORDER BY id DESC LIMIT ?
    ''', (limit,)).fetchall()
    conn.close()
    print(f"\n ===== 已抓取B站热搜列表 =====")
    for r in rows:
        print(f"【第{r[0]}位】{r[1]} | 热度：{r[2]}")
        print(f"    入库时间：{r[3]}\n")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("opt",help="命令：crewl执行采集；show查看数据库数据")
    args = parser.parse_args()

    if args.opt == "crawl":
        crawl_task()
    elif args.opt == "show":
        show_records()
    else:
        print(f"参数错误，只能使用 crawl / show")

if __name__ == "__main__":
    main()
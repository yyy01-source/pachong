import sys
import time
import logging
import sqlite3
import argparse

from selenium import webdriver
from selenium.webdriver.edge.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==================== 全局配置 ====================
DB_PATH = "dangdang_books.db"
LOG_PATH = "news_v3.log"
KEYWORD = "Python"

# ==================== 日志配置 ====================
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_PATH, encoding='utf-8'),
        logging.StreamHandler()
    ],
)
logger = logging.getLogger(__name__)

# ==================== 1. 启动Edge浏览器（带反爬伪装） ====================
def get_selenium_driver(headless=False): # headless=False:弹出Edge窗口，可以看到自动操作(True:后台运行不弹出窗口)
    options = Options() # optains变量用来存放所有浏览器自动参数，后面一次性传给 Edge
    if headless: # 若headless=True，开启无头模式
        options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")

    # 反爬伪装：抹掉自动化特征
    # 关闭Edge浏览器自带的 自动化测试 提示【正受到自动测试软件控制】
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    # 禁用 Edge 的自动化扩展插件（这个插件也是爬虫特征之一）
    options.add_experimental_option("useAutomationExtension", False)
    # 关闭 Blink 内核的自动化检测，让网站无法通过浏览器内核标记识别 selenium
    options.add_argument("--disable-blink-features=AutomationControlled")

    # 创建 Edge 驱动对象
    driver = webdriver.Edge(options=options)

    # 最关键的反爬一行：浏览器已经启动，页面加载前注入JS修改浏览器内置变量
    # execute_cdp_cmd:调用底层CDP协议（开发者协议），每打开一个新页面，页面加载之前，提前执行一段JS代码抹除webdriver检测
    driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {
        "source": "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    })
    return driver

# ==================== 2. 数据库操作 ====================
def init_db():
    conn=sqlite3.connect(DB_PATH)
    conn.execute("""
    CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT,
    price TEXT,
    link TEXT UNIQUE NOT NULL,
    keyword TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP)
    """)
    conn.commit()
    return conn

def save_book(conn,title,price,link,keyword):
    before = conn.total_changes
    conn.execute(
        "INSERT OR IGNORE INTO books (title, price, link, keyword) VALUES (?, ?, ?, ?)",
    (title, price, link, keyword)
    )
    conn.commit()
    return conn.total_changes - before

# ==================== 3. 核心抓取与交互逻辑 ====================
def crawl_dangdang(keyword):
    logger.info(f"开始当当网搜索任务，关键词：{keyword}")
    driver = get_selenium_driver()
    conn=init_db()
    total_add = 0

    try:
        driver.get("https://www.dangdang.com/")

        # 显式等待
        wait = WebDriverWait(driver, 10)

        logger.info("正在寻找搜索框并输入关键词...")
        search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR,"#key_S")))
        search_box.clear()
        search_box.send_keys(keyword)

        logger.info("点击搜索按钮...")
        search_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR,"#form_search_new .button")))
        driver.execute_script("arguments[0].click();", search_btn) # JS强行点击，防遮挡

        logger.info("等待商品列表加载...")
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.bigimg > li")))
        time.sleep(2)


        for i in range(2):
            print(f"正在抓取第{i+1}页")
            booklist = driver.find_elements(By.CSS_SELECTOR, ".con.shoplist li")
            logger.info(f"当前页面找到了 {len(booklist)} 本书")
            for li in booklist:
                try:
                    price = li.find_elements(By.CSS_SELECTOR, ".search_now_price")
                    if not price:
                        continue
                    price = price[0].text

                    title_else = li.find_elements(By.CSS_SELECTOR, "p.name > a")
                    if not title_else:
                        continue
                    title = title_else[0].get_attribute("title")
                    link = title_else[0].get_attribute("href")

                    if not title:
                        continue

                    # 保存到数据库
                    cnt = save_book(conn,title,price,link,keyword)
                    total_add += cnt

                    if cnt > 0:
                        logger.info(f"新增：{title} | 价格：{price}")

                except Exception as e:
                    logger.warning(f"解析单本书失败，跳过。原因: {e}")

            # 翻页操作
            try:

                # 1. 记录翻页前，当前页第一个商品的元素
                first_book = driver.find_element(By.CSS_SELECTOR, ".con.shoplist li")

                next_btn = driver.find_element(By.CSS_SELECTOR, "li.next a")  # class=next的 <li> 中的 <a>
                # next = driver.find_element(By.LINK_TEXT, "下一页")  # 也可以通过超链接的文本定位到 下一页 按钮
                driver.execute_script("arguments[0].click();", next_btn)
                # next_btn.click()

                # 等待旧的第一个商品从页面上消失！
                wait.until(EC.staleness_of(first_book))
                # 翻页后等待新一页数据加载出来
                wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "ul.bigimg > li")))

            except:
                print("已经是最后一页了")
                break
    except Exception as e:
        logger.error(f"抓取发生错误：{e}")
    finally:
        conn.close()
        driver.quit()
        logger.info(f"任务结束！本次抓取并新增了 {total_add} 本书")

# ==================== 4. 程序入口 ====================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("opt",choices=["crawl"],help="执行 crawl 启动抓取")
    args = parser.parse_args()

    if args.opt == "crawl":
        crawl_dangdang(KEYWORD)

if __name__ == "__main__":
    main()
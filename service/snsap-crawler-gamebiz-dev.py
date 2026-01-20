import json
import os
import time
import re
import requests
import translater_deepl
import boto3
import datetime
import pytz
from zoneinfo import ZoneInfo
from botocore.exceptions import NoCredentialsError, ClientError
from bs4 import BeautifulSoup
from urllib.parse import urljoin

BASE_URL = "https://gamebiz.jp"
TAG_URL = "https://gamebiz.jp/news/tag/22096"
OUTPUT_DIR = "/tmp/output/gamebiz_tag_22096"

TOKYO_TZ = pytz.timezone("Asia/Tokyo")

HEADERS = {
    "User-Agent": "Mozilla/5.0"
}

os.makedirs(OUTPUT_DIR, exist_ok=True)

def insert_article_to_dynamodb(item):
    dynamodb = boto3.resource(
        'dynamodb',
        region_name="ap-northeast-1"
    )

    table = dynamodb.Table("gamebiz_article_dev")

    try:
        table.put_item(Item=item)
        print(f"✅ Inserted article {item['article_id']}")
    except ClientError as e:
        print(f"❌ Failed to insert: {e.response['Error']['Message']}")


def get_secret():

    secret_name = "dev/x2wb"
    region_name = "ap-northeast-1"

    # Create a Secrets Manager client
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager',
        region_name=region_name
    )

    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_name
        )
    except ClientError as e:
        raise e

    secret = get_secret_value_response['SecretString']
    return json.loads(secret)


def upload_file_to_s3(file_path, object_key=None):
    """
    Uploads a file to an S3 bucket with explicit AWS credentials.
    """
    # Create the S3 client with credentials
    s3 = boto3.client(
        's3',
        region_name="ap-northeast-1"
    )

    if object_key is None:
        import os
        object_key = os.path.basename(file_path)

    try:
        s3.upload_file(file_path, "snsap-crawler-dev", object_key)
        print(f"✅ Uploaded: s3://snsap-crawler-dev/{object_key}")
    except FileNotFoundError:
        print("❌ File not found.")
    except NoCredentialsError:
        print("❌ AWS credentials are invalid or missing.")
    except ClientError as e:
        print(f"❌ Upload failed: {e}")


def is_article_href(href):
    """
    只允许 /news/ + 6位数字
    例如: /news/417205
    """
    if not href:
        return False
    return re.match(r"^/news/\d{6}$", href) is not None



# -----------------------------
# 1. 获取所有文章 URL
# -----------------------------
def get_all_article_urls(page: int):
    urls = set()

    while True:
        print(f"抓取列表页: page={page}")
        resp = requests.get(f"{TAG_URL}?page={page}", headers=HEADERS)
        if resp.status_code != 200:
            break

        soup = BeautifulSoup(resp.text, "html.parser")

        links = soup.select('a[href^="/news/"]')
        before = len(urls)

        for a in links:
            href = a.get("href")
            if is_article_href(href):
                urls.add(urljoin(BASE_URL, href))

        if len(urls) == before:
            break  # 没有新文章了

        page += 1
        time.sleep(1)
        break

    return list(urls)


def get_pubtime(soup):
    """
    获取 gamebiz 文章发布时间（兼容多种模板）
    """

    # 1️⃣ 新模板（你提供的这个）
    pub = soup.select_one("div.article__published-at")
    if pub:
        return pub.get_text(strip=True)

    # 2️⃣ 旧模板 / 其他文章
    time_tag = soup.find("time")
    if time_tag:
        return time_tag.get_text(strip=True)

    # 3️⃣ 兜底
    return ""


# -----------------------------
# 2. 抓取单篇文章
# -----------------------------
def crawl_article(url, DEEPL_API_KEY):
    print("  抓取文章:", url)
    resp = requests.get(url, headers=HEADERS)
    resp.encoding = resp.apparent_encoding

    if "中山淳雄の「推しもオタクもグローバル」" not in resp.text:
        print(f"[SKIP] 作者不匹配: {url}")
        return None

    soup = BeautifulSoup(resp.text, "html.parser")

    article_id = url.rstrip("/").split("/")[-1]
    article_dir = os.path.join(OUTPUT_DIR, article_id)
    img_dir = os.path.join(article_dir, "images")
    os.makedirs(img_dir, exist_ok=True)

    title = soup.select_one("h1").get_text(strip=True)
    title_zh = translater_deepl.translate_japanese_to_chinese(title, DEEPL_API_KEY)
    pubtime = get_pubtime(soup)

    content = soup.select_one('.article__body-text[data-content="blogparts"]')

    if content:
        text = content.get_text(separator='\n', strip=True)
        # print(text)
    else:
        print('没有找到正文')
        return

    lines = [
        f"# {title}",
        f"*公開日時*: {pubtime}",
        ""
    ]

    lines_zh = [
        f"# {title_zh}",
        f"*发布时间*: {pubtime}",
        ""
    ]

    img_index = 1

    for elem in content.find_all(["p"], recursive=False):

        # 1️⃣ 找 p 里的所有 img（可能 1 张，也可能多张）
        imgs = elem.find_all("img")
        if imgs:
            for img in imgs:
                src = (
                        img.get("data-src")
                        or img.get("data-original")
                        or img.get("src")
                )
                if not src:
                    continue

                img_url = urljoin(url, src)
                ext = os.path.splitext(img_url)[1].split("?")[0] or ".jpg"
                img_name = f"{article_id}_img_{img_index}{ext}"
                img_path = os.path.join(img_dir, img_name)

                try:
                    with open(img_path, "wb") as f:
                        f.write(requests.get(img_url, headers=HEADERS).content)

                    upload_file_to_s3(img_path, f"gamebiz/gamebiz_tag_22096/{article_id}/images/{img_name}")
                    lines.append(f"![](images/{img_name})")
                    lines.append("")
                    lines_zh.append(f"![](images/{img_name})")
                    lines_zh.append("")
                    img_index += 1
                except Exception as e:
                    print("图片下载失败:", img_url, e)

            continue  # ⚠️ 这个 p 已经作为“图片段落”处理完了

        # 2️⃣ 普通文字段落
        text = elem.get_text(strip=True)
        if text:
            lines.append(text)
            lines.append("")
            text_zh = translater_deepl.translate_japanese_to_chinese(text, DEEPL_API_KEY)
            lines_zh.append(text_zh)
            lines_zh.append("")

    articel_file_name_ja = os.path.join(article_dir, f"article_{article_id}_ja.md")
    with open(articel_file_name_ja, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    upload_file_to_s3(articel_file_name_ja, f"gamebiz/gamebiz_tag_22096/{article_id}/article_{article_id}_ja.md")

    articel_file_name_zh = os.path.join(article_dir, f"article_{article_id}_zh.md")
    with open(articel_file_name_zh, "w", encoding="utf-8") as f:
        f.write("\n".join(lines_zh))

    upload_file_to_s3(articel_file_name_zh, f"gamebiz/gamebiz_tag_22096/{article_id}/article_{article_id}_zh.md")
    now_time = datetime.datetime.now(TOKYO_TZ).isoformat(timespec="seconds")
    article_item = {
        "article_id": article_id,
        "publish_time": pubtime,
        "created_at": now_time
    }
    insert_article_to_dynamodb(article_item)


def lambda_handler(event, context):
    secret = get_secret()
    DEEPL_API_KEY = secret['DEEPL_API_KEY_1']

    page = int(event.get("page", 1))  # 默认 page=1
    urls = get_all_article_urls(page)
    print(f"共发现文章 {len(urls)} 篇")

    for i, url in enumerate(sorted(urls), 1):
        print(f"[{i}/{len(urls)}]")
        crawl_article(url, DEEPL_API_KEY)
        time.sleep(1.5)  # 非常重要

    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }

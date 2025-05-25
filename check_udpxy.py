import requests
import socket
import time
from datetime import datetime, timezone, timedelta
import json
from concurrent.futures import ThreadPoolExecutor, as_completed

# 测试单个 UDPXY 地址
def test_udpxy_stream(url: str, test_duration: int = 10, chunk_size: int = 1024, idle_threshold: float = 3.0) -> dict:
    print(f"Testing {url}")
    try:
        response = requests.get(url, stream=True, timeout=(3, 1))
        response.raise_for_status()
    except requests.RequestException as e:
        return result_dict(url, "Connection Error Invalid Address", 0.0)

    response.raw.decode_content = False
    start_time = time.time()
    last_data_time = start_time

    while time.time() - start_time < test_duration:
        try:
            chunk = response.raw.read(chunk_size)
            if chunk:
                last_data_time = time.time()
            else:
                return result_dict(url, "Connection Blocked", last_data_time - start_time)
        except (socket.timeout, requests.exceptions.ReadTimeout):
            pass
        except Exception as e:
            return result_dict(url, "Connection Error Stream Service Stop", last_data_time - start_time)

        if time.time() - last_data_time > idle_threshold:
            return result_dict(url, "Connection Blocked", last_data_time - start_time)

    return result_dict(url, "Connection OK", last_data_time - start_time)

# 格式化结果字典（含北京时间）
def result_dict(url, result, last_data_elapsed):
    beijing_time = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
    now_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")
    return {
        "URL": url,
        "Result": result,
        "LastDataTimeSeconds": round(last_data_elapsed, 1),
        "TestTime": now_str
    }

# 获取 IPTV 地址列表
def fetch_urls_from_github(raw_url):
    try:
        response = requests.get(raw_url)
        response.raise_for_status()
        lines = response.text.strip().splitlines()
        return [line.strip() for line in lines if line.startswith("http")]
    except Exception as e:
        print(f"Error fetching IPTV list: {e}")
        return []

if __name__ == "__main__":
    github_raw_url = "https://raw.githubusercontent.com/tangdeyi11/udpxy-text/main/iptv.txt"
    urls = fetch_urls_from_github(github_raw_url)

    results = []

    max_workers = min(20, len(urls))  # 设置最大线程数

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(test_udpxy_stream, url): url for url in urls}

        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"{url} generated an exception: {exc}")
                results.append(result_dict(url, "Exception Occurred", 0.0))

    # 保存所有测试结果到 JSON 文件
    with open("iptv-test.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\nAll results written to iptv-test.json")

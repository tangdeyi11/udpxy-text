import requests
import socket
import time
from datetime import datetime, timezone, timedelta
import json

# 测试单个 UDPXY 地址
def test_udpxy_stream(url: str, test_duration: int = 10, chunk_size: int = 1024, idle_threshold: float = 3.0) -> (str, float):
    print(f"\nConnecting to {url}")
    try:
        response = requests.get(url, stream=True, timeout=(3, 1))
        response.raise_for_status()
    except requests.RequestException as e:
        print(f"Failed to connect or get stream: {e}")
        return "Connection Error Invalid Address", 0.0

    response.raw.decode_content = False
    start_time = time.time()
    last_data_time = start_time

    while time.time() - start_time < test_duration:
        try:
            chunk = response.raw.read(chunk_size)
            if chunk:
                elapsed = time.time() - start_time
                print(f"[{elapsed:.1f}s] Received {len(chunk)} bytes")
                last_data_time = time.time()
            else:
                print("Stream closed by server (TCP FIN received)")
                return "Connection Blocked", last_data_time - start_time
        except (socket.timeout, requests.exceptions.ReadTimeout):
            print(f"[{time.time() - start_time:.1f}s] Read timeout, no data")
        except Exception as e:
            print(f"Unexpected error: {e}")
            return "Connection Error Stream Service Stop", last_data_time - start_time

        if time.time() - last_data_time > idle_threshold:
            print(f"No data for more than {idle_threshold} seconds — considering blocked.")
            return "Connection Blocked", last_data_time - start_time

    print("Stream data continued successfully.")
    return "Connection OK", last_data_time - start_time

# 从 GitHub 获取 IPTV 地址列表
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
    # GitHub 原始地址（需使用 raw 格式）
    github_raw_url = "https://raw.githubusercontent.com/tangdeyi11/udpxy-text/main/iptv.txt"
    urls = fetch_urls_from_github(github_raw_url)

    results = []

    for url in urls:
        result, last_data_elapsed = test_udpxy_stream(url, test_duration=10, idle_threshold=3.0)

        # 获取北京时间
        utc_now = datetime.utcnow().replace(tzinfo=timezone.utc)
        beijing_time = utc_now.astimezone(timezone(timedelta(hours=8)))
        now_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")

        results.append({
            "URL": url,
            "Result": result,
            "LastDataTimeSeconds": round(last_data_elapsed, 1),
            "TestTime": now_str
        })

    # 写入 JSON 文件
    with open("iptv-test.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print("\nAll results written to iptv-test.json")


import requests                 # 用于发送 HTTP 请求
import socket                   # 用于处理底层网络超时
import time                     # 处理时间相关操作
from datetime import datetime, timezone, timedelta  # 获取和转换当前时间
import json                     # 处理 JSON 数据
from concurrent.futures import ThreadPoolExecutor, as_completed  # 并发执行任务

# -----------------------------
# 函数：测试一个 UDPXY 流地址
# -----------------------------
def test_udpxy_stream(url: str, test_duration: int = 10, chunk_size: int = 1024, idle_threshold: float = 3.0) -> dict:
    print(f"Testing {url}")

    try:
        # 发起 HTTP 流请求，设置连接超时为3秒，读取超时为1秒
        response = requests.get(url, stream=True, timeout=(3, 1))
        response.raise_for_status()
    except requests.RequestException:
        # 连接失败或响应无效
        return result_dict(url, "Connection Error Invalid Address", 0.0)

    response.raw.decode_content = False  # 不自动解码内容
    start_time = time.time()             # 测试开始时间
    last_data_time = start_time          # 上次接收到数据的时间

    # 在设定的测试时间内循环读取数据块
    while time.time() - start_time < test_duration:
        try:
            chunk = response.raw.read(chunk_size)
            if chunk:
                last_data_time = time.time()  # 记录接收到数据的时间
            else:
                # 如果服务器主动关闭连接
                return result_dict(url, "Connection Blocked", last_data_time - start_time)
        except (socket.timeout, requests.exceptions.ReadTimeout):
            # 如果发生读取超时，忽略继续尝试
            pass
        except Exception:
            # 其它错误，视为服务停止
            return result_dict(url, "Connection Error Stream Service Stop", last_data_time - start_time)

        # 如果在设定的时间内未收到任何数据，判断为阻断
        if time.time() - last_data_time > idle_threshold:
            return result_dict(url, "Connection Blocked", last_data_time - start_time)

    # 流持续正常传输，视为成功
    return result_dict(url, "Connection OK", last_data_time - start_time)

# --------------------------------
# 函数：生成格式化的结果字典（含北京时间）
# --------------------------------
def result_dict(url, result, last_data_elapsed):
    beijing_time = datetime.utcnow().replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=8)))
    now_str = beijing_time.strftime("%Y-%m-%d %H:%M:%S %Z%z")  # 转为北京时间字符串

    return {
        "URL": url,
        "Result": result,
        "LastDataTimeSeconds": round(last_data_elapsed, 1),
        "TestTime": now_str
    }

# ----------------------------------------
# 函数：从 GitHub 原始地址中读取 IPTV 列表
# ----------------------------------------
def fetch_urls_from_github(raw_url):
    try:
        response = requests.get(raw_url)
        response.raise_for_status()  # 抛出非 200 错误
        lines = response.text.strip().splitlines()  # 分割为多行
        return [line.strip() for line in lines if line.startswith("http")]  # 过滤出 http 开头的地址
    except Exception as e:
        print(f"Error fetching IPTV list from {raw_url}: {e}")
        return []

# ----------------------------------------
# 函数：对地址列表进行并发测试并保存结果
# ----------------------------------------
def test_and_save(url_list, output_filename):
    results = []  # 存储所有测试结果
    max_workers = min(20, len(url_list))  # 设置最大并发线程数为 20 或列表长度

    # 使用线程池进行并发测试
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有测试任务
        future_to_url = {executor.submit(test_udpxy_stream, url): url for url in url_list}

        # 按完成顺序处理结果
        for future in as_completed(future_to_url):
            url = future_to_url[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f"{url} generated an exception: {exc}")
                results.append(result_dict(url, "Exception Occurred", 0.0))

    # 将所有结果写入 JSON 文件
    with open(output_filename, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=4)

    print(f"\nResults written to {output_filename}")

# ----------------------------
# 主程序入口
# ----------------------------
if __name__ == "__main__":
    # 定义两个 IPTV 列表源及对应输出文件
    source_map = {
        "https://iptv.dtcs520.com/iptvlist": "iptv-test.json",
        "https://iptv.dtcs520.com/iptvdllist": "iptvdl-test.json"
    }

    # 遍历每个源，进行测试并保存对应结果
    for source_url, output_file in source_map.items():
        print(f"\n--- Fetching and testing from: {source_url} ---")
        urls = fetch_urls_from_github(source_url)
        if urls:
            test_and_save(list(set(urls)), output_file)  # 去重后测试
        else:
            print(f"⚠️ No valid URLs found in {source_url}")

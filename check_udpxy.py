import requests
import socket
import time
from datetime import datetime

def test_udpxy_stream(url: str, test_duration: int = 10, chunk_size: int = 1024, idle_threshold: float = 3.0) -> (str, float):
    print(f"Connecting to {url}")
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

if __name__ == "__main__":
    url = "http://123.115.118.228:9000/udp/239.3.1.129:8008"  # 可替换
    result, last_data_elapsed = test_udpxy_stream(url, test_duration=60, idle_threshold=3.0)
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # 写入文件
    with open("iptv-test.txt", "w", encoding="utf-8") as f:
        f.write(f"URL: {url}\n")
        f.write(f"Result: {result}\n")
        f.write(f"Last Data Time: {last_data_elapsed:.1f} seconds\n")
        f.write(f"Test Time: {now_str}\n")

    print("Result written to iptv-test.txt")

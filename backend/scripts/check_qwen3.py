#!/usr/bin/env python3
import os
import json
import time
import argparse
import sys
import requests


def main():
    parser = argparse.ArgumentParser(description="Check Qwen3 API connectivity and model validity")
    parser.add_argument("--api-key", dest="api_key", default=None, help="Qwen3 API key (overrides env)")
    parser.add_argument("--api-url", dest="api_url", default=None, help="Qwen3 API URL (overrides env)")
    parser.add_argument("--model", dest="model", default=None, help="Qwen3 model, e.g., qwen-mt-turbo or qwen-mt-plus")
    parser.add_argument("--timeout", dest="timeout", type=int, default=30, help="HTTP timeout seconds")
    args = parser.parse_args()

    api_key = (args.api_key or os.getenv("QWEN3_API_KEY", "")).strip()
    api_url = (args.api_url or os.getenv("QWEN3_API_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions")).strip()
    model = (args.model or os.getenv("QWEN3_MODEL", "qwen-mt-turbo")).strip()

    print("[Qwen3 Connectivity Check]")
    print(f"- API URL: {api_url}")
    print(f"- Model  : {model}")
    print(f"- API Key present: {bool(api_key)}")
    if api_key:
        print(f"- API Key preview: {api_key[:6]}...{api_key[-4:]} (masked)")
    else:
        print("ERROR: QWEN3_API_KEY is empty. Provide --api-key or set env.")
        sys.exit(2)

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": "看完这个视频我没有笑",
            }
        ],
        "translation_options": {
            "source_lang": "auto",
            "target_lang": "English"
        }
    }

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }

    try:
        t0 = time.time()
        resp = requests.post(api_url, headers=headers, json=payload, timeout=args.timeout)
        dt = time.time() - t0
        print(f"HTTP {resp.status_code} in {dt:.2f}s")
        head = resp.text[:300].replace("\n", " ")
        print("Response head:", head)
        resp.raise_for_status()

        data = resp.json()
        content = (
            data.get("choices", [{}])[0]
            .get("message", {})
            .get("content", "")
            .strip()
        )
        print("Content head:", content[:200])

        parsed_ok = False
        try:
            arr = json.loads(content)
            if isinstance(arr, list) and len(arr) >= 1:
                parsed_ok = True
                print("Parsed JSON array OK. Sample:", arr[:1])
        except Exception:
            pass

        if not parsed_ok:
            print("Note: Could not parse JSON array directly from content (provider may return plain text).")

        print("Qwen3 connectivity check: SUCCESS")
    except Exception as e:
        print("Qwen3 connectivity check: FAILED")
        print("Error:", repr(e))
        sys.exit(1)


if __name__ == "__main__":
    main()



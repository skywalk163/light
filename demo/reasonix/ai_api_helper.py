"""
Reasonix AI API 辅助模块

封装 OpenAI 兼容接口的 HTTP 调用，供 Duan 代码通过 `导入 Python:` 调用。
"""

import os
import json
import requests


def _load_env():
    """手动加载 .env 文件到环境变量（不依赖 python-dotenv）"""
    env_path = os.path.join(os.path.dirname(__file__), '.env')
    if os.path.exists(env_path):
        with open(env_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, _, value = line.partition('=')
                key = key.strip()
                value = value.strip().strip('"').strip("'")
                if key and key not in os.environ:
                    os.environ[key] = value


def load_config():
    """加载 AI API 配置"""
    _load_env()
    return {
        'api_key': os.environ.get('REASONIX_API_KEY', ''),
        'api_base_url': os.environ.get('REASONIX_API_BASE_URL', 'https://api.openai.com/v1'),
        'model': os.environ.get('REASONIX_MODEL', 'gpt-4o-mini'),
        'max_tokens': int(os.environ.get('REASONIX_MAX_TOKENS', '2000')),
        'temperature': float(os.environ.get('REASONIX_TEMPERATURE', '0.7')),
    }


def check_api_key():
    """检查是否配置了 API 密钥"""
    config = load_config()
    return bool(config['api_key'])


def call_ai(system_prompt, user_prompt, config=None):
    """调用 AI API，返回响应文本。失败时返回 None"""
    if config is None:
        config = load_config()

    if not config['api_key']:
        return None

    headers = {
        'Authorization': f"Bearer {config['api_key']}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': config['model'],
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt},
        ],
        'temperature': config['temperature'],
        'max_tokens': config['max_tokens'],
    }

    try:
        url = config['api_base_url'].rstrip('/') + '/chat/completions'
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        result = response.json()
        content = result['choices'][0]['message']['content']
        # 空内容视为失败，返回 None，便于上层回退到模拟内容
        if not content or not content.strip():
            return None
        return content
    except requests.exceptions.Timeout:
        print("  [AI API 超时: 请求超过 60 秒]")
        return None
    except requests.exceptions.ConnectionError as e:
        print(f"  [AI API 连接失败: {e}]")
        return None
    except requests.exceptions.HTTPError as e:
        status = e.response.status_code if hasattr(e, 'response') and e.response else '?'
        print(f"  [AI API HTTP {status}: {e}]")
        return None
    except Exception as e:
        print(f"  [AI API 调用失败: {e}]")
        return None
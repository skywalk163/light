# -*- coding: utf-8 -*-
"""
调试适配器配置文件

提供 launch.json 和 attach.json 配置示例。
"""

import os
import json

LAUNCH_TEMPLATE = {
    "version": "0.2.0",
    "configurations": [
        {
            "name": "光明: 调试当前文件",
            "type": "light",
            "request": "launch",
            "program": "${file}",
            "stopOnEntry": True,
            "console": "integratedTerminal"
        },
        {
            "name": "光明: 调试程序",
            "type": "light",
            "request": "launch",
            "program": "${workspaceFolder}/${input:programName}",
            "stopOnEntry": True,
            "console": "integratedTerminal",
            "args": []
        },
        {
            "name": "光明: 附加到调试器",
            "type": "light",
            "request": "attach",
            "port": 8765,
            "host": "localhost"
        }
    ],
    "inputs": [
        {
            "id": "programName",
            "type": "promptString",
            "description": "输入要调试的程序名称",
            "default": "main.light"
        }
    ]
}

ATTACH_TEMPLATE = {
    "version": "0.2.0",
    "configurations": [
        {
            "name": "光明: 附加",
            "type": "light",
            "request": "attach",
            "port": 8765,
            "host": "localhost",
            "timeout": 10000
        }
    ]
}


def generate_launch_json(output_path: str = '.vscode/launch.json'):
    """生成 launch.json 配置"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(LAUNCH_TEMPLATE, f, indent=2, ensure_ascii=False)
    print(f'已生成: {output_path}')


def generate_attach_json(output_path: str = '.vscode/attach.json'):
    """生成 attach.json 配置"""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(ATTACH_TEMPLATE, f, indent=2, ensure_ascii=False)
    print(f'已生成: {output_path}')


if __name__ == '__main__':
    generate_launch_json()
    generate_attach_json()

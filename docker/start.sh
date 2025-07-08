#!/bin/bash

echo "📦 开始构建并启动 RSI+EMA+MACD 监控容器..."

# 进入当前脚本所在目录
# shellcheck disable=SC2164
cd "$(dirname "$0")"

# 构建并后台启动
docker-compose up --build -d

# 打印容器状态
docker ps | grep rsi_monitor

echo "✅ 启动完成，使用 'docker logs -f rsi_monitor' 查看日志"




FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 拷贝文件
COPY . .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt

# 设置容器启动命令
CMD ["python", "rsi_alert.py"]

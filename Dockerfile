FROM python:3.11-slim

WORKDIR /app

# 安装系统依赖（WeasyPrint 需要）
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libharfbuzz0b \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 安装 Python 依赖
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建数据目录
RUN mkdir -p data reports

# 暴露端口
EXPOSE 5000

# 启动命令
CMD ["python", "app/main.py"]

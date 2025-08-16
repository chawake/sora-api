FROM python:3.10-slim

WORKDIR /app

# 设置Python环境
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONIOENCODING=utf-8

# Instalar curl para el healthcheck
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p /app/src/static/images && \
    chmod -R 777 /app/src/static

# 暴露端口
EXPOSE 8890


# 启动应用
CMD ["python", "run.py"] 

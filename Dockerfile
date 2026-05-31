# 使用官方 Python 3.12 精简镜像作为基础
FROM python:3.12-slim

# 设置工作目录
WORKDIR /app

# 先复制依赖文件，利用 Docker 缓存层加速后续构建
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# 复制应用代码
COPY . .

# 暴露端口
EXPOSE 5000

# 使用 Gunicorn 作为生产级 WSGI 服务器启动
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "app:app"]

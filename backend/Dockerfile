
FROM python:3.10-slim

WORKDIR /app

# 设置时区为北京时间
ENV TZ=Asia/Shanghai
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

# 安装系统依赖和编译工具
RUN apt-get update && apt-get install -y \
    pandoc \
    gcc \
    g++ \
    tzdata \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./

# 安装Python依赖
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# 添加启动命令
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]

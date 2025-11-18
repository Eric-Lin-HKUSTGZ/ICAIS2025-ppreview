# 使用Python 3.12
FROM python:3.12-slim-bookworm

WORKDIR /app

ENV PYTHONUNBUFFERED=1

# 复制依赖文件
COPY requirements.txt .

# 使用清华镜像源安装依赖
RUN pip install --no-cache-dir -i https://pypi.tuna.tsinghua.edu.cn/simple -r requirements.txt

# 复制V2方案所需的Python模块文件
COPY api_service_v2.py .
COPY config.py .
COPY llm_client.py .
COPY pdf_parser.py .
COPY reviewer_v2.py .
COPY prompt_template_v2.py .

# 暴露端口
EXPOSE 3000

# 运行API服务
CMD ["uvicorn", "api_service_v2:app", "--host", "0.0.0.0", "--port", "3000", "--log-level", "info", "--access-log"]


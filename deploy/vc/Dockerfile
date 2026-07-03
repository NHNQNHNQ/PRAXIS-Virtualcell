# PRAXIS-VirtualCell 离线发行镜像(本地网页 + CLI,offline 确定性,无需 API key/DB)。
# 真机构建:docker build -f deploy/vc/Dockerfile -t praxis-virtualcell .
# 跑:docker run -p 8000:8000 praxis-virtualcell  → 浏览器开 http://127.0.0.1:8000
FROM python:3.13-slim
WORKDIR /app

# 拷打包所需(pyproject/MANIFEST 决定 package-data)+ 源码 + demo 输入
COPY pyproject.toml MANIFEST.in ./
COPY praxis_virtualcell ./praxis_virtualcell
COPY praxis_vc_api ./praxis_vc_api
COPY examples ./examples
RUN pip install --no-cache-dir ".[api]" && rm -rf /root/.cache

# 可选:若已构建 React dist,拷入让 serve 同源托管(dist 不在 git,构建时 npm run build 后再 build 镜像)
# COPY praxis_vc_react/dist ./praxis_vc_react/dist

# non-root(容器逃逸防御)
RUN useradd -r -u 1000 -m -s /sbin/nologin praxisvc && chown -R praxisvc /app
USER praxisvc

ENV PRAXIS_VIRTUALCELL_MODE=offline
EXPOSE 8000
CMD ["praxis-vc", "serve", "--host", "0.0.0.0", "--port", "8000"]

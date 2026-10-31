# Optional host-neutral container. Not deployed or container-tested in this task.
FROM python:3.13-slim AS build
WORKDIR /app
COPY content ./content
COPY public ./public
COPY tools ./tools
COPY docs ./docs
RUN python tools/build.py && python tools/check.py

FROM python:3.13-slim
WORKDIR /app
COPY --from=build /app/dist ./dist
COPY --from=build /app/tools/serve.py ./tools/serve.py
ENV PORT=8080
EXPOSE 8080
USER 65532:65532
CMD ["python", "tools/serve.py", "--host", "0.0.0.0"]

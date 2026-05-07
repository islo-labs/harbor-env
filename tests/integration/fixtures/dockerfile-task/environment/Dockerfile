# debian-slim because IsloEnvironment.exec() runs commands as `bash -lc <cmd>`
# inside the built container, and the chosen base must ship bash. alpine doesn't.
FROM debian:12-slim
WORKDIR /app

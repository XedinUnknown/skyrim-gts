FROM python:3.12-alpine

RUN apk add --no-cache git

COPY gateway.py /gateway.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

EXPOSE 8765

ENTRYPOINT ["/entrypoint.sh"]

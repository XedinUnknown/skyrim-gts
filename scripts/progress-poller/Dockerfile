FROM python:3.12-alpine

RUN apk add --no-cache git

COPY poller.py /poller.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]

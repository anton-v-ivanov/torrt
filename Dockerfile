FROM python:3-alpine

RUN apk add bash
RUN apk add g++ gcc libxslt-dev libffi-dev openssl-dev

COPY ./config.json /root/_torrt/config.json
COPY . /app
RUN chmod +x /app/torrt/main.py
WORKDIR /app

RUN pip3 install python-telegram-bot
RUN python setup.py install

ENTRYPOINT [ "torrt", "run_bots" ]
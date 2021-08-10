FROM python:3.9-buster


WORKDIR /controller

COPY app.py app.py
COPY requirements.txt requirements.txt
COPY docker-entrypoint.sh docker-entrypoint.sh

RUN pip install -r requirements.txt

ENTRYPOINT ["./docker-entrypoint.sh"]

CMD ["--host", "0.0.0.0", "--port", "5000", "--debug", "True"]

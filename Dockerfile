FROM python:3.10-slim

WORKDIR /discord-esbot

COPY . /discord-esbot

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 2356

CMD ["python", "main.py"]

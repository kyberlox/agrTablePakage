FROM python:3.13-bookworm

WORKDIR /data/app
COPY ./requirements.txt /data/app/requirements.txt

RUN pip install --upgrade pip

RUN pip install --no-cache-dir --upgrade -r requirements.txt

CMD ["fastapi", "run", "main.py", "--port", "8000"]
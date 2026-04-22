FROM python:3.10

WORKDIR /code

COPY . /code

RUN pip install --no-cache-dir -r requirements.txt

CMD ["gunicorn", "-b", "0.0.0.0:7860", "app:app"]
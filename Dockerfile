FROM python:3.7-alpine
COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

COPY . /app
ENV FLASK_APP=app.py FLASK_ENV=development
CMD flask run -h 0.0.0.0
EXPOSE 5000

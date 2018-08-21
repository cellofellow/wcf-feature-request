FROM node AS js
RUN npm install knockout
RUN curl -L https://github.com/swagger-api/swagger-js/archive/v3.8.13.tar.gz | tar xvz
RUN cd swagger-js-3.8.13 && \
    npm install && \
    npm run build-bundle

FROM python:3.7-alpine
COPY requirements.txt /app/
WORKDIR /app
RUN pip install -r requirements.txt

COPY --from=js /node_modules/knockout/build/output/knockout-latest.js /app/static/js/knockout.js
COPY --from=js /swagger-js-3.8.13/browser/* /app/static/js/
COPY . /app
VOLUME /app/static/js
ENV FLASK_APP=app.py FLASK_ENV=development
CMD flask run -h 0.0.0.0
EXPOSE 5000

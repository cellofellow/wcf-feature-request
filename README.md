# WCF FeatureRequests

FeatureRequests allows users to record any features they request to add to THE
PROJECT. It is implemented in Python 3.7 with Flask and SQLAlchemy on SQLite,
with KnockoutJS in the frontend.

## Running

Docker Compose is used to produce a running copy. Steps are simple:

```shell
Bring up the Server
$ docker-compose up -d
Create the Database
$ docker-compose exec web flask create-all
$ docker-compose exec web flask default-data
```

You can now access the app at http://localhost:5000/


## Technical Documentation

This is a very basic Flask app and has little in the way of separation into
modules as that is something of a mystery to the author in Flask. (Circular
dependencies kept being a problem).

Flask provides the basic web server framework. The root `/` route serves a
static HTML file with JavaScript and CSS inline. Additional third-party
dependencies are placed in `static/js/` by the Docker Build process by way of a
staged build, using a NodeJS image to fetch and compile dependencies.

The Python library Marshmallow is used for serializing/deserializing objects
to/from the API. Flask-RESTFUL is used to provide API resources to the Flask
router. APISpec produces Swagger (OpenAPI 2.0) data that is consumed by the API
client in the JavaScript app. (This was fun to learn.)

The frontend webpage is as simple as possible. Pretty layouts and animations are
for real projects with a team of designers.

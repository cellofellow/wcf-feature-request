import typing as t

from flask import Flask, request, jsonify
from sqlalchemy.exc import IntegrityError
from sqlalchemy.engine import Engine
from sqlalchemy import event

app = Flask(__name__)
app.config.from_object('default_settings')


@event.listens_for(Engine, 'connect')
def set_sqlite_pragma(conn, record):
    cursor = conn.cursor()
    cursor.execute('PRAGMA foreign_keys=ON')
    cursor.close()


@app.route('/')
def index():
    return app.send_static_file('index.html')



# SQLAlchemy Models
from flask_sqlalchemy import SQLAlchemy
db = SQLAlchemy(app)

class Client(db.Model):
    __tablename__ = 'client'
    client_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    featurerequests = db.relationship('FeatureRequest',
                                      back_populates='client', lazy='dynamic')

    def __repr__(self) -> str:
        return f'<User {self.name}>'

    @property
    def id(self) -> int:
        return self.client_id


class ProductArea(db.Model):
    __tablename__ = 'productarea'
    productarea_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String, unique=True, nullable=False)

    # Relationships
    featurerequests = db.relationship('FeatureRequest',
                                      back_populates='productarea',
                                      lazy='dynamic')

    def __repr__(self) -> str:
        return f'<ProductArea {self.name}>'

    @property
    def id(self) -> int:
        return self.productarea_id


class FeatureRequest(db.Model):
    __tablename__ = 'featurerequest'
    featurerequest_id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, unique=True, nullable=False)
    description = db.Column(db.String, nullable=False)
    priority = db.Column(db.Integer, nullable=False)
    target_date = db.Column(db.Date)

    # References
    client_id = db.Column(db.Integer, db.ForeignKey('client.client_id'),
                          nullable=False)
    productarea_id = db.Column(db.Integer,
                               db.ForeignKey('productarea.productarea_id'),
                               nullable=False)

    # Relationships
    client = db.relationship('Client', back_populates='featurerequests',
                             lazy='joined')
    productarea = db.relationship('ProductArea',
                                  back_populates='featurerequests',
                                  lazy='joined')

    # Constraints
    __table_args__ = (
        db.UniqueConstraint('client_id', 'priority'),
    )

    @property
    def id(self) -> int:
        return self.featurerequest_id

    def handle_unique_constraints(self) -> t.Optional[str]:
        '''
        Each FeatureRequest must have a unique priority number for each client.
        When creating or updating a request, use this method to manage the
        conflict when a request with an existing priority is created. This
        increments the priority of all other request for that client equal to
        or above the new request's priority.

        Just return an error if any other unique constraints (title) are
        violated.
        '''
        cls = type(self)
        db.session.add(self)
        try:
            db.session.flush()
        except IntegrityError as err:
            reason = err.args[0]
            is_uniq = 'UNIQUE constraint failed: ' in reason
            if not is_uniq:
                raise
            is_priority_client = (
                '.client_id' in reason
                and '.priority' in reason
            )
            if is_priority_client:
                db.session.rollback()
                # Two-step priority shift. Can't defer unique constraints in
                # SQLite otherwise it could be 1-step.
                (db.session.query(cls)
                 .filter(cls.client_id == self.client_id)
                 .filter(cls.priority >= self.priority)
                 .update({cls.priority: (cls.priority + 1) * -1}))
                (db.session.query(cls)
                 .filter(cls.priority < 0)
                 .update({cls.priority: cls.priority * -1}))
                db.session.add(self)
            if '.title' in reason:
                return 'Unique title required'

    def save(self) -> t.Tuple[dict, int]:
        err = self.handle_unique_constraints()
        if err is not None:
            db.session.rollback()
            return {'errors': [err]}, 409

        db.session.commit()
        self = self.query.get(self.id)
        result = FeatureRequestSchema().dump(self)
        return {'featurerequest': result}, 200


# SQLAlchemy Commands
@app.cli.command('create-all')
def create_all():
    db.create_all()


@app.cli.command('default-data')
def default_data():
    session = db.session
    for c in 'ABC':
        session.add(Client(name=f'Client {c}'))
    for area in ['Policies', 'Billing', 'Claims', 'Reports']:
        session.add(ProductArea(name=area))
    session.commit()


__all__ = ['Client', 'ProductArea', 'FeatureRequest']

@app.cli.command('drop-all')
def drop_all():
    db.drop_all()



# Define Flask-Restful Resources
# These use the Marshmallow schemas

from marshmallow import ValidationError
from schema import FeatureRequestSchema, ProductAreaSchema, ClientSchema
from flask_restful import Api, Resource


api = Api(app)

class FeatureRequestListResource(Resource):
    '''
    API resource create and list FeatureRequests
    '''
    schema = FeatureRequestSchema

    def get(self):
        '''List all FeatureRequests
            ---
            tags: [featureRequest]
            operationId: listFeatureRequests
            description: list all feature requests
            responses:
              200:
                description: list all feature requests
                schema:
                  featurerequests:
                    type: array
                    items:
                      $ref: '#/definitions/FeatureRequest'
        '''
        reqs = self.schema(many=True).dump(FeatureRequest.query.all())
        return {'featurerequests': reqs}

    def post(self):
        '''Create new FeatureRequest
            ---
            tags: [featureRequest]
            operationId: createFeatureRequest
            description: create new feature request
            consumes:
            - application/json
            parameters:
            - in: body
              name: body
              description: FeatureRequest object to add
              required: true
              schema: {$ref: '#/definitions/FeatureRequest'}
            responses:
              200:
                description: successfully created featurerequest
                schema:
                  featurerequest:
                    type: array
                    items:
                      $ref: '#/definitions/FeatureRequest'
                  message:
                    type: string
              400:
                description: unreadable input
                schema:
                  message:
                     type: string
              422:
                description: invalid input
                schema:
                  errors:
                    type: array
                    items: string
        '''
        json_data = request.get_json()
        if not json_data:
            return {'message': 'Empty input received'}, 400
        json_data.pop('id', None)
        try:
            req = self.schema().load(json_data)
        except ValidationError as err:
            return {'errors': err.messages}, 422
        response, status = req.save()
        if status != 200:
            return response, status
        response['message'] = 'Created a new FeatureRequest'
        return response, 201
api.add_resource(FeatureRequestListResource,
                 '/v1/featurerequest')


class ProductAreaResource(Resource):
    schema = ProductAreaSchema

    def get(self):
        '''List all ProductAreas
            ---
            tags: [productArea]
            operationId: listProductAreas
            description: list all product areas
            responses:
              200:
                description: list all product areas
                schema:
                  productareas:
                    type: array
                    items:
                      $ref: '#/definitions/ProductArea'
        '''
        areas = ProductArea.query.all()
        return {'productareas': [{'id': a.id, 'name': a.name} for a in areas]}
api.add_resource(ProductAreaResource,
                 '/v1/productarea')


class ClientResource(Resource):
    schema = ClientSchema

    def get(self):
        '''List all Clients
            ---
            tags: [client]
            operationId: listClients
            description: list all clients
            responses:
              200:
                description: list all clients
                schema:
                  clients:
                    type: array
                    items:
                      $ref: '#/definitions/Client'
        '''
        clients = Client.query.all()
        return {'clients': [{'id': c.id, 'name': c.name} for c in clients]}
api.add_resource(ClientResource,
                 '/v1/client')



# Swagger API
from apispec import APISpec
from apispec.ext.marshmallow import MarshmallowPlugin

# Create an APISpec
spec = APISpec(
    title='Feature Requests',
    version='0.1.0b1',
    openapi_version='2.0',
    plugins=[
        MarshmallowPlugin(),
        'apispec_flask_restful',
    ],
)
spec.add_tag({'name': 'featureRequest'})
spec.add_tag({'name': 'productArea'})
spec.add_tag({'name': 'client'})
spec.definition('FeatureRequest', schema=FeatureRequestSchema)
spec.definition('Client', schema=ClientSchema)
spec.definition('ProductArea', schema=ProductAreaSchema)
spec.add_path(resource=FeatureRequestListResource, api=api)
spec.add_path(resource=ClientResource, api=api)
spec.add_path(resource=ProductAreaResource, api=api)

@app.route('/v1')
def swagger():
    return jsonify(spec.to_dict())

@app.cli.command('swagger')
def show_swagger_yaml():
    print(spec.to_yaml())

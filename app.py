import typing as t

from flask import Flask, request, url_for, jsonify
from sqlalchemy.exc import IntegrityError

app = Flask(__name__)
app.config.from_object('default_settings')


@app.route('/')
def root():
    return '<h1>Hello World</h1>'


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
    priority = db.Column(db.Integer,
                         db.CheckConstraint('priority > 0',
                                            name='positive_priority'),
                         nullable=False)
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
                (db.session.query(FeatureRequest)
                 .filter(cls.client_id == self.client_id)
                 .filter(cls.priority >= self.priority)
                 .update({cls.priority: cls.priority + 1}))
            if '.title' in reason:
                return 'Unique title required'

    def save(self) -> t.Tuple[dict, int]:
        err = self.handle_unique_constraints()
        if err is not None:
            db.session.rollback()
            return {'errors': [err]}, 409

        db.session.commit()
        import schema
        self = self.query.get(self.id)
        result = schema.FeatureRequestSchema().dump(self)
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
from schema import FeatureRequestSchema
from flask_restful import Api, Resource


api = Api(app)

class FeatureRequestListResource(Resource):
    '''
    API resource create and list FeatureRequests
    '''
    schema = FeatureRequestSchema

    def get(self):
        reqs = self.schema(many=True).dump(FeatureRequest.query.all())
        return {'featurerequests': reqs}

    def post(self):
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


class FeatureRequestResource(Resource):
    '''
    API resource to read, update, and delete a FeatureRequest
    '''
    schema = FeatureRequestSchema

    def get(self, pk):
        req = FeatureRequest.query.get(pk)
        if req is None:
            return {'message': f'FeatureRequest {pk} could not be found.'}, 404
        req_data = self.schema().dump(req)
        return {'featurerequest': req_data}, 200

    def put(self, pk, partial=False):
        req = FeatureRequest.query.get(pk)
        if req is None:
            return {'message': f'FeatureRequest {pk} could not be found.'}, 404
        json_data = request.get_json()
        json_data['id'] = pk
        try:
            req = self.schema().load(json_data, partial=partial)
        except ValidationError as err:
            return {'errors': err.messages}, 422
        response, status = req.save()
        if status != 200:
            return response, status
        response['message'] = 'Modified FeatureRequest'
        return response, status

    def patch(self, pk):
        return self.put(pk, partial=True)
api.add_resource(FeatureRequestResource,
                 '/v1/featurerequest/<pk>')


# No need for "resources" for simple read-only listings.
@app.route('/v1/productarea')
def list_productareas():
    areas = ProductArea.query.all()
    return {'productareas': [{'id': a.id, 'name': a.name} for a in areas]}


@app.route('/v1/client')
def list_clients():
    clients = Client.query.all()
    return {'clients': [{'id': c.id, 'name': c.name} for c in clients]}


# Simple root for the API allowing some kind of discoverability.
@app.route('/v1')
def api_root():
    return jsonify({'resources': [
        url_for('featurerequestlistresource', _external=True),
        url_for('list_productareas', _external=True),
        url_for('list_clients', _external=True),
    ]})

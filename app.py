from flask import Flask
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config.from_object('default_settings')
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


@app.cli.command('drop-all')
def drop_all():
    db.drop_all()

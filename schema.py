from marshmallow import Schema, fields, post_load, validates


class FeatureRequestSchema(Schema):
    id = fields.Int()
    title = fields.Str(required=True)
    description = fields.Str(required=True)
    priority = fields.Int(required=True, validate=lambda v: v > 0)
    target_date = fields.Date(allow_none=True)
    client_id = fields.Int(required=True)
    client_name = fields.Str(attribute='client.name', dump_only=True)
    productarea_id = fields.Int(required=True)
    productarea_name = fields.Str(attribute='productarea.name', dump_only=True)

    @validates('client_id')
    def _client_id_exists(self, value):
        from app import db, Client
        q = (Client.query
             .filter(Client.client_id == value)
             .exists())
        return db.session.query(q).scalar()

    @validates('productarea_id')
    def _productarea_id_exists(self, value):
        from app import db, ProductArea
        q = (ProductArea.query
             .filter(ProductArea.productarea_id == value)
             .exists())
        return db.session.query(q).scalar()

    @post_load
    def make_orm_object(self, data):
        from app import FeatureRequest
        id = data.pop('id', None)
        if id:
            req = FeatureRequest.query.get(id)
            if req:
                for k, v in data.items():
                    setattr(req, k, v)
        else:
            req = FeatureRequest(**data)
        return req


class ClientSchema(Schema):
    id = fields.Int()
    name = fields.Str()


class ProductAreaSchema(Schema):
    id = fields.Int()
    name = fields.Str()

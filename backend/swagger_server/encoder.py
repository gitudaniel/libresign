from connexion.apps.flask_app import FlaskJSONEncoder
import six

class JSONEncoder(FlaskJSONEncoder):
    include_nulls = False

    def default(self, o):
        from .models.base_model_ import Model

        if isinstance(o, Model):
            dikt = {}
            for attr, _ in six.iteritems(o.swagger_types):
                value = getattr(o, attr)
                if value is None and not self.include_nulls:
                    continue
                attr = o.attribute_map[attr]
                dikt[attr] = value
            return dikt
        return FlaskJSONEncoder.default(self, o)

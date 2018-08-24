
from . import app

class TokenObject:
    def __init__(self, uid, tgt_doc=None):
        self.uid = uid
        self.tgt_doc = tgt_doc

@app.jwt.user_identity_loader
def _identity_loader(obj):
    if type(obj) == TokenObject:
        return obj.uid
    return obj

@app.jwt.user_claims_loader
def _add_claims_to_token(obj):
    target = None

    if type(obj) == TokenObject:
        target = obj.tgt_doc

    return {
        'target-document': target
    }
    

import json

from flask import Flask, request, Response

app = Flask(__name__)

@app.route('/', methods=['POST', 'GET'])
def log_output():
    data = request.get_json()

    print(json.dumps(data, indent=4))

    return Response(None, 200)

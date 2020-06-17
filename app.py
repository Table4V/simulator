from flask import Flask, send_from_directory, request, jsonify
from NewTranslator import TranslationWalk, InvalidTranslationWalk
from Context import Context, ContextFromJSON, ContextFromJSON5
from typing import Union
import benedict
app = Flask(__name__)


@app.route('/')
def mainpage():
    return send_from_directory('gui/modules', 'index.html')

@app.route('/advanced')
def advanced():
    return send_from_directory('gui/modules', 'advanced.html')


@app.route('/modules/<path:filename>')
def send_module(filename):
    return send_from_directory('gui/modules', filename)


def h2i(s: Union[str, None, int]) -> int:
    if not s:
        return None
    if type(s) == int:
        return s
    return int(s, 16)


def _clean(data: dict) -> dict:
    d = benedict.benedict(data)
    d['memory_size'] = h2i(d.get('memory_size'))
    d['lower_bound'] = h2i(d.get('lower_bound')) or 0
    d['satp.ppn'] = h2i(d.get('satp.ppn'))
    d['test_cases'] = [d]
    return d


@app.route('/api', methods=['POST'])
def simapi():
    data = request.get_json()
    # print('API called,', data)
    mgr = ContextFromJSON(_clean(data))
    d = mgr.jsonify()
    # print(d)
    return jsonify(d)

@app.route('/api/json5', methods=['POST'])
def json5api():
    data = request.get_json()
    data = data['code']
    mgr = ContextFromJSON5(data)
    d = mgr.jsonify()
    return jsonify(d)

if __name__ == "__main__":
    app.run("0.0.0.0", port=8080, debug=True)

import pandas as pd

from flask import Flask, request, jsonify

app = Flask(__name__)


@app.route('/api/data', methods=['GET'])
def retrieve_training_data():
    # gets all users
    if request.method == 'GET':
        df = pd.read_csv('../data/interim/hexes_nigeria_res7_thres30.csv')
        df = df.head(1000)
        return {'data': df.to_dict()}, 200


@app.route('/api/estimates', methods=['GET'])
def retrieve_microestimates_data():
    pass


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=105, debug=True)

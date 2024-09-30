from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests

app = Flask(__name__)
CORS(app)

API_KEY = os.environ.get('OPENAI_API_KEY')

@app.route('/api/process-request', methods=['POST'])
def process_request():
    data = request.json
    user_request = data.get('request')

    if not API_KEY:
        return jsonify({"error": "API key not set"}), 500

    try:
        response = requests.post(
            'https://api.openai.com/v1/chat/completions',
            headers={
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {API_KEY}'
            },
            json={
                "model": "gpt-4",
                "messages": [
                    {"role": "system", "content": "You are an AI assistant that helps reformulate requests made by users and make them as specific as possible for vendors."},
                    {"role": "user", "content": f'Suggest to the user an improved request, made by improving the text by using more precise words, bulletpoints or any other tool to improve the needs definition. Conclude by asking the user if they want to proceed to the next step. Here is the request: "{user_request}"'}
                ]
            }
        )

        response.raise_for_status()
        return jsonify(response.json())

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
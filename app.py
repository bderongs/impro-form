from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import requests
import time
import logging

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.DEBUG)

API_KEY = os.environ.get('OPENAI_API_KEY')
ASSISTANT_ID = "asst_3J2uyW9Kut0dVJBTGW1Rjmw2"

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

@app.route('/api/start-conversation', methods=['POST', 'OPTIONS'])
def start_conversation():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json
    user_message = data.get('message')

    if not API_KEY:
        return jsonify({"error": "API key not set"}), 500

    try:
        # Create a thread
        app.logger.info("Create thread")
        thread_response = requests.post(
            'https://api.openai.com/v1/threads',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            },
            json= {"messages": [
                {
                "role": "assistant", 
                "content": "L'industrie de l'entreprise est la création de site web"
            }]}
        )
        app.logger.info("End thread")
        thread_response.raise_for_status()
        thread_id = thread_response.json()['id']

        # Add the initial message and get the response
        response = send_message_and_get_response(thread_id, user_message)

        return jsonify({"thread_id": thread_id, "response": response})

    except requests.exceptions.RequestException as e:
        error_message = str(e)
        if hasattr(e, 'response') and e.response is not None:
            error_message += f". Response: {e.response.text}"
        return jsonify({"error": error_message}), 500

@app.route('/api/send-message', methods=['POST', 'OPTIONS'])
def send_message():
    if request.method == 'OPTIONS':
        return '', 204
    data = request.json
    thread_id = data.get('thread_id')
    user_message = data.get('message')

    if not API_KEY:
        return jsonify({"error": "API key not set"}), 500

    if not thread_id:
        return jsonify({"error": "Thread ID is required"}), 400

    try:
        response = send_message_and_get_response(thread_id, user_message)
        return jsonify({"response": response})

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

def send_message_and_get_response(thread_id, user_message):
    # Add a message to the thread
    message_response = requests.post(
        f'https://api.openai.com/v1/threads/{thread_id}/messages',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}',
            'OpenAI-Beta': 'assistants=v2'
        },
        json={
            "role": "user",
            "content": user_message
        }
    )
    message_response.raise_for_status()

    # Run the assistant
    run_response = requests.post(
        f'https://api.openai.com/v1/threads/{thread_id}/runs',
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {API_KEY}',
            'OpenAI-Beta': 'assistants=v2'
        },
        json={
            "assistant_id": ASSISTANT_ID
        }
    )
    run_response.raise_for_status()
    run_id = run_response.json()['id']

    # Wait for the run to complete
    while True:
        run_status_response = requests.get(
            f'https://api.openai.com/v1/threads/{thread_id}/runs/{run_id}',
            headers={
                'Authorization': f'Bearer {API_KEY}',
                'OpenAI-Beta': 'assistants=v2'
            }
        )
        run_status_response.raise_for_status()
        status = run_status_response.json()['status']
        app.logger.info("Status : %s", status)
        if status == 'completed':
            break
        if status == 'failed':
            app.logger.info("Run failed")
            app.logger.info(run_status_response.json())
            break
        time.sleep(1)

    # Retrieve the assistant's response
    messages_response = requests.get(
        f'https://api.openai.com/v1/threads/{thread_id}/messages',
        headers={
            'Authorization': f'Bearer {API_KEY}',
            'OpenAI-Beta': 'assistants=v2'
        }
    )
    messages_response.raise_for_status()
    messages = messages_response.json()['data']
    assistant_message = next(msg for msg in messages if msg['role'] == 'assistant')

    return assistant_message['content'][0]['text']['value']

if __name__ == '__main__':
    app.run(debug=True)
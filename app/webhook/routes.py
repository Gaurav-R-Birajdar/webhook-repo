from flask import Blueprint, json, request, jsonify
from app.extensions import mongo
import datetime

webhook = Blueprint('Webhook', __name__, url_prefix='/webhook')

@webhook.route('/receiver', methods=["POST"])
def receiver():
    # Handle GitHub 'ping' event for webhook setup verification
    if request.headers.get('X-GitHub-Event') == 'ping':
        return jsonify({'msg': 'Ping successful'}), 200

    # Process 'push' events 
    if request.headers.get('X-GitHub-Event') == 'push':
        data = request.json
        author = data['pusher']['name']
        to_branch = data['ref'].split('/')[-1]
        timestamp = datetime.datetime.fromisoformat(data['head_commit']['timestamp'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
        request_id = data['head_commit']['id'] # Git commit hash 

        event_data = {
            "request_id": request_id,
            "author": author,
            "action": "PUSH",
            "from_branch": None, # Not applicable for direct push
            "to_branch": to_branch,
            "timestamp": timestamp
        }
        mongo.db.github_events.insert_one(event_data) # 'github_events' is the collection name
        print(f"Stored PUSH event: {event_data}")

    # Process 'pull_request' events 
    elif request.headers.get('X-GitHub-Event') == 'pull_request':
        data = request.json
        action_type = data['action']

        # Handle 'PULL_REQUEST' (when a pull request is opened) 
        if action_type == 'opened':
            author = data['pull_request']['user']['login']
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            timestamp = datetime.datetime.fromisoformat(data['pull_request']['created_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
            request_id = data['pull_request']['id'] # Pull Request ID 

            event_data = {
                "request_id": str(request_id),
                "author": author,
                "action": "PULL_REQUEST",
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }
            mongo.db.github_events.insert_one(event_data)
            print(f"Stored PULL_REQUEST event: {event_data}")

        # Handle 'MERGE' action (when a pull request is closed and merged) 
        elif action_type == 'closed' and data['pull_request']['merged']:
            author = data['pull_request']['merged_by']['login']
            from_branch = data['pull_request']['head']['ref']
            to_branch = data['pull_request']['base']['ref']
            timestamp = datetime.datetime.fromisoformat(data['pull_request']['merged_at'].replace('Z', '+00:00')).strftime("%Y-%m-%d %H:%M:%S UTC")
            request_id = data['pull_request']['merge_commit_sha'] # Use merge commit hash 

            event_data = {
                "request_id": request_id,
                "author": author,
                "action": "MERGE",
                "from_branch": from_branch,
                "to_branch": to_branch,
                "timestamp": timestamp
            }
            mongo.db.github_events.insert_one(event_data)
            print(f"Stored MERGE event: {event_data}")

    return jsonify({'msg': 'Webhook received and processed'}), 200
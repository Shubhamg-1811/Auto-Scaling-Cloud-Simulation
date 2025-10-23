from flask import Flask, request, jsonify
import requests
import threading

app = Flask(__name__)

# --- State ---
servers = []
current_server_index = 0
request_counter = 0
lock = threading.Lock()

# --- API Endpoints ---
@app.route('/<path:page>')
def handle_request(page):
    """
    Receives client requests, selects a server using Round-Robin,
    and forwards the request.
    """
    global request_counter, current_server_index
   
    selected_server = None
   
    with lock:
        request_counter += 1
       
        if not servers:
            return "No available servers to handle the request.", 503
           
        selected_server = servers[current_server_index]
        current_server_index = (current_server_index + 1) % len(servers)

    # --- NEW: Log which server the request is being sent to ---
    print(f"[LB] Request for '{page}' forwarded to -> {selected_server}")

    try:
        resp = requests.get(f"{selected_server}/{page}", timeout=5)
        return resp.text, resp.status_code
    except requests.exceptions.RequestException as e:
        print(f"[LB] ERROR: Server {selected_server} is unavailable: {e}")
        return f"The server at {selected_server} is currently unavailable.", 503


@app.route('/update_servers', methods=['POST'])
def update_servers():
    """Endpoint for the scheduler to update the list of active servers."""
    global servers, current_server_index
    new_server_list = request.json.get('servers', [])
   
    with lock:
        servers = new_server_list
        current_server_index = 0
       
    print(f"[LB] Updated server list: {servers}")
    return "Servers updated successfully.", 200


@app.route('/metrics')
def get_metrics():
    """Endpoint for the scheduler to get the recent request count."""
    global request_counter
   
    with lock:
        count = request_counter
        request_counter = 0
       
    return jsonify({"request_count_10s": count})


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000, debug=False)

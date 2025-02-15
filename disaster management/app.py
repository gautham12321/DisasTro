from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import os
from math import radians, sin, cos, sqrt, atan2

# Initialize Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Load hubs and relief camps data from file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "hubs.json")

allocations_data = []  # Variable to store allocations in current session

def load_data():
    try:
        with open(DATA_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading data: {e}")
        return {"hubs": [], "relief_camps": []}

def save_data(data):
    with open(DATA_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

data = load_data()
HUBS = data["hubs"]
RELIEF_CAMPS = data["relief_camps"]

def calculate_distance(loc1, loc2):
    R = 6371.0
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])
    
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

@app.route('/')
def index():
    print(allocations_data)
    return render_template("index.html")

@app.route('/hub')
def hub_page():
    return render_template("hub.html")

@app.route('/hubs.json',methods=['GET'])
def hubs_json():
    print("hiiiiii")
    return jsonify(load_data())

@app.route('/allocate_hub', methods=['POST'])
def allocate_to_hub():
    global allocations_data
    try:
        data = load_data()
        HUBS, RELIEF_CAMPS = data["hubs"], data["relief_camps"]

        req_data = request.json
        relief_camp_requests = req_data.get("requests", [])

        if not relief_camp_requests:
            return jsonify({"error": "Invalid request data"}), 400

        priority_order = {"children": 1, "elderly": 2, "women": 3, "men": 4}
        relief_camp_requests.sort(
            key=lambda req: (
                priority_order.get(req.get("priority", "men"), 4),
                -req.get("time_since_last_request", 0)
            )
        )

        allocations = []
        hub_index = 0

        for req in relief_camp_requests:
            resource = req.get("resource")
            units_needed = req.get("units")
            relief_camp_name = req.get("relief_camp")

            if not resource or not isinstance(units_needed, int) or units_needed <= 0:
                continue

            for _ in range(len(HUBS)):
                hub = HUBS[hub_index]
                hub_index = (hub_index + 1) % len(HUBS)

                available_units = hub["resources"].get(resource, 0)
                if available_units > 0:
                    alloc_units = min(units_needed, available_units)
                    units_needed -= alloc_units
                    hub["resources"][resource] -= alloc_units

                    allocation_entry = {
                        "resource": resource,
                        "allocated_to": relief_camp_name,
                        "hub": hub["name"],
                        "allocated_units": alloc_units,
                        "status": "Allocated"
                    }
                    allocations.append(allocation_entry)
                    allocations_data.append(allocation_entry)

                if units_needed <= 0:
                    break

            if units_needed > 0:
                allocation_entry = {
                    "resource": resource,
                    "allocated_to": relief_camp_name,
                    "hub": "N/A",
                    "allocated_units": "Not fully allocated",
                    "status": "Pending"
                }
                allocations.append(allocation_entry)
                allocations_data.append(allocation_entry)

        save_data({"hubs": HUBS, "relief_camps": RELIEF_CAMPS})

        return jsonify(allocations_data)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/session_allocations', methods=['GET'])
def get_session_allocations():
    return jsonify(allocations_data)

if __name__ == '__main__':
    app.run(debug=True)

from flask import Flask, request, jsonify, send_from_directory, render_template
from flask_cors import CORS  # Enable cross-origin requests
import json
from math import radians, sin, cos, sqrt, atan2
import os
import time

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "hubs.json")

# Initialize Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)  # Enable CORS for frontend requests

# Load hubs and relief camps data
try:
    with open(DATA_PATH, encoding="utf-8") as f:
        data = json.load(f)
    HUBS = data.get("hubs", [])
    RELIEF_CAMPS = data.get("relief_camps", [])
except (FileNotFoundError, json.JSONDecodeError) as e:
    print(f"Error loading data: {e}")
    HUBS, RELIEF_CAMPS = [], []

# Serve the index.html page for relief camps
@app.route('/')
def index():
    return render_template("index.html")

# Serve the hub-side management interface
@app.route('/hub')
def hub_page():
    return render_template("hub.html")

# Serve static files like favicon
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.getcwd(), 'favicon.ico')

# Function to calculate the distance between two geographical points (Haversine formula)
def calculate_distance(loc1, loc2):
    R = 6371.0  # Earth radius in km
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])

    dlat = lat2 - lat1
    dlon = lon2 - lon1

    a = sin(dlat / 2)**2 + cos(lat1) * cos(lat2) * sin(dlon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    return R * c  # Distance in km

# Allocate resources to relief camps from the nearest hubs
@app.route('/allocate', methods=['POST'])
def allocate_to_relief_camp():
    try:
        data = request.json
        location = data.get('location')
        requests = data.get('requests', [])

        if not location or not requests:
            return jsonify({"error": "Invalid request data"}), 400

        allocations = []

        for req in requests:
            resource = req.get('resource')
            units_needed = req.get('units')

            if not resource or not isinstance(units_needed, int) or units_needed <= 0:
                continue  # Skip invalid requests

            # Filter hubs that have the requested resource
            available_hubs = [hub for hub in HUBS if hub["resources"].get(resource, 0) > 0]

            # Sort hubs by distance to the relief camp
            available_hubs.sort(key=lambda hub: calculate_distance(location, hub["location"]))

            total_allocated = 0
            for hub in available_hubs:
                if total_allocated >= units_needed:
                    break

                hub_resources = hub["resources"].get(resource, 0)
                if hub_resources > 0:
                    alloc_units = min(units_needed - total_allocated, hub_resources)
                    total_allocated += alloc_units
                    hub["resources"][resource] -= alloc_units  # Reduce available units

                    allocations.append({
                        "resource": resource,
                        "allocated_to": "Relief Camp",
                        "hub": hub["name"],
                        "allocated_units": alloc_units
                    })

            # If not all requested units are allocated
            if total_allocated < units_needed:
                allocations.append({
                    "resource": resource,
                    "allocated_to": "Relief Camp",
                    "hub": "N/A",
                    "allocated_units": "Not fully allocated"
                })

        return jsonify(allocations)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Priority Round-Robin allocation for hubs
@app.route('/allocate_hub', methods=['POST'])
def allocate_to_hub():
    try:
        data = request.json
        relief_camp_requests = data.get('requests', [])

        if not relief_camp_requests:
            return jsonify({"error": "Invalid request data"}), 400

        # Define priority order
        priority_order = {"children": 1, "elderly": 2, "women": 3, "men": 4}
        
        # Sort relief camps by priority (lower value = higher priority)
        relief_camp_requests.sort(
            key=lambda req: (
                priority_order.get(req.get("priority", "men"), 4),
                -req.get("time_since_last_request", 0)  # More time since last request = higher priority
            )
        )

        allocations = []
        hub_index = 0  # Round-robin index for hubs

        for req in relief_camp_requests:
            resource = req.get('resource')
            units_needed = req.get('units')

            if not resource or not isinstance(units_needed, int) or units_needed <= 0:
                continue

            # Round-robin allocation across hubs
            for _ in range(len(HUBS)):  # Ensure we loop through all hubs
                hub = HUBS[hub_index]
                hub_index = (hub_index + 1) % len(HUBS)  # Move to next hub

                hub_resources = hub["resources"].get(resource, 0)
                if hub_resources > 0:
                    alloc_units = min(units_needed, hub_resources)
                    units_needed -= alloc_units
                    hub["resources"][resource] -= alloc_units  # Reduce inventory

                    allocations.append({
                        "resource": resource,
                        "allocated_to": req["relief_camp"],
                        "hub": hub["name"],
                        "allocated_units": alloc_units,
                        "status": "Allocated"
                    })

                if units_needed <= 0:
                    break  # Move to the next request

            # If not all requested units are allocated
            if units_needed > 0:
                allocations.append({
                    "resource": resource,
                    "allocated_to": req["relief_camp"],
                    "hub": "N/A",
                    "allocated_units": "Not fully allocated",
                    "status": "Pending"
                })

        return jsonify(allocations)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)

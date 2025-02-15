from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_cors import CORS
import json
import os
from math import radians, sin, cos, sqrt, atan2

# Get the directory where app.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_PATH = os.path.join(BASE_DIR, "data", "hubs.json")
allocations_data=[]
# Initialize Flask app
app = Flask(__name__, template_folder="templates")
CORS(app)

# Load hubs and relief camps data
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

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/hub')
def hub_page():
    return render_template("hub.html")

@app.route('/hubs.json')
def hubs_json():
    return jsonify(load_data())

def calculate_distance(loc1, loc2):
    R = 6371.0
    lat1, lon1 = radians(loc1[0]), radians(loc1[1])
    lat2, lon2 = radians(loc2[0]), radians(loc2[1])
    
    dlat, dlon = lat2 - lat1, lon2 - lon1
    a = sin(dlat / 2) ** 2 + cos(lat1) * cos(lat2) * sin(dlon / 2) ** 2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    
    return R * c

@app.route('/allocate', methods=['POST'])
def allocate_to_relief_camp():
    try:
        data = load_data()
        HUBS, RELIEF_CAMPS = data["hubs"], data["relief_camps"]

        req_data = request.json
        relief_camp_name = req_data.get("relief_camp")
        location = req_data.get("location")
        requests = req_data.get("requests", [])

        if not relief_camp_name or not location or not requests:
            return jsonify({"error": "Invalid request data"}), 400

        allocations = []

        for req in requests:
            resource = req.get("resource")
            units_needed = req.get("units")

            if not resource or not isinstance(units_needed, int) or units_needed <= 0:
                continue

            available_hubs = [hub for hub in HUBS if hub["resources"].get(resource, 0) > 0]
            available_hubs.sort(key=lambda hub: calculate_distance(location, hub["location"]))

            total_allocated = 0
            for hub in available_hubs:
                if total_allocated >= units_needed:
                    break

                available_units = hub["resources"].get(resource, 0)
                alloc_units = min(units_needed - total_allocated, available_units)
                total_allocated += alloc_units
                hub["resources"][resource] -= alloc_units

                allocations.append({
                    "resource": resource,
                    "allocated_to": relief_camp_name,
                    "hub": hub["name"],
                    "allocated_units": alloc_units
                })

            if total_allocated < units_needed:
                allocations.append({
                    "resource": resource,
                    "allocated_to": relief_camp_name,
                    "hub": "N/A",
                    "allocated_units": "Not fully allocated"
                })

        for camp in RELIEF_CAMPS:
            if camp["name"] == relief_camp_name:
                if "allocations" not in camp:
                    camp["allocations"] = []
                camp["allocations"].extend(allocations)

        save_data({"hubs": HUBS, "relief_camps": RELIEF_CAMPS})
        pr

        return jsonify(allocations)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
def process_pending_allocations():
    """
    This function scans through each relief camp's allocations and
    attempts to process any pending allocation requests using any newly
    available resources from the hubs.
    """
    data = load_data()
    hubs = data["hubs"]
    relief_camps = data["relief_camps"]

    for camp in relief_camps:
        if "allocations" in camp:
            # Iterate over a copy of the allocations list to avoid modification issues.
            for alloc in list(camp["allocations"]):
                if alloc.get("status") == "Pending" and alloc.get("units_remaining", 0) > 0:
                    resource = alloc["resource"]
                    units_remaining = alloc["units_remaining"]

                    # Try to allocate remaining units from any hub with available resources.
                    for hub in hubs:
                        if units_remaining <= 0:
                            break
                        available_units = hub["resources"].get(resource, 0)
                        if available_units > 0:
                            alloc_units = min(units_remaining, available_units)
                            hub["resources"][resource] -= alloc_units
                            units_remaining -= alloc_units

                            new_alloc = {
                                "resource": resource,
                                "allocated_to": camp["name"],
                                "hub": hub["name"],
                                "allocated_units": alloc_units,
                                "status": "Allocated"
                            }
                            camp["allocations"].append(new_alloc)
                            allocations_data.append(new_alloc)
                    # Update the pending allocation record.
                    alloc["units_remaining"] = units_remaining
                    if units_remaining <= 0:
                        alloc["status"] = "Allocated"
                        alloc["hub"] = "Multiple"
                        alloc["allocated_units"] = "Allocated across hubs"
    print(relief_camps)
    save_data({"hubs": hubs, "relief_camps": relief_camps})

@app.route('/allocate_hub', methods=['POST'])
def allocate_to_hub():
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

                    allocations.append({
                        "resource": resource,
                        "allocated_to": relief_camp_name,
                        "hub": hub["name"],
                        "allocated_units": alloc_units,
                        "status": "Allocated"
                    })

                if units_needed <= 0:
                    break

            if units_needed > 0:
                allocations.append({
                    "resource": resource,
                    "allocated_to": relief_camp_name,
                    "hub": "N/A",
                    "allocated_units": "Not fully allocated",
                    "allocated_units": 0,
                    "units_remaining": units_needed,
                    "status": "Pending"
                })
        allocations_data.extend(allocations)    

        for camp in RELIEF_CAMPS:
            for alloc in allocations:
                if camp["name"] == alloc["allocated_to"]:
                    if "allocations" not in camp:
                        camp["allocations"] = []
                    camp["allocations"].append(alloc)

        save_data({"hubs": HUBS, "relief_camps": RELIEF_CAMPS})
        print(allocations)
        return jsonify(allocations)

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    
@app.route('/update_inventory', methods=['POST'])
def update_inventory():
    """
    Update the inventory of a specific hub.
    Expected JSON payload:
    {
        "hub_name": "Hub A",
        "resources": {
            "water": 100,
            "food": 50
        },
        "update_type": "add"  # optional, can be "set" or "add" (default is "set")
    }
    """
    try:
        data = load_data()
        hubs = data["hubs"]

        req_data = request.json
        hub_name = req_data.get("hub_name")
        resources_update = req_data.get("resources")
        update_type = req_data.get("update_type", "set")  # default is "set"

        if not hub_name or not resources_update:
            return jsonify({"error": "hub_name and resources are required"}), 400

        if update_type not in ("set", "add"):
            return jsonify({"error": "update_type must be either 'set' or 'add'"}), 400

        # Find the hub by name
        hub = next((h for h in hubs if h.get("name") == hub_name), None)
        if not hub:
            return jsonify({"error": "Hub not found"}), 404

        # Update the inventory for each resource
        for resource, value in resources_update.items():
            if not isinstance(value, (int, float)):
                return jsonify({"error": f"Value for resource '{resource}' must be numeric"}), 400
            if update_type == "set":
                hub["resources"][resource] = value
            elif update_type == "add":
                hub["resources"][resource] = hub["resources"].get(resource, 0) + value

        save_data(data)
        process_pending_allocations()
        return jsonify({"message": "Hub inventory updated successfully", "hub": hub})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
@app.route('/session_allocations',methods=['GET'])
def session_all():
    return jsonify(allocations_data)
if __name__ == '__main__':
    app.run(debug=True)
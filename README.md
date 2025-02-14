# AidLink

AidLink is an intelligent relief distribution system that optimizes the routing of resources from supply hubs to relief centers. It uses a greedy algorithm that prioritizes deliveries based on urgency, the demographics of affected populations, and the time since their last delivery.

# Features

Priority Score Calculation: Assigns priority to each relief center based on urgency, the number of people in different age groups, and the last delivery time.

Greedy Algorithm: Ensures efficient allocation of resources by iteratively selecting the most critical relief center.

Dynamic Routing: Adjusts delivery routes in real-time based on changing conditions and resource availability.

Scalability: Can handle multiple hubs and relief centers with varying needs.

# Algorithm Overview

Priority Score Calculation: Each relief center is assigned a score based on:

Urgency level (e.g., medical emergencies, food shortages, etc.)

Number of people in vulnerable age groups (children, elderly, etc.)

Time elapsed since the last delivery

Resource Allocation: Resources are assigned to the highest-priority relief center first.

Greedy Selection: The algorithm iterates through available resources and selects the next best relief center based on recalculated scores.

Route Optimization: Attempts to minimize travel time while maximizing resource impact.


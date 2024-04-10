import osmnx as ox
import networkx as nx
from collections import deque
import colorsys
import random

# Load graph from GML
graph = ox.io.load_graphml('graph_ubc.gml')

# Helper function that determines if edge (v,w) is a valid candidate for adding to the graph
def good(gst, d, v, w):
    return w not in list(gst.adj[v]) and \
           v not in list(gst.adj[w]) and \
           graph.edges[v, w, 0]['length'] > 0 \
           and d + graph.edges[v, w, 0]['length'] <= goal_dist

# Helper function that returns the absolute difference between any 2 given directions.
# Note that the value should never be more than 180, since a left turn of x is
# equivalent to a right turn of (360 - x).
def get_bearing_diff(b1, b2):
    bdiff = abs(b1 - b2) % 360  # allows for neg and large bearings
    if bdiff > 180:
        bdiff = 360 - bdiff
    return bdiff

# Main dfs function. Given a start node, goal distance, and graph of distances,
# solve these 2 related questions:
# Part 1: return a subgraph whose edges are a trail with distance at least goal_distance
# Part 2: return a subgraph with the characteristics from Part 1, but change the definition
# of "neighbors" so that at every node, the direction of the next edge is as close as possible
# to the current direction. This feature changes the order in which the neighbors are considered.

def find_route(start, goal_dist, graph):
    # distances and feasible edges will come from 'graph', solution built in 'gstate'
    gstate = nx.DiGraph()
    gstate.add_nodes_from(graph)

    # need stack of: (gstate, prev node, curr node, totlen so far, number of edges in route so far)
    # init stack & push start vertex
    stack = deque()
    stack.append((gstate, start, start, 0, 0))
    # next two lines are necessary for part 2) so that every current bearing has a previous bearing to compare against
    graph.add_edge(start, start, 0)
    graph.edges[start, start, 0]['bearing'] = random.randint(0,360) # grab a random initial direction

    while stack:
        gst, prev, curr, lensofar, clock = stack.pop()  # gst, previous node, curr node, dist so far, edges so far

        if curr not in list(gst.neighbors(prev)):
            gst.add_edge(prev, curr)
            gst.edges[prev, curr]['time'] = clock # need this for path drawing

            # stopping criteria: if we've gone far enough, return our solution graph and the number of edges
            if lensofar > goal_dist:
                return gst, clock

            # neighbors for part 1)
            neighbors = graph.neighbors(curr)
            # neighbors for part 2)
            neighbors = sorted(graph.neighbors(curr),
                               key=lambda x: get_bearing_diff(graph.edges[prev, curr, 0]['bearing'],
                                                               graph.edges[curr, x, 0]['bearing']))

            for w in neighbors:
                if good(gst, lensofar, curr, w):
                    gstnew = nx.DiGraph(gst)  # Deep copy of gst
                    stack.append((gstnew, curr, w, lensofar + graph.edges[curr, w, 0]['length'], clock))  # Removed clock + 1

# returns the total elevation gain in gr, over the route described by rt (list of vertices).
# edges whose elevation gain is negative should be ignored.
# you can refer to a node's elevation by: gr.nodes[rt[k]]['elevation'], where k is the kth element
# of the rt list.
def total_elevation_gain(gr, rt):
    eg = 0
    for i in range(len(rt) - 1):
        elevation_gain = gr.nodes[rt[i + 1]]['elevation'] - gr.nodes[rt[i]]['elevation']
        if elevation_gain > 0:
            eg += elevation_gain
    return eg

# hsv color representation gives a rainbow from red and back to red over values 0 to 1.
# this function returns the color in rgb hex, given the current and total edge numbers
def shade_given_time(k, n):
    col = colorsys.hsv_to_rgb(k / n, 1.0, 1.0)
    tup = tuple((int(x * 255) for x in col)) # Corrected the multiplier
    st = f"#{tup[0]:02x}{tup[1]:02x}{tup[2]:02x}"
    return st

# Choose a starting location
lat, lon = 49.255, -123.255  # Wreck Beach
start = ox.nearest_nodes(graph, lon, lat)

goal_dist = 5000  # meters, must go at least this far

route, time = find_route(start, goal_dist, graph)

# Visualize map for sanity check
fig, ax = ox.plot_graph(route)

sorted_lst = sorted(route.edges(), key=lambda x: route.edges[x[0], x[1]]['time'])
routevertices = [x[0] for x in sorted_lst]
routevertices.append(sorted_lst[-1][1])

eg = total_elevation_gain(graph, routevertices)

# Initialize the map plot
m = ox.plot_graph_folium(graph, tiles='openstreetmap')

# Add the edges in the graph one at a time with rainbow color
for k, x in enumerate(sorted_lst[1:]):
    ox.plot_route_folium(graph, x, route_map=m, weight=5, color=shade_given_time(k, time))

# Place the elevation gain on the map at the end point of the workout.
endlat, endlon = graph.nodes[routevertices[-1]]['x'], graph.nodes[routevertices[-1]]['y']
folium.map.Marker(
    [endlat, endlon],
    icon=DivIcon(
        icon_size=(250, 36),
        icon_anchor=(0, 0),
        html=f'<div style="font-size: 20pt">Elevation Gain: {eg}m</div>',
    )
).add_to(m)

# Save the map to HTML file
filepath = "route_graph_workout.html"
m.save(filepath)

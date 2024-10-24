# flow_simulation.py
import networkx as nx
# Betim - Det er noget anders har importet så tænker ikke det er relevant da der ikke er noget i filen
# from delay_calculations import calculate_dPQ_TX, calculate_dTX_DQ, calculate_dDQ_SO
import time
import csv

def build_graph():
    G = nx.Graph()
    
    # Read from the small_topology.v2.csv file
    with open('small-topology.v2.csv', 'r') as f:
        reader = csv.reader(f)
        for row in reader: 
            if row[0] == 'SW':  # Switch
                # Add switch as a node
                G.add_node(row[1])
            elif row[0] == 'ES':  # End System
                # Add end system as a node
                G.add_node(row[1])
            elif row[0] == 'LINK':  # Link
                # Add edge between two nodes
                # Adjust indices based on how your CSV is structured
                G.add_edge(row[2], row[4])
    
    return G

def calculate_per_hop_delay(flow, link_rate):
    dPQ_TX = calculate_dPQ_TX(flow, flow['interfering_flows'], link_rate)
    dTX_DQ = calculate_dTX_DQ(flow['size'], link_rate)
    dDQ_SO = calculate_dDQ_SO(flow, flow['interfering_flows'], link_rate)
    return dPQ_TX + dTX_DQ + dDQ_SO

def simulate_flows(flows, num_hops):
    link_rate = 1e9  # 1 Gbps
    delays = []
    start_time = time.time()
    
    # Build the network graph from the topology
    G = build_graph()

    for flow in flows:
        src = flow['src']  # Adjust this based on your flow structure
        dst = flow['dst']  # Adjust this based on your flow structure
        
        # Check if there's a path
        if nx.has_path(G, src, dst):
            # Calculate interfering flows
            interfering_flows = [f for f in flows if f != flow and nx.has_path(G, f['src'], f['dst'])]
            flow['interfering_flows'] = interfering_flows
            
            e2e_delay = 0
            for _ in range(num_hops):
                e2e_delay += calculate_per_hop_delay(flow, link_rate)
            delays.append(e2e_delay)
        else:
            print(f"No path found for flow {flow['flow_id']} from {src} to {dst}.")
            delays.append(None)  # or some default value to indicate no delay
    
    runtime = time.time() - start_time
    mean_delay = sum(d for d in delays if d is not None) / len(delays) if delays else 0
    max_delay = max(d for d in delays if d is not None) if delays else 0
    return runtime, mean_delay, max_delay, delays
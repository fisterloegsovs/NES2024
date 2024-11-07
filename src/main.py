import csv
from collections import deque, defaultdict
import queue
from enum import Enum
import networkx as nx
import time
import numpy as np
from dataclasses import dataclass

small_streams_csv = 'small-streams.v2.csv'
small_topology_csv = 'small-topology.v2.csv'

def streams_csv(filename):
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            small_streams = list(reader)
            # Print the list
            print(small_streams)
            # Check if the first row is a header
            if small_streams[0][0] == 'PCP':
                small_streams = small_streams[1:]  # Skip the header row
        return small_streams
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def topology_csv(filename):
    try:
        with open(filename, 'r') as f:
            reader = csv.reader(f)
            small_topology = list(reader)
        return small_topology
    except FileNotFoundError:
        print(f"File {filename} not found.")
        return []
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

queue_dict = defaultdict(lambda: {i: queue.Queue() for i in range(8)})

def calculate_r_b(size, period):
    b = size
    r = size / period
    return r, b

class Device_Type(Enum):
    NA = 0
    ES = 1
    SW = 2

@dataclass
class Node:
    device_type: Device_Type
    device_name: str
    ports: int
    domain: str

@dataclass
class Link:
    link_id: str
    source_device: str
    source_port: int
    dest_device: str
    dest_port: int
    domain: str

class Stream_type(Enum):
    NONE = 0
    ATS = 1
    AVB = 2

class Stream:
    def __init__(self, pcp, stream_name, stream_type, source_node, dest_node, size, period, deadline):
        self.pcp = pcp
        self.stream_name = stream_name
        self.stream_type = stream_type
        self.source_node = source_node
        self.dest_node = dest_node
        self.size = size
        self.period = period
        self.deadline = deadline
        self.r, self.b = calculate_r_b(size, period) if stream_type == Stream_type.ATS else (None, None)
        self.path = []
        
    def __repr__(self):
        return f"Stream {self.stream_name} from {self.source_node} to {self.dest_node} with size {self.size} and period {self.period}"

class Network_Graph:
    def __init__(self):
        self.edges = []
        self.vertices = []
        self.graph = nx.Graph()
        self.stream_delays = {}

    def add_edge(self, edge):
        self.edges.append(edge)
        self.graph.add_edge(edge.source_device, edge.dest_device)

    def add_vertex(self, vertex):
        self.vertices.append(vertex)

    def read_topology(self):
        topology = topology_csv(small_topology_csv)
        for node in topology:
            try:
                if node[0] == 'LINK':
                    if len(node) < 6:
                        raise IndexError(f"Link row does not have enough columns: {node}")
                    temp_link = Link(node[1], node[2], int(node[3]), node[4], int(node[5]), node[6] if len(node) > 6 else None)
                    self.add_edge(temp_link)
                else:
                    device_type = Device_Type.ES if node[0] == 'ES' else Device_Type.SW
                    domain = node[3] if len(node) > 3 else None
                    temp_node = Node(device_type, node[1], int(node[2]), domain)
                    self.add_vertex(temp_node)
            except IndexError as e:
                print(f"Error: {e}")
            except ValueError:
                print(f"Error: Invalid data type in row: {node}")
        return self

    def read_streams(self):
        streams = streams_csv(small_streams_csv)
        for stream in streams:
            try:
                pcp = int(stream[0])
                temp_stream = Stream(
                    pcp,
                    stream[1],
                    Stream_type.ATS if stream[2].lower() == 'ats' else Stream_type.AVB,
                    stream[3],
                    stream[4],
                    int(stream[5]),
                    int(stream[6]),
                    int(stream[7])
                )
            except ValueError as e:
                print(f"Error: {e} in row: {stream}")
                continue

            source = temp_stream.source_node
            destination = temp_stream.dest_node
            
            try:
                shortest_path = nx.shortest_path(self.graph, source=source, target=destination)
                print(f"Shortest path for stream {temp_stream.stream_name}: {shortest_path}")
                temp_stream.path = shortest_path 
            except nx.NetworkXNoPath:
                print(f"No path found for stream {temp_stream.stream_name} from {source} to {destination}")
                continue
            
            # Priority is from 0 to 7 so highest priority is 0 and lowest is 7
            queue_dict[source][pcp].put(temp_stream) 
            print(f"Added stream {temp_stream.stream_name} to queue {pcp} of source {source}")
            self.stream_delays[temp_stream.stream_name] = self.calculate_delay(temp_stream) * 1e6  # Convert to microseconds
        return self

    def calculate_delay(self, stream):
            # Ensure link capacity matches previously calculated for the target delay
            link_capacity = 1000000000  # 1 Gbps
            
            total_delay = 0
            for i in range(len(stream.path) - 1):
                source_node = stream.path[i]
                dest_node = stream.path[i + 1]
                
                accumulated_burst = 0
                for q in queue_dict[source_node].values():
                    if not q.empty():
                        head_stream = q.queue[0]
                        if head_stream.b is not None:
                            accumulated_burst += head_stream.b
                
                remaining_bandwidth = self.calculate_remaining_bandwidth(source_node, link_capacity)
                if remaining_bandwidth <= 0:
                    return float('inf')
                
                # Transmission delay over link
                transmission_delay = stream.size / remaining_bandwidth
                
                # Queueing delay based on accumulated burst
                dP_Q_T_X = accumulated_burst / remaining_bandwidth
                
                # Shaping delay refinement
                shaping_delay = stream.period / remaining_bandwidth
                
                # Total delay for this hop
                hop_delay = dP_Q_T_X + transmission_delay + shaping_delay
                
                total_delay += hop_delay
                queue_dict[dest_node][stream.pcp].put(stream)

            return total_delay

    def calculate_remaining_bandwidth(self, source_node, link_capacity):
        total_reserved_rate = sum(stream.r for q in queue_dict[source_node].values() for stream in q.queue if stream.pcp < 8 and stream.r is not None)
        remaining_bandwidth = link_capacity - total_reserved_rate
        return remaining_bandwidth if remaining_bandwidth > 0 else 0

start_time = time.time()

network_graph = Network_Graph()
network_graph.read_topology().read_streams()

delays = list(network_graph.stream_delays.values())
mean_delay = np.mean(delays) if delays else 0
max_delays = {stream_name: delay for stream_name, delay in network_graph.stream_delays.items()}

end_time = time.time()
runtime = end_time - start_time

with open("evaluation_results.txt", "w") as f:
    f.write(f"Runtime (seconds): {runtime:.2f}\n")
    f.write(f"Mean E2E Delay (µs): {mean_delay:.2f}\n")
    f.write("Maximum E2E Delay for each flow (µs):\n")
    for stream_name, max_delay in max_delays.items():
        f.write(f"{stream_name}: {max_delay:.2f}\n")

print(f"Runtime (seconds): {runtime:.2f}")
print(f"Mean E2E Delay (µs): {mean_delay:.2f}")
print("Maximum E2E Delay for each flow (µs):")
for stream_name, max_delay in max_delays.items():
    print(f"{stream_name}: {max_delay:.2f}")

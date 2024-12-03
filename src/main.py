import csv
from collections import defaultdict
import queue
from enum import Enum
import networkx as nx
from dataclasses import dataclass

small_streams_csv = 'csv-files/small-streams.v2.csv'
small_topology_csv = 'csv-files/small-topology.v2.csv'

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
        self.paths = []  # Define paths attribute to store streams
        self.queues = defaultdict(lambda: defaultdict(lambda: {i: [] for i in range(8)}))


    def add_edge(self, edge):
        self.edges.append(edge)
        self.graph.add_edge(edge.source_device, edge.dest_device)

    def add_vertex(self, vertex):
        self.vertices.append(vertex)
        self.graph.add_node(vertex.device_name)

    def add_stream_to_queue(self, stream):
        source = stream.source_node
        destination = stream.dest_node
        pcp = stream.pcp

        # QAR1: Streams from different sources can't share the same queue
        for other_stream in self.queues[source][destination][pcp]:
            if other_stream.source_node != source:
                raise ValueError(f"QAR1 Violated: Stream {stream.stream_name} shares queue with stream from {other_stream.source_node}")

        # QAR2: Streams from the same source but different PCP can't share
        for priority in range(8):
            if priority != pcp and self.queues[source][destination][priority]:
                raise ValueError(f"QAR2 Violated: Stream {stream.stream_name} shares source with different priority stream")

        # Add the stream if QARs hold
        assert isinstance(stream, Stream), "Only Stream objects should be added to the queue."
        self.queues[source][destination][pcp].append(stream)
        print(f"Stream {stream.stream_name} added to queue {pcp} of {source} -> {destination}")


    def read_topology(self):
        topology = topology_csv(small_topology_csv)
        for node in topology:
            try:
                if node[0] == 'LINK':
                    if len(node) < 6:
                        raise IndexError(f"Link row does not have enough columns: {node}")
                    temp_link = Link(node[1], node[2], int(node[3]), node[4], int(node[5]), node[6] if len(node) > 6 else None)
                    self.add_edge(temp_link)
                    self.graph.add_edge(node[2], node[4])  # Add edge to graph
                else:
                    device_type = Device_Type.ES if node[0] == 'ES' else Device_Type.SW
                    domain = node[3] if len(node) > 3 else None
                    temp_node = Node(device_type, node[1], int(node[2]), domain)
                    self.add_vertex(temp_node)
                    self.graph.add_node(node[1])  # Add node to graph
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
            
            if source not in self.graph or destination not in self.graph:
                print(f"Source {source} or destination {destination} not in graph.")
                continue
            
            try:
                shortest_path = nx.shortest_path(self.graph, source=source, target=destination)
                print(f"Shortest path for stream {temp_stream.stream_name}: {shortest_path}")
                temp_stream.path = shortest_path 
            except nx.NetworkXNoPath:
                print(f"No path found for stream {temp_stream.stream_name} from {source} to {destination}")
                continue

            try:
                self.add_stream_to_queue(temp_stream)
            except ValueError as e:
                print(f"Queue assignment error for {temp_stream.stream_name}: {e}")
                continue

            self.paths.append(temp_stream)  # Add stream to paths
        return self

    def calculate_per_hop_delay(self, stream, source, dest):
        link_capacity = 10**9/8
        
        b_H = 0
        r_H = 0  

        for pcp in range(stream.pcp + 1, 8):
            for s in self.queues[source][dest][pcp]:
                if not isinstance(s, Stream):
                    raise TypeError(f"Queue contains non-Stream object: {type(s)}")
                b_H += s.size
                r_H += s.r

        # Calculate effective capacity and validate
        effective_capacity = link_capacity - r_H
        if effective_capacity <= 0:
            raise ValueError(f"Effective capacity is zero or negative: {effective_capacity}. Check stream configurations.")

        # Calculate delays
        dPQ_TX = b_H / effective_capacity
        l_f = stream.size
        dTX_DQ = l_f / link_capacity

        return dPQ_TX + dTX_DQ

    def calculate_worst_case_delay(self):
        delays = {}
        for stream in self.paths:
            total_delay = 0
            for i in range(len(stream.path) - 1):
                source = stream.path[i]
                dest = stream.path[i + 1]
                total_delay += self.calculate_per_hop_delay(stream, source, dest)
            total_delay_microseconds = total_delay * 1e6
            delays[stream.stream_name] = round(total_delay_microseconds, 3)
            print(f"Total end-to-end delay for stream {stream.stream_name}: {total_delay_microseconds:.3f} µs")
        return delays

network_graph = Network_Graph()
network_graph.read_topology().read_streams()

delays = network_graph.calculate_worst_case_delay()

with open("evaluation_results.txt", "w") as f:
    for stream_name, delay in delays.items():
        f.write(f"{stream_name}: {delay:.3f} µs\n")

print("Worst-case E2E Delays (µs):")
for stream_name, delay in delays.items():
    print(f"{stream_name}: {delay:.3f} µs")
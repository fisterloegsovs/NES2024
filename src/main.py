import csv
from collections import defaultdict
import networkx as nx
from dataclasses import dataclass
from enum import Enum

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

      # Simplified QAR1: Allow frames from different ingress ports to share the same shaped queues if they have the same priority level
      # QAR2: Frames from the same source but different PCP can share, but frames from the same source with the same PCP cannot share
      for qar in self.queues[source][destination][pcp]:
        if qar.stream_type == stream.stream_type:
          raise ValueError(f"Stream {stream.stream_name} with PCP {pcp} already exists in queue {pcp} of {source} -> {destination}")
      

      # Add the stream if QARs hold
      assert isinstance(stream, Stream), "Only Stream objects should be added to the queue."
      self.queues[source][destination][pcp].append(stream)
      print(f"Stream {stream.stream_name} added to queue {pcp} of {source} -> {destination}")

    def aggregate_queues(self):
      aggregated_queues = defaultdict(list)
      for source in self.queues:
          for dest in self.queues[source]:
              for pcp in self.queues[source][dest]:
                  aggregated_queues[pcp].extend(self.queues[source][dest][pcp])
      return aggregated_queues
        

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
        unique_pcp_values = set()
        for stream in streams:
            try:
                pcp = int(stream[0])
                unique_pcp_values.add(pcp)
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

        # Initialize queues based on unique PCP values
        self.queues = defaultdict(lambda: defaultdict(lambda: {pcp: [] for pcp in unique_pcp_values}))
        return self

    def calculate_per_hop_delay(self, stream, source, dest):
        link_capacity = 100e6  # Link capacity in bps (100 Mbps)
        processing_delay = 5e-6  # Processing delay in seconds (5 μs)

        # Calculate transmission delay
        transmission_delay = stream.size * 8 / link_capacity  # Convert size to bits

        # Aggregate all queues
        aggregated_queues = self.aggregate_queues()

        # Calculate blocking delay
        blocking_delay = 0
        for higher_pcp in range(stream.pcp):
            higher_priority_queue = aggregated_queues.get(higher_pcp, [])
            blocking_delay += sum([s.size * 8 / link_capacity for s in higher_priority_queue])
        
        print(f"Blocking delay from {source} to {dest} for stream {stream.stream_name}: {blocking_delay:.6f} seconds")

        # Total per-hop delay
        per_hop_delay = processing_delay + transmission_delay + blocking_delay
        print(f"Per-hop delay from {source} to {dest} for stream {stream.stream_name}: {per_hop_delay:.6f} seconds")
        return per_hop_delay

    def calculate_worst_case_delay(self):
        delays = {}
        for stream in self.paths:
            total_delay = 0
            for i in range(len(stream.path) - 1):
                source = stream.path[i]
                dest = stream.path[i + 1]
                per_hop_delay = self.calculate_per_hop_delay(stream, source, dest)
                total_delay += per_hop_delay

            total_delay_microseconds = total_delay * 1e6  # Convert to microseconds
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
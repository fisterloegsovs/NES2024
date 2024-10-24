import csv
import queue

# First parse the small_streams.csv and then the small_topology.csv files.

small_streams_csv = 'small-streams.v2.csv'
small_topology_csv = 'small-topology.v2.csv'

small_streams_fields = ['PCP', 'StreamName', 'StreamType', 'SourceNode', 'DestinationNode', 'Size', 'Period', 'Deadline']

small_topology_fields = ['DeviceType', 'DeviceName', 'Ports', 'Domain']

# Read and parse the small_streams.csv file
with open(small_streams_csv, 'r') as f:
    reader = csv.DictReader(f, fieldnames=small_streams_fields)
    small_streams = list(reader)
    # print(small_streams)
# Read and parse the small_topology.csv file
with open(small_topology_csv, 'r') as f:
    reader = csv.DictReader(f, fieldnames=small_topology_fields)
    small_topology = list(reader)
    

# Now we have the small_streams and small_topology data in memory.
def calculate_dPQ_TX(flow, qS, QH, linkrate):
    return

# - Beto implementation
# iterating the data
for i, stream in enumerate(small_streams):
    print(i, stream)

# Creating three queues for different priorities streams
queue_ready = {}
queue_high = {}
queue_low = {}


# Each node has ports where they can upload and recieve data
def get_create_queue(queues_dict, source_node):
    if source_node not in queues_dict:
        queues_dict[source_node] = queue.Queue()
    return queues_dict[source_node]

# add streams to the correct queues based on 'pcp value'
for stream in small_streams:
    pcp = int(stream['PCP'])
    source = stream['SourceNode']

    if pcp == 0:
        q = get_create_queue(queue_ready, source)
    elif pcp == 1:
        q = get_create_queue(queue_high, source)
    elif pcp == 2:
        q = get_create_queue(queue_low, source)
    q.put(stream)

print(f"Ready queue: {len(queue_ready)}")
print(f"High priority queue: {len(queue_high)}")
print(f"Low priority queue: {len(queue_low)}")

for source, q in queue_ready.items():
    print(f"Ready queue source {source} = {q.qsize()} items.")
for source, q in queue_high.items():
    print(f"High priority queue source {source} = {q.qsize()} items.")
for source, q in queue_low.items():
    print(f"Low priority queue source {source} = {q.qsize()} items.")


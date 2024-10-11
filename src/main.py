import csv

# First parse the small_streams.csv and then the small_topology.csv files.

small_streams_csv = 'small-streams.csv'
small_topology_csv = 'small-topology.csv'

small_streams_fields = ['PCP', 'StreamName', 'StreamType', 'SourceNode', 'DestinationNode', 'Size', 'Period', 'Deadline']

small_topology_fields = ['DeviceType', 'DeviceName', 'Ports', 'Domain']

# Read and parse the small_streams.csv file
with open(small_streams_csv, 'r') as f:
    reader = csv.DictReader(f, fieldnames=small_streams_fields)
    small_streams = list(reader)

# Read and parse the small_topology.csv file
with open(small_topology_csv, 'r') as f:
    reader = csv.DictReader(f, fieldnames=small_topology_fields)
    small_topology = list(reader)

# Now we have the small_streams and small_topology data in memory.
def calculate_dPQ_TX(flow, qS, QH, linkrate):
    



    


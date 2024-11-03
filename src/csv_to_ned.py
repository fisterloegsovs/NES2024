import csv
import argparse

#Example of usage: 
#python3 csv_to_ned.py /path/to/your/input.csv /path/to/output/generated_topology.ned
#For example: python3 csv_to_ned.py ~/Documents/small-topology.csv ~/Documents/generated_topology.ned
#This program assumes that the package is dtu_networks

def generate_ned_from_csv(csv_path, ned_path):
    """
    This function takes in a CSV file and generates a NED file with specified imports,
    connections based on LINK entries, and the package "dtu_networks".
    
    Parameters:
        csv_path (str): Path to the CSV file.
        ned_path (str): Path where the NED file will be saved.
    """
    # Define the gate names for TsnDevice and TsnSwitch, adjust as necessary
    device_gate_name = "ethg"  # Use the actual gate name from TsnDevice module if different
    switch_gate_name = "ethg"  # Use the actual gate name from TsnSwitch module if different
    
    with open(csv_path, 'r') as csv_file:
        csv_reader = csv.reader(csv_file)
        
        # Start writing to the NED file
        with open(ned_path, 'w') as ned_file:
            # Add package definition and imports
            ned_file.write("package dtu_networks;\n\n")
            ned_file.write("import inet.networks.base.TsnNetworkBase;\n")
            ned_file.write("import inet.node.ethernet.Eth1G;\n")
            ned_file.write("import inet.node.tsn.TsnDevice;\n")
            ned_file.write("import inet.node.tsn.TsnSwitch;\n\n")
            
            # Initialize the network definition
            ned_file.write("network GeneratedNetwork extends TsnNetworkBase {\n")
            ned_file.write("    submodules:\n")
            
            # To hold the submodule definitions and connections
            submodules = []
            connections = []

            for row in csv_reader:
                # Process device definitions
                if row[0] in ["SW", "ES"] and len(row) >= 3:
                    device_type, device_name, num_ports = row[0], row[1], row[2]

                    # Create submodule entry based on device type
                    if device_type == "SW":  # Switch
                        submodules.append(f"        {device_name}: TsnSwitch {{\n")
                        submodules.append(f"            gates: {switch_gate_name}[{num_ports}];\n")
                        submodules.append("        }\n")
                    elif device_type == "ES":  # End System
                        submodules.append(f"        {device_name}: TsnDevice {{\n")
                        submodules.append(f"            gates: {device_gate_name}[{num_ports}];\n")
                        submodules.append("        }\n")

                # Process link definitions
                elif row[0] == "LINK" and len(row) >= 6:
                    # Extract link attributes
                    link_id, source_device, source_port = row[1], row[2], row[3]
                    destination_device, destination_port = row[4], row[5]
                    
                    # Define the connection using source and destination devices and ports
                    connections.append(
                        f"        {source_device}.{device_gate_name}[{source_port}] <--> Eth1G <--> {destination_device}.{device_gate_name}[{destination_port}];\n"
                    )

            # Write the submodules section to the NED file
            ned_file.writelines(submodules)

            # Write connections section
            ned_file.write("    connections:\n")
            ned_file.writelines(connections)
            ned_file.write("}\n")

    print(f"NED file generated at: {ned_path}")

# Command line argument handling
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert CSV to NED file with 'dtu_networks' package.")
    parser.add_argument("csv_path", type=str, help="Path to the input CSV file.")
    parser.add_argument("ned_path", type=str, help="Path to save the output NED file.")
    args = parser.parse_args()
    
    generate_ned_from_csv(args.csv_path, args.ned_path)

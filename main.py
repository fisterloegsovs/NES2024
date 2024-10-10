from flow_simulation import simulate_flows
from output_handling import write_output

if __name__ == "__main__":
    flows = [
        # TODO: Define your flows here
    ]
    runtime, mean_delay, max_delay, delays = simulate_flows(flows, num_hops=5)
    write_output(runtime, mean_delay, max_delay, delays)

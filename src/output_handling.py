# output_handling.py
def write_output(runtime, mean_delay, max_delay, delays):
    with open('output.txt', 'w') as f:
        f.write(f"Runtime (seconds): {runtime}\n")
        f.write(f"Mean E2E delay (seconds): {mean_delay}\n")
        f.write(f"Maximum E2E delay (seconds) per flow: {max_delay}\n")
        f.write("E2E delay per flow:\n")
        for i, delay in enumerate(delays):
            f.write(f"Flow {i+1}: {delay} seconds\n")

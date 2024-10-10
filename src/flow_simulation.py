from delay_calculations import calculate_dPQ_TX, calculate_dTX_DQ, calculate_dDQ_SO
import time

def calculate_per_hop_delay(flow, link_rate):
    dPQ_TX = calculate_dPQ_TX(flow['bH'], flow['bC'], flow['lL'], link_rate, flow['rH'])
    dTX_DQ = calculate_dTX_DQ(flow['lf'], link_rate)
    dDQ_SO = calculate_dDQ_SO(flow['bH'], flow['bC'], flow['lf'], flow['lf'], flow['lL'], link_rate, flow['rH'])
    return dPQ_TX + dTX_DQ + dDQ_SO

def simulate_flows(flows, num_hops):
    link_rate = 1e9  # 1 Gbps
    delays = []
    start_time = time.time()
    
    for flow in flows:
        e2e_delay = 0
        for _ in range(num_hops):
            e2e_delay += calculate_per_hop_delay(flow, link_rate)
        delays.append(e2e_delay)
    
    runtime = time.time() - start_time
    mean_delay = sum(delays) / len(delays) if delays else 0
    max_delay = max(delays) if delays else 0
    return runtime, mean_delay, max_delay, delays

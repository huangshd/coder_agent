#!/usr/bin/env python3
"""
Parse Coder Agent benchmark results
Similar to figure19/parse_vllm_time.py but adapted for agent workloads
"""

import os
import re
import json
from pathlib import Path


def parse_agent_logs():
    """Parse agent benchmark logs for timing information"""
    results = {
        'total_requests': 0,
        'successful_requests': 0,
        'latencies': [],
        'ttfts': [],
        'tpots': []
    }

    # Try to read from coder_benchmark.log
    log_file = "coder_benchmark.log"
    if os.path.exists(log_file):
        with open(log_file, 'r') as f:
            content = f.read()

            # Extract metrics from log
            total_match = re.search(r'Total\s+requests:\s+(\d+)', content)
            if total_match:
                results['total_requests'] = int(total_match.group(1))

            latency_pattern = r'latency[:\s=]+(\d+\.?\d*)\s*ms'
            for match in re.finditer(latency_pattern, content, re.IGNORECASE):
                results['latencies'].append(float(match.group(1)))

    return results


def parse_json_results(json_path):
    """Parse JSON results file"""
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
        return data
    except Exception as e:
        print(f"Warning: Could not parse {json_path}: {e}")
        return None


def parse_worker_logs():
    """Parse vLLM worker logs for FTT and decode times (similar to figure19)"""
    ftt_points = {}
    exit_points = {}

    # Parse worker logs if they exist
    for filename in os.listdir("."):
        if filename.startswith("model_worker") or filename.startswith("worker_"):
            try:
                with open(filename, "r") as file:
                    for line in file:
                        # Look for FTT markers
                        match = re.search(r"hack ftt: (\d+), ([\d\-: ]+)", line)
                        if match:
                            req_no = match.group(1)
                            cur_time = match.group(2)
                            ftt_points[req_no] = cur_time

                with open(filename, "r") as file:
                    for line in file:
                        # Look for exit markers
                        match = re.search(r"hack request exit: (\d+), (\d+)", line)
                        if match:
                            req_no = match.group(1)
                            cur_time = match.group(2)
                            exit_points[req_no] = cur_time
            except Exception as e:
                print(f"Warning: Could not parse {filename}: {e}")

    return ftt_points, exit_points


def main():
    print("\n" + "="*60)
    print("CODER AGENT BENCHMARK RESULTS PARSER")
    print("="*60)

    # Find the latest results file
    results_dir = Path("./results")
    if results_dir.exists():
        result_files = sorted(results_dir.glob("coder_results*.json"))
        if result_files:
            latest_result = result_files[-1]
            print(f"\nParsing: {latest_result}")

            data = parse_json_results(latest_result)
            if data:
                print("\n--- SUMMARY ---")
                summary = data.get('summary', {})
                print(f"Total Requests:    {summary.get('total_requests', 'N/A')}")
                print(f"Successful:        {summary.get('successful_requests', 'N/A')}")
                print(f"Total Time:        {summary.get('total_time_seconds', 'N/A'):.2f}s")
                print(f"Throughput:        {summary.get('throughput_req_per_sec', 'N/A'):.2f} req/s")

                print("\n--- LATENCY METRICS ---")
                latency = data.get('latency_metrics', {})
                print(f"Avg Latency:       {latency.get('avg_latency_ms', 'N/A'):.2f} ms")
                print(f"P50 Latency:       {latency.get('p50_latency_ms', 'N/A'):.2f} ms")
                print(f"P99 Latency:       {latency.get('p99_latency_ms', 'N/A'):.2f} ms")

                print("\n--- TTFT METRICS ---")
                ttft = data.get('ttft_metrics', {})
                if ttft.get('avg_ttft_ms'):
                    print(f"Avg TTFT:          {ttft.get('avg_ttft_ms', 'N/A'):.2f} ms")
                    print(f"Min TTFT:          {ttft.get('min_ttft_ms', 'N/A'):.2f} ms")
                    print(f"Max TTFT:          {ttft.get('max_ttft_ms', 'N/A'):.2f} ms")
                else:
                    print("TTFT metrics not available")

                print("\n--- TPOT METRICS ---")
                tpot = data.get('tpot_metrics', {})
                if tpot.get('avg_tpot_ms'):
                    print(f"Avg TPOT:          {tpot.get('avg_tpot_ms', 'N/A'):.2f} ms")
                else:
                    print("TPOT metrics not available")

                # Calculate normalized latency if possible
                if latency.get('avg_latency_ms') and summary.get('total_requests'):
                    # This is a simplified calculation
                    print("\n--- ADDITIONAL METRICS ---")
                    print(f"Avg Request Latency: {latency.get('avg_latency_ms', 0):.2f} ms")

    # Also try to parse worker logs for low-level metrics
    print("\n--- WORKER LOG ANALYSIS ---")
    ftt_points, exit_points = parse_worker_logs()

    if ftt_points and exit_points:
        print(f"Found timing data for {len(ftt_points)} requests from worker logs")

        # Calculate decode times
        decode_times = []
        for req_no in ftt_points.keys():
            if req_no in exit_points:
                try:
                    gen_latency = (int(exit_points[req_no]) - int(ftt_points[req_no])) / 1e6
                    decode_times.append(gen_latency)
                except:
                    pass

        if decode_times:
            avg_decode = sum(decode_times) / len(decode_times)
            print(f"Avg Decode Time:   {avg_decode:.2f} ms")
    else:
        print("No worker timing data found (requires VLLM_REQ_TRACK=1)")

    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    main()
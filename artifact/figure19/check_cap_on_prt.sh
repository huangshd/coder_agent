#!/bin/sh

# Test threads_capacity sensitivity from 10 to 256 in 10 steps
# Capacity values: 10, 37, 64, 91, 118, 145, 172, 199, 226, 256

rm result_capacity_test.txt
touch result_capacity_test.txt

# Define capacity values (10 steps from 10 to 256)
capacities=(10 20 30 40 50 60 70 80 90 100)

# Backup original engine.json
cp cluster_4_vicuna_7b/engine.json cluster_4_vicuna_7b/engine.json.backup

echo "Starting threads_capacity sensitivity test..." | tee -a result_capacity_test.txt
echo "Testing capacities: ${capacities[@]}" | tee -a result_capacity_test.txt
echo "================================================" | tee -a result_capacity_test.txt

for cap in "${capacities[@]}"
do
    echo ""
    echo "========================================" | tee -a result_capacity_test.txt
    echo "Testing threads_capacity = $cap" | tee -a result_capacity_test.txt
    echo "========================================" | tee -a result_capacity_test.txt

    # Modify engine.json with new threads_capacity value
    sed -i.tmp "s/\"threads_capacity\": [0-9]\+/\"threads_capacity\": $cap/" cluster_4_vicuna_7b/engine.json

    # Verify the change
    echo "Current threads_capacity:" | tee -a result_capacity_test.txt
    grep "threads_capacity" cluster_4_vicuna_7b/engine.json | tee -a result_capacity_test.txt

    # Clean up old logs
    rm -rf checklog
    # rm *.log -rf

    pwd=$PWD
    log_path=$pwd/checklog/

    echo "Log path: $log_path"

    # Launch cluster
    cd cluster_4_vicuna_7b
    bash launch.sh $log_path os.log engine1.log engine2.log

    # Run benchmark
    cd ..

    echo "Running benchmark for threads_capacity=$cap..." | tee -a result_capacity_test.txt
    python3 start_benchmark_parrot.py &> $log_path/client.log
    sleep 10

    # Parse results and append to result file
    echo "Results for threads_capacity=$cap:" >> result_capacity_test.txt
    python3 parse_parrot_time.py >> result_capacity_test.txt
    echo "" >> result_capacity_test.txt

    # Kill cluster
    bash ../../scripts/kill_all_servers.sh

    # Wait a bit before next iteration to ensure clean shutdown
    sleep 5
done

# Restore original engine.json
echo "Restoring original engine.json..."
mv cluster_4_vicuna_7b/engine.json.backup cluster_4_vicuna_7b/engine.json

# Clean up temporary files
rm -f cluster_4_vicuna_7b/engine.json.tmp

echo ""
echo "================================================" | tee -a result_capacity_test.txt
echo "Test completed! Results saved to result_capacity_test.txt" | tee -a result_capacity_test.txt
echo "================================================" | tee -a result_capacity_test.txt

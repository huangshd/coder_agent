from multiprocessing import Process, Barrier
import os
import time


def start_chat_benchmark(barrier: Barrier, requests_num: int, request_rate: float):
    barrier.wait()
    os.system(
        f"""python3 -u benchmark_chat_ttft_vllm.py \
        --num-prompts {requests_num} \
        --tokenizer hf-internal-testing/llama-tokenizer \
        --dataset ../workloads/sharegpt/ShareGPT_V3_unfiltered_cleaned_split.json \
        --request-rate {request_rate} \
        > vllm_chat.log 2>&1"""
    )


def start_mr_benchmark(barrier: Barrier, app_num: int, app_rate: float):
    barrier.wait()

    # Chat needs some time to load ShareGPT
    time.sleep(15)

    os.system(
        f"""python3 benchmark_mr_serving_vllm.py \
        --num-apps {app_num} \
        --app-rate {app_rate} \
        > vllm_mr.log"""
    )

def start_coding_benchmark(barrier: Barrier, app_num: int, app_rate: float):
    print("等待所有进程就绪...")
    # 等待所有进程/线程到达屏障点
    barrier.wait()
    os.system(f"""python benchmarks/benchmark_coder.py \
                --num-apps {app_num} \
                --request-rate {app_rate} \
                --prompts-file test_prompts.txt \
                --seed 42 """
    )
        



if __name__ == "__main__":
    barrier = Barrier(1)
    #METAGPT_DATASET_PATH = "../workloads/metagpt/log_3_round.jsonl"
    #chat_proc = Process(target=start_chat_benchmark, args=(barrier, 40, 1))
    #mr_proc = Process(target=start_mr_benchmark, args=(barrier, 9, 999))
    coding_proc = Process(target=start_coding_benchmark, args=(barrier, 3, 10))

    #chat_proc.start()
    #mr_proc.start()
    coding_proc.start()

    coding_proc.join()

    #mr_proc.join()
    #chat_proc.join()

#!/bin/bash

# 定义一个清理函数，用于接收停止信号
# cleanup() {
#     echo "接收到停止信号 (SIGTERM/SIGINT)，正在关闭服务器..."
    
#     # 停止两个后台进程
#     # 'kill' 会发送 SIGTERM 信号给子进程
#     if [ -n "$core_pid" ]; then
#         kill "$core_pid"
#     fi
#     if [ -n "$engine_pid" ]; then
#         kill "$engine_pid"
#     fi

#     # 等待子进程完全退出
#     wait
#     echo "所有服务已停止。"
# }


# 设置陷阱 (trap)，捕获 SIGINT (Ctrl+C) 和 SIGTERM (docker stop)
# 当捕获到这些信号时，执行 cleanup 函数
# trap cleanup SIGINT SIGTERM

python3 -m parrot.os.http_server \
    --config_path os.json \
    --log_dir log/ \
    --log_filename core_1_vicuna_7b.log \
    --release_mode &
core_pid=$!
sleep 1

python3 -m parrot.engine.http_server \
    --config_path engine.json \
    --log_dir log/ \
    --log_filename engine_1_vicuna_7b.log \
    --port 9001 \
    --engine_name engine_server1 \
    --release_mode \
    --device cuda &

engine_pid=$!
sleep 30

echo "Successfully launched Parrot runtime system."

# 3. 等待进程
# 这是最关键的一步：
# 'wait -n' 会等待 *任意一个* 后台子进程退出。
# 一旦 core_pid 或 engine_pid 之一（因为崩溃或正常退出）停止，'wait -n' 就会返回。
# wait -n

# 如果脚本执行到这里，说明两个服务器中的一个已经停止了（可能是崩溃了）。
# 我们调用 cleanup 来停止另一个，并让容器干净地退出。
# echo "检测到有服务已停止，开始关闭所有服务..."
# cleanup
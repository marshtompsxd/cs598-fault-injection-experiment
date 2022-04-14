import argparse
import json
import os
import subprocess
import threading
import time

import redis


def parse_opt():
    parser = argparse.ArgumentParser()
    parser.add_argument("--iters", type=int, default=1, help="number of iterations")
    parser.add_argument(
        "--workload",
        type=str,
        default="workload10000",
        help="workload path",
    )
    parser.add_argument(
        "--target-throughput",
        type=str,
        default="1000,2000,3000,4000,5000",
        help="target throughput",
    )
    parser.add_argument(
        "--config", type=str, default="config.json", help="injection config path"
    )
    parser.add_argument(
        "--fault-type",
        type=str,
        default="no",
        help="no/crash/cpuslow/memcontention",
    )
    parser.add_argument(
        "--fault-target", type=str, default="follower", help="leader/follower"
    )
    # parser.add_argument(
    #     "--runoutput", type=str, default="runoutput", help="results output path"
    # )
    # parser.add_argument(
    #     "--loadoutput", type=str, default="loadoutput", help="results output path"
    # )
    parser.add_argument(
        "--request-port", type=int, default=5001, help="results output path"
    )
    parser.add_argument(
        "--fault-snooze",
        type=int,
        default=0,
        help="After how long from the start of sending reqs should the fault be injected",
    )
    opt = parser.parse_args()
    return opt


def run_cmd(cmd, stdout=None):
    print(cmd)
    subprocess.run(cmd, shell=True, check=True, stdout=stdout)


def cleanup(config):
    run_cmd("rm -rf raftlog*.db")
    run_cmd("rm -rf raftlog*.db.idx")
    run_cmd("rm -rf raftlog*.db.meta")
    run_cmd("rm -rf *.rdb")


def start_redis(config):
    server_configs = config["servers"]
    leader_port = None
    for idx, server_config in enumerate(server_configs):
        port = server_config["port"]
        dbfilename = server_config["dbfilename"]
        raftlogfilename = server_config["raftlogfilename"]
        cpu = server_config["cpu"]
        is_leader = idx == 0
        run_cmd(
            "taskset -ac {} redis-server --port {} --dbfilename {} --daemonize yes --loadmodule redisraft/redisraft.so raft-log-filename {} addr localhost:{}".format(
                cpu, port, dbfilename, raftlogfilename, port
            )
        )
        if is_leader:
            run_cmd("redis-cli -p {} raft.cluster init".format(port))
            leader_port = port
        else:
            run_cmd(
                "redis-cli -p {} raft.cluster join localhost:{}".format(
                    port, leader_port
                )
            )


def stop_redis(config):
    run_cmd("pkill redis")


def get_redis_pids(config):
    pids = []
    server_configs = config["servers"]
    for server_config in server_configs:
        port = server_config["port"]
        r = redis.Redis(host="localhost", port=port)
        pids.append(r.info()["process_id"])
    return pids


def benchmark_load(config, opt, throughput):
    client_config = config["client"]
    cpu = client_config["cpu"]
    workload = os.path.join("..", opt.workload)
    req_port = opt.request_port
    out_file = "load-{}-{}-{}".format(throughput, opt.fault_type, opt.fault_target)
    run_cmd(
        'cd YCSB; taskset -ac {} ./bin/ycsb load redis -s -P {} -threads 32 -p "redis.host=localhost" -p "redis.port={}"'.format(
            cpu, workload, req_port
        ),
        stdout=open(out_file, "w"),
    )


def benchmark_run(config, opt, throughput):
    client_config = config["client"]
    cpu = client_config["cpu"]
    workload = os.path.join("..", opt.workload)
    req_port = opt.request_port
    if throughput != "":
        target_cmd = "-target {}".format(throughput)
    out_file = "run-{}-{}-{}".format(throughput, opt.fault_type, opt.fault_target)
    run_cmd(
        'cd YCSB; taskset -ac {} ./bin/ycsb run redis -s -P {} -threads 32 {} -p "redis.host=localhost" -p "redis.port={}"'.format(
            cpu, workload, target_cmd, req_port
        ),
        stdout=open(out_file, "w"),
    )


def kill_process(pids):
    for pid in pids:
        run_cmd("kill -9 {}".format(pid))


def cpu_slow(slow_pids):
    quota = 50000
    period = 1000000
    cgroup_name = "/sys/fs/cgroup/cpu/db"
    run_cmd("sudo mkdir {}".format(cgroup_name))
    run_cmd("sudo echo {} > {}/cpu.cfs_quota_us".format(quota, cgroup_name))
    run_cmd("sudo echo {} > {}/cpu.cfs_period_us".format(period, cgroup_name))
    for slow_pid in slow_pids:
        run_cmd("echo {} > {}/cgroup.procs".format(slow_pid, cgroup_name))


def memory_contention(slow_pids):
    cgroup_name = "/sys/fs/cgroup/memory/db"
    run_cmd("sudo mkdir {}".format(cgroup_name))
    run_cmd(
        "sudo echo {} > {}/memory.limit_in_bytes".format(5 * 1024 * 1024, cgroup_name)
    )
    for slow_pid in slow_pids:
        run_cmd("sudo echo {} > {}/cgroup.procs".format(slow_pid, cgroup_name))


def fault_injection(config, opt, pids):
    if opt.fault_type == "no":
        return
    else:
        if opt.fault_snooze > 0:
            time.sleep(opt.fault_snooze)
        faulty_pid = pids[0] if opt.fault_target == "leader" else pids[1]
        print(
            "fault injection {} to {}({})".format(
                opt.fault_type, opt.fault_target, faulty_pid
            )
        )
        if opt.fault_type == "crash":
            kill_process([faulty_pid])
        elif opt.fault_type == "cpuslow":
            cpu_slow([faulty_pid])
        elif opt.fault_type == "memcontention":
            memory_contention([faulty_pid])
        else:
            return


def run(opt, throughput):
    config = None
    with open(opt.config) as f:
        config = json.load(f)
    cleanup(config)
    start_redis(config)
    pids = get_redis_pids(config)
    print(pids)
    benchmark_load(config, opt, throughput)
    fault_injection_thread = threading.Thread(
        target=fault_injection,
        args=(
            config,
            opt,
            pids,
        ),
    )
    fault_injection_thread.start()
    benchmark_run(config, opt, throughput)
    fault_injection_thread.join()
    stop_redis(config)


if __name__ == "__main__":
    opt = parse_opt()
    for throughput in opt.target_throughput.split(","):
        run(opt, throughput)

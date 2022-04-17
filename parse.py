import glob
import os

map = {}
ycsb_files = glob.glob("runoutput/*")
for ycsb_file in ycsb_files:
    file_name = os.path.basename(ycsb_file)
    tokens = file_name.split("-")
    fault_type = tokens[-2] + "-" + tokens[-1]
    if fault_type not in map:
        map[fault_type] = []
    perf = {"throughput": 0.0, "read_latency": 0.0, "update_latency": 0.0}
    for line in open(ycsb_file).readlines():
        if "[OVERALL], Throughput(ops/sec)," in line:
            perf["throughput"] = float(line.strip().split(" ")[-1])
        elif "[READ], AverageLatency(us)," in line:
            perf["read_latency"] = float(line.strip().split(" ")[-1])
        elif "[UPDATE], AverageLatency(us)," in line:
            perf["update_latency"] = float(line.strip().split(" ")[-1])
    map[fault_type].append(perf)

for fault_type in map:
    map[fault_type] = sorted(map[fault_type], key=lambda i: i["throughput"])

for fault_type in map:
    str = fault_type
    for item in map[fault_type]:
        str += "\t({},{})".format(int(item["throughput"]), int(item["update_latency"]))
    print(str)

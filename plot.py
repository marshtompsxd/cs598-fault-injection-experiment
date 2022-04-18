from cProfile import label
import matplotlib.pyplot as plt
import json

map = json.load(open("result.json"))
to_plots = [
    "no-follower",
    "crash-follower",
    "cpuslow-leader",
    "cpuslow-follower",
    "memcontention-leader",
    "memcontention-follower",
    "cpuslow-leader_50000",
    "cpuslow-leader_200000",
    "memcontention-leader_512",
]
patterns = [".", "v", "o", "*", "+", "^", "<", ">", "s"]
labels = [
    "fault free",
    "follower crash",
    "leader cpu slow",
    "follower cpu slow",
    "leader mem contention",
    "follower mem contention",
]

cmp_cpu_labels = {
    "no-follower": "fault free",
    "cpuslow-leader": "leader cpu slow (100000)",
    "cpuslow-leader_50000": "leader cpu slow (50000)",
    "cpuslow-leader_200000": "leader cpu slow (200000)",
}

cmp_mem_labels = {
    "no-follower": "fault free",
    "memcontention-leader": "leader mem contention (256)",
    "memcontention-leader_512": "leader mem contention (512)",
}

plt.rcParams["figure.figsize"] = (12, 12)
fig, axs = plt.subplots(3, 2)
for i, to_plot in enumerate(to_plots):
    perfs = map[to_plot]
    x = []
    y = []
    for perf in perfs:
        x.append(perf["throughput"])
        y.append(perf["update_latency"])
    if i == 0:
        axs[0, 0].plot(x, y, marker=patterns[i], linestyle="-", label=labels[i])
        axs[0, 0].legend()
    if (i == 0 or i % 2 == 1) and i < 6:
        axs[0, 1].plot(x, y, marker=patterns[i], linestyle="-", label=labels[i])
        axs[0, 1].legend()
    if (i == 0 or i % 2 == 0) and i < 6:
        axs[1, 0].plot(x, y, marker=patterns[i], linestyle="-", label=labels[i])
        axs[1, 0].legend()
    if to_plot in cmp_cpu_labels:
        axs[1, 1].plot(
            x, y, marker=patterns[i], linestyle="-", label=cmp_cpu_labels[to_plot]
        )
        axs[1, 1].legend()
    if to_plot in cmp_mem_labels:
        axs[2, 0].plot(
            x, y, marker=patterns[i], linestyle="-", label=cmp_mem_labels[to_plot]
        )
        axs[2, 0].legend()

axs[0, 0].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")
axs[0, 1].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")
axs[1, 0].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")
axs[1, 1].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")
axs[2, 0].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")
axs[2, 1].set(xlabel="Throughput (ops/sec)", ylabel="Average Latency (us)")

plt.savefig("fig.pdf")

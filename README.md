# CXLMemSim and MEMU

# CXLMemSim
The CXL.mem simulator uses target latency for simulating CPU perspective, taking ROB and different cacheline states into account from the application level. It supports both standalone operation and client-server mode for flexible testing scenarios.

## Quick Start

### Building the Project
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Running in Server Mode

The server supports various configuration options:

```bash
./cxlmemsim_server [OPTIONS]

Options:
  --default_latency N    Base memory access latency in ns (default: 100)
  --interleave_size N   Memory interleaving size in bytes (default: 256)
  --capacity N          Total CXL memory capacity in MB (default: 256)
  --port N             Server port number (default: 9999)
  --topology FILE      Topology configuration file (default: topology.txt)
  --comm-mode MODE     Communication mode: tcp or shm (default: tcp)
  -v, --verbose N      Verbosity level 0-3 (default: 2)
  --backing-file FILE  Optional file to back CXL memory
```

Example server setup:
```bash
# Create a topology file with two memory expanders
cat > topology.txt << EOL
# Format: node_id read_bandwidth write_bandwidth read_latency write_latency capacity_mb
1 4000 4000 85 85 256
2 4000 4000 100 100 256
EOL

# Run server with configuration
SPDLOG_LEVEL=debug ./cxlmemsim_server --default_latency 85 --interleave_size 256 --capacity 512 --port 9999 --topology topology.txt
```

### Client Examples

1. Simple Memory Test (C client):
```bash
cd microbench
gcc -o simple_client simple_client.c
./simple_client  # Basic read/write tests
```

2. Python Trace Replay:
```bash
cd microbench
./inference_replay.py ../artifact/llama/llama-cli/cxlmemsim.txt
```

3. Available Microbenchmarks:
- `ld_simple.cpp`: Memory load testing
- `bw.cpp`: Bandwidth measurement
- `ptr-chasing.cpp`: Latency measurement
- `st.cpp`: Store operation testing

### Inference and Workload Replay

The project includes several pre-configured workloads and traces:

1. Available Workloads (`workloads/`):
   - LLaMA Inference (`llama.cpp/`)
   - Memory Bandwidth (`MLC/`)
   - Graph Processing (`gapbs/`)
   - Molecular Dynamics (`gromacs/`)

2. Pre-recorded Traces (`artifact/llama/llama-cli/`):
   - Base configuration: `cxlmemsim.txt`
   - Policy variations:
     - Frequency-based: `cxlmemsim_none_frequency_none_none.txt`
     - Locality-based: `cxlmemsim_none_locality_none_none.txt`
     - Load balancing: `cxlmemsim_none_loadbalance_none_none.txt`

### Running in Standalone Mode
For standalone operation, use the following command format:
```bash
SPDLOG_LEVEL=debug ./CXLMemSim [OPTIONS]

Options:
  -t PATH     Target executable path
  -i N        Epoch interval in milliseconds
  -c N,N      CPU core IDs (format: run_core,monitor_core)
  -d N        DRAM latency in ns (default: 85)
  -b N,N      Bandwidth (read,write) in GB/s
  -l N,N      Latency (read,write) in ns
  -c N,N      Memory capacity in MB (local,remote)
  -w N,N,...  Bandwidth weights for heuristics
  -o STR      Topology in Newick format
```

Example standalone run:
```bash
SPDLOG_LEVEL=debug ./CXLMemSim -t ./microbench/ld -i 5 -c 0,2 -d 85 -c 100,100 \
    -w 85.5,86.5,87.5,85.5,86.5,87.5,88 -o "(1,(2,3))"
```

The topology option (-o) uses Newick tree syntax, for example "(1,(2,3))" represents:
```
            1
          /
0 - local
          \
                   2
         switch  / 
                 \ 
                  3
```

### Memory Management Policies

CXLMemSim supports several memory management policies:

1. Allocation:
   - Interleaved
   - NUMA-aware

2. Migration:
   - Frequency-based
   - Heat-aware
   - Load balancing
   - Locality-based

3. Paging:
   - Huge pages
   - Page table aware

4. Caching:
   - FIFO
   - Frequency-based

To experiment with different policies, use the corresponding trace files in `artifact/llama/llama-cli/` or modify server configuration.

## Cite
```bash
@article{yangyarch23,
  title={CXLMemSim: A pure software simulated CXL.mem for performance characterization},
  author={Yiwei Yang, Pooneh Safayenikoo, Jiacheng Ma, Tanvir Ahmed Khan, Andrew Quinn},
  journal={arXiv preprint arXiv:2303.06153},
  booktitle={The fifth Young Architect Workshop (YArch'23)},
  year={2023}
}
```

# MEMU

Compute Express Link (CXL) 3.0 introduces powerful memory pooling and promises to transform datacenter architectures. However, the lack of available CXL 3.0 hardware and the complexity of multi-host configurations pose significant challenges to the community. This paper presents MEMU, a comprehensive emulation framework that enables full CXL 3.0 functionality, including multi-host memory sharing and pooling support. MEMU provides emulation of CXL 3.0 features—such as fabric management, dynamic memory allocation, and coherent memory sharing across multiple hosts—in advance of real hardware availability. An evaluation of MEMU shows that it achieves performance within about 3x of projected native CXL 3.0 speeds having complete compatibility with existing CXL software stacks. We demonstrate the utility of MEMU through a case study on Genomics Pipeline, observing up to a 15% improvement in application performance compared to traditional RDMA-based approaches. MEMU is open-source and publicly available, aiming to accelerate CXL 3.0 research and development.

```bash
sudo ip link add br0 type bridge
sudo ip link set br0 up
sudo ip addr add 192.168.100.1/24 dev br0
for i in 0; do
    sudo ip tuntap add tap$i mode tap
    sudo ip link set tap$i up
    sudo ip link set tap$i master br0
done
mkdir build
cd build
wget https://asplos.dev/about/qemu.img
wget https://asplos.dev/about/bzImage
cp qemu.img qemu1.img
../qemu_integration/launch_qemu_cxl1.sh
# in qemu
vi /usr/local/bin/*.sh
# change 192.168.100.10 to 11
vi /etc/hostname
# change node0 to node1
exit
# out of qemu
../qemu_integration/launch_qemu_cxl.sh &
../qemu_integration/launch_qemu_cxl1.sh &
```


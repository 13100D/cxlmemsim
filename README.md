# CXLMemSim and MEMU

# CXLMemSim
The CXL.mem simulator provides a server-client architecture for simulating CXL Type 3 memory devices, with support for different memory management policies, workload replay, and performance analysis.

## Quick Start

### Building the Project
```bash
mkdir build && cd build
cmake ..
make -j$(nproc)
```

### Running the Server

The CXL memory simulator server (`cxlmemsim_server`) supports the following options:

```bash
Usage: cxlmemsim_server [OPTIONS]

Options:
  -h, --help            Show help message
  -v, --verbose N       Verbose level (default: 2)
  --default_latency N   Base memory access latency in ns (default: 100)
  --interleave_size N   Memory interleaving size in bytes (default: 256)
  --capacity N          CXL expander capacity in MB (default: 256)
  -p, --port N         Server port (default: 9999)
  -t, --topology FILE  Topology configuration file (default: topology.txt)
  --backing-file FILE  Optional backing file for shared memory
  --comm-mode MODE     Communication mode: tcp or shm (default: tcp)
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
SPDLOG_LEVEL=debug ./cxlmemsim_server --default_latency 85 --interleave_size 256 \
    --capacity 512 --port 9999 --topology topology.txt
```

### Using the Simulator

#### 1. Basic Memory Tests (C Client)
The simple_client.c provides basic read/write testing:
```bash
cd microbench
gcc -o simple_client simple_client.c
./simple_client  # Performs basic read/write operations
```

#### 2. Microbenchmarks
The `microbench/` directory contains various test programs:
```bash
cd build/microbench
# Load Tests
./ld_simple     # Simple memory load patterns
./ld1 through ./ld256  # Different load sizes
./ld_nt1 through ./ld_nt256  # Non-temporal loads
./ld_serial1 through ./ld_serial256  # Serial loads

# Store Tests
./st1 through ./st256  # Different store sizes
./st_serial1 through ./st_serial256  # Serial stores

# Other Tests
./ptr-chasing   # Memory latency measurement
./bw            # Memory bandwidth test
./cache-miss    # Cache miss behavior
./thread        # Multi-threaded access patterns
```

#### 3. Workload Replay
The project includes several pre-recorded workloads in `artifact/`:

1. LLaMA Inference Traces (`artifact/llama/llama-cli/`):
```bash
# Different policy configurations:
cxlmemsim.txt                           # Base configuration
cxlmemsim_none_frequency_none_none.txt  # Frequency-based policy
cxlmemsim_none_locality_none_none.txt   # Locality-based policy
cxlmemsim_none_loadbalance_none_none.txt # Load balancing policy
```

2. GROMACS Molecular Dynamics:
```bash
cd artifact
./run_gromacs.sh  # Runs molecular dynamics simulation
```

3. Memory Latency Calibration (MLC):
```bash
cd artifact/mlc
# Provides latency measurements for:
mlc-alderlake.txt
mlc-lunarlake.txt
mlc-sapphirerapids.txt
```

#### 4. Trace Replay Tool
The Python trace replay tool can be used to replay any memory access trace:
```bash
cd microbench
./inference_replay.py <trace_file>

# Example with LLaMA trace:
./inference_replay.py ../artifact/llama/llama-cli/cxlmemsim.txt
```

Trace file format:
```
# timestamp addr size op_type
# op_type: 0=read, 1=write
1234567890 0x1000 64 0  # Example read operation
1234567891 0x2000 64 1  # Example write operation
```

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


#!/usr/bin/env python3
import socket
import struct
import time
import numpy as np
from typing import List, Tuple

class CXLMemSimClient:
    def __init__(self, host='127.0.0.1', port=9999):
        """Initialize connection to CXL Memory Simulator."""
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"Connected to CXL Memory Server at {host}:{port}")

    def __del__(self):
        """Close connection on cleanup."""
        self.sock.close()

    def _send_request(self, op_type: int, addr: int, size: int, data: bytes = None) -> Tuple[int, int, bytes]:
        """Send a request to the server and get response.
        
        Args:
            op_type: 0 for READ, 1 for WRITE
            addr: Memory address
            size: Size in bytes (max 64)
            data: Data to write (for WRITE operations)
        
        Returns:
            Tuple of (status, latency_ns, data)
        """
        # Create request structure (matches C struct)
        req = struct.pack('=BxxxQLQL', 
                         op_type,      # uint8_t op_type
                         addr,         # uint64_t addr
                         size,         # uint64_t size
                         0)           # uint64_t timestamp
        
        if op_type == 1:  # WRITE
            req += data.ljust(64, b'\0')  # Pad to 64 bytes
        else:
            req += b'\0' * 64  # 64 bytes of padding for READ

        # Send request
        self.sock.sendall(req)

        # Receive response
        resp = self.sock.recv(struct.calcsize('=BxxxQL64s'))
        status, latency, data = struct.unpack('=BxxxQL64s', resp)
        
        return status, latency, data[:size]

    def read(self, addr: int, size: int = 64) -> Tuple[bytes, int]:
        """Read from CXL memory.
        
        Args:
            addr: Memory address to read from
            size: Number of bytes to read (max 64)
        
        Returns:
            Tuple of (data, latency_ns)
        """
        status, latency, data = self._send_request(0, addr, size)
        if status != 0:
            raise RuntimeError(f"Read failed with status {status}")
        return data, latency

    def write(self, addr: int, data: bytes) -> int:
        """Write to CXL memory.
        
        Args:
            addr: Memory address to write to
            data: Bytes to write (max 64 bytes)
            
        Returns:
            Latency in nanoseconds
        """
        status, latency, _ = self._send_request(1, addr, len(data), data)
        if status != 0:
            raise RuntimeError(f"Write failed with status {status}")
        return latency

    def measure_latency(self, num_ops=1000, size=64) -> Tuple[float, float, float]:
        """Measure read latency statistics.
        
        Args:
            num_ops: Number of operations to perform
            size: Size of each read in bytes
            
        Returns:
            Tuple of (mean_latency_ns, min_latency_ns, max_latency_ns)
        """
        latencies = []
        for i in range(num_ops):
            _, latency = self.read(i * size, size)
            latencies.append(latency)
        
        return np.mean(latencies), np.min(latencies), np.max(latencies)

    def test_bandwidth(self, total_size=1024*1024, chunk_size=64) -> Tuple[float, float]:
        """Measure read and write bandwidth.
        
        Args:
            total_size: Total amount of data to transfer
            chunk_size: Size of each operation
            
        Returns:
            Tuple of (read_bandwidth_gbps, write_bandwidth_gbps)
        """
        # Prepare test data
        test_data = bytes([x % 256 for x in range(chunk_size)])
        num_ops = total_size // chunk_size

        # Measure write bandwidth
        start = time.time()
        for i in range(num_ops):
            self.write(i * chunk_size, test_data)
        write_time = time.time() - start
        write_bw = (total_size / write_time) / 1e9  # GB/s

        # Measure read bandwidth
        start = time.time()
        for i in range(num_ops):
            self.read(i * chunk_size, chunk_size)
        read_time = time.time() - start
        read_bw = (total_size / read_time) / 1e9  # GB/s

        return read_bw, write_bw

def main():
    # Create client
    client = CXLMemSimClient()

    # Test 1: Basic read/write
    print("\nTest 1: Basic Read/Write")
    test_data = bytes([x % 256 for x in range(64)])
    write_lat = client.write(0x1000, test_data)
    read_data, read_lat = client.read(0x1000)
    print(f"Write latency: {write_lat} ns")
    print(f"Read latency: {read_lat} ns")
    print(f"Read data matches: {read_data == test_data}")

    # Test 2: Latency Statistics
    print("\nTest 2: Latency Statistics (1000 reads)")
    mean_lat, min_lat, max_lat = client.measure_latency()
    print(f"Mean latency: {mean_lat:.2f} ns")
    print(f"Min latency:  {min_lat:.2f} ns")
    print(f"Max latency:  {max_lat:.2f} ns")

    # Test 3: Bandwidth Test
    print("\nTest 3: Bandwidth Test (1MB transfers)")
    read_bw, write_bw = client.test_bandwidth()
    print(f"Read bandwidth:  {read_bw:.2f} GB/s")
    print(f"Write bandwidth: {write_bw:.2f} GB/s")

if __name__ == '__main__':
    main()

#!/usr/bin/env python3

import socket
import struct
import time
import argparse
from collections import defaultdict
import numpy as np

# Server request/response structures matching C client
class ServerRequest:
    def __init__(self, op_type=0, addr=0, size=64, timestamp=0, data=bytes(64)):
        self.op_type = op_type  # 0=READ, 1=WRITE
        self.addr = addr
        self.size = size
        self.timestamp = timestamp
        self.data = data[:64]  # Ensure 64 bytes
        
    def pack(self):
        return struct.pack('BQQQ64s', 
                         self.op_type,
                         self.addr,
                         self.size,
                         self.timestamp,
                         self.data)

class ServerResponse:
    @classmethod
    def unpack(cls, data):
        status, latency, data = struct.unpack('BQ64s', data)
        return cls(status, latency, data)
        
    def __init__(self, status, latency_ns, data):
        self.status = status
        self.latency_ns = latency_ns
        self.data = data

class CXLSimulator:
    def __init__(self, host='localhost', port=9999):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        print(f"Connected to CXL Memory Server at {host}:{port}")
        
    def send_request(self, req):
        self.sock.sendall(req.pack())
        resp_data = self.sock.recv(73)  # 1 + 8 + 64 bytes
        return ServerResponse.unpack(resp_data)
        
    def read(self, addr, size=64):
        req = ServerRequest(op_type=0, addr=addr, size=size)
        return self.send_request(req)
        
    def write(self, addr, data, size=64):
        req = ServerRequest(op_type=1, addr=addr, size=size, data=data)
        return self.send_request(req)

    def close(self):
        self.sock.close()

def parse_trace_line(line):
    """Parse a trace file line. Format depends on trace type."""
    # Example format: timestamp addr size op_type
    try:
        parts = line.strip().split()
        if len(parts) >= 4:
            timestamp = int(parts[0])
            addr = int(parts[1], 16) if '0x' in parts[1] else int(parts[1])
            size = int(parts[2])
            op_type = 1 if parts[3].lower() in ['w', 'write', '1'] else 0
            return timestamp, addr, size, op_type
    except:
        return None
    return None

def run_trace_replay(trace_file, simulator):
    print(f"\nReplaying trace from {trace_file}")
    
    # Statistics tracking
    stats = {
        'read_latencies': [],
        'write_latencies': [],
        'read_count': 0,
        'write_count': 0,
        'total_bytes': 0
    }
    
    start_time = time.time()
    last_progress = start_time
    line_count = 0
    
    try:
        with open(trace_file, 'r') as f:
            for line in f:
                line_count += 1
                if line_count % 1000 == 0:
                    now = time.time()
                    if now - last_progress >= 5:  # Progress update every 5 seconds
                        print(f"Processed {line_count} operations...")
                        last_progress = now
                
                parsed = parse_trace_line(line)
                if not parsed:
                    continue
                    
                timestamp, addr, size, op_type = parsed
                
                # Align address to 64-byte boundary
                addr = (addr // 64) * 64
                
                try:
                    if op_type == 0:  # Read
                        resp = simulator.read(addr, size)
                        stats['read_latencies'].append(resp.latency_ns)
                        stats['read_count'] += 1
                    else:  # Write
                        resp = simulator.write(addr, bytes(64), size)
                        stats['write_latencies'].append(resp.latency_ns)
                        stats['write_count'] += 1
                    
                    stats['total_bytes'] += size
                    
                except Exception as e:
                    print(f"Error on line {line_count}: {e}")
                    continue
                    
    except KeyboardInterrupt:
        print("\nTrace replay interrupted by user")
    
    duration = time.time() - start_time
    
    # Print statistics
    print("\nTrace Replay Statistics:")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Operations: {line_count} ({line_count/duration:.2f} ops/sec)")
    print(f"Total data: {stats['total_bytes']/1e6:.2f} MB ({stats['total_bytes']/duration/1e6:.2f} MB/sec)")
    print("\nRead operations:")
    if stats['read_latencies']:
        print(f"  Count: {stats['read_count']}")
        print(f"  Average latency: {np.mean(stats['read_latencies']):.2f} ns")
        print(f"  Min latency: {np.min(stats['read_latencies']):.2f} ns")
        print(f"  Max latency: {np.max(stats['read_latencies']):.2f} ns")
    print("\nWrite operations:")
    if stats['write_latencies']:
        print(f"  Count: {stats['write_count']}")
        print(f"  Average latency: {np.mean(stats['write_latencies']):.2f} ns")
        print(f"  Min latency: {np.min(stats['write_latencies']):.2f} ns")
        print(f"  Max latency: {np.max(stats['write_latencies']):.2f} ns")

def main():
    parser = argparse.ArgumentParser(description='CXL Memory Simulator Trace Replay')
    parser.add_argument('trace_file', help='Path to trace file')
    parser.add_argument('--host', default='localhost', help='CXL simulator host')
    parser.add_argument('--port', type=int, default=9999, help='CXL simulator port')
    args = parser.parse_args()
    
    simulator = CXLSimulator(args.host, args.port)
    try:
        run_trace_replay(args.trace_file, simulator)
    finally:
        simulator.close()

if __name__ == '__main__':
    main()

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdint.h>
#include <time.h>

// Matching server's request/response structures
struct ServerRequest {
    uint8_t op_type;      // 0=READ, 1=WRITE
    uint64_t addr;
    uint64_t size;
    uint64_t timestamp;
    uint8_t data[64];     // Cacheline data
};

struct ServerResponse {
    uint8_t status;
    uint64_t latency_ns;
    uint8_t data[64];
};

#define CACHE_LINE_SIZE 64
#define STRIDE 7
#define ARRAY_SIZE (1024 * 1024)  // 1MB of data
#define ITERATIONS 1000

int main(int argc, char *argv[]) {
    int sock = socket(AF_INET, SOCK_STREAM, 0);
    if (sock < 0) {
        perror("socket");
        return 1;
    }

    struct sockaddr_in server_addr = {
        .sin_family = AF_INET,
        .sin_port = htons(9999),
        .sin_addr.s_addr = inet_addr("127.0.0.1")
    };

    if (connect(sock, (struct sockaddr *)&server_addr, sizeof(server_addr)) < 0) {
        perror("connect");
        return 1;
    }

    printf("Connected to CXL Memory Server\n");
    printf("Testing memory latency with pointer chasing pattern:\n");
    printf("- Array size: %d bytes\n", ARRAY_SIZE);
    printf("- Stride: %d cache lines\n", STRIDE);
    printf("- Iterations: %d\n\n", ITERATIONS);

    struct ServerRequest req = {0};
    struct ServerResponse resp = {0};

    // Initialize the memory with stride pattern
    printf("Initializing memory with stride pattern...\n");
    for (uint64_t addr = 0; addr < ARRAY_SIZE; addr += CACHE_LINE_SIZE) {
        req.op_type = 1; // WRITE
        req.addr = addr;
        req.size = CACHE_LINE_SIZE;
        req.timestamp = 0;
        // Fill with stride pattern
        for (int i = 0; i < CACHE_LINE_SIZE; i++) {
            req.data[i] = STRIDE;
        }

        if (send(sock, &req, sizeof(req), 0) != sizeof(req)) {
            perror("send write");
            return 1;
        }

        if (recv(sock, &resp, sizeof(resp), MSG_WAITALL) != sizeof(resp)) {
            perror("recv write response");
            return 1;
        }
    }

    printf("Starting pointer chasing test...\n");
    struct timespec start, end;
    clock_gettime(CLOCK_MONOTONIC, &start);

    uint64_t position = 0;
    uint64_t total_latency = 0;
    int completed_iterations = 0;

    // Main test loop - pointer chasing pattern
    for (int i = 0; i < ITERATIONS; i++) {
        req.op_type = 0; // READ
        req.addr = position;
        req.size = CACHE_LINE_SIZE;
        req.timestamp = 0;

        if (send(sock, &req, sizeof(req), 0) != sizeof(req)) {
            perror("send read");
            break;
        }

        if (recv(sock, &resp, sizeof(resp), MSG_WAITALL) != sizeof(resp)) {
            perror("recv read response");
            break;
        }

        total_latency += resp.latency_ns;
        position += (resp.data[0] * CACHE_LINE_SIZE);
        position &= (ARRAY_SIZE - 1);  // Wrap around within array bounds
        completed_iterations++;
    }

    clock_gettime(CLOCK_MONOTONIC, &end);
    double elapsed = (end.tv_sec - start.tv_sec) + (end.tv_nsec - start.tv_nsec) / 1e9;

    printf("\nResults:\n");
    printf("- Completed iterations: %d\n", completed_iterations);
    printf("- Total time: %.3f seconds\n", elapsed);
    printf("- Average latency: %.2f ns\n", (double)total_latency / completed_iterations);
    printf("- Operations per second: %.2f\n", completed_iterations / elapsed);

    close(sock);
    return 0;
}

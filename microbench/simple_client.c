#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <unistd.h>
#include <stdint.h>

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

    // Test both read and write operations
    struct ServerRequest req = {0};
    struct ServerResponse resp = {0};

    // Test 1: Write to address 0x1000
    printf("\nTest 1: Writing pattern to address 0x1000\n");
    req.op_type = 1; // WRITE
    req.addr = 0x1000;
    req.size = 64;
    req.timestamp = 0;
    for (int i = 0; i < 64; i++) {
        req.data[i] = i;
    }

    if (send(sock, &req, sizeof(req), 0) != sizeof(req)) {
        perror("send write");
        return 1;
    }

    if (recv(sock, &resp, sizeof(resp), MSG_WAITALL) != sizeof(resp)) {
        perror("recv write response");
        return 1;
    }

    printf("Write completed with status %d, latency %lu ns\n", 
           resp.status, resp.latency_ns);

    // Test 2: Read from address 0x1000
    printf("\nTest 2: Reading back from address 0x1000\n");
    req.op_type = 0; // READ
    
    if (send(sock, &req, sizeof(req), 0) != sizeof(req)) {
        perror("send read");
        return 1;
    }

    if (recv(sock, &resp, sizeof(resp), MSG_WAITALL) != sizeof(resp)) {
        perror("recv read response");
        return 1;
    }

    printf("Read completed with status %d, latency %lu ns\n", 
           resp.status, resp.latency_ns);

    printf("Read data: ");
    for (int i = 0; i < 16; i++) { // Print first 16 bytes
        printf("%02x ", resp.data[i]);
    }
    printf("...\n");

    close(sock);
    return 0;
}

## Algorithm Steps

1. Start the TCP server and listen for incoming client connections.
2. Accept client connections and create a separate thread for each client.
3. Recursively scan the client's source directory to identify all files.
4. Calculate the SHA-256 checksum and file size for each file.
5. Send file metadata (filename, relative path, size, and SHA-256 checksum) to the server in JSON format.
6. Acquire a per-file lock and check whether the file exists on the server.
7. Compare SHA-256 checksums and respond with `SEND` if the file is missing or modified, or `SKIP` if unchanged.
8. If `SEND`, transfer the file over TCP in 4 KiB chunks.
9. Receive the file into a temporary file and verify its SHA-256 checksum.
10. Atomically replace the destination file after successful verification.
11. Send a `STORED` acknowledgment and release the file lock.
12. Repeat the process for all files, skipping unchanged files to minimize redundant transmission.
13. Send a `DONE` message and close the client connection after synchronization completes.

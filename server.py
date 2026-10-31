import os
import socket
import tempfile
import threading

from utils import calculate_sha256, send_json, recv_json


HOST = "127.0.0.1"
PORT = 9001
DEST_DIR = "received_files"

BUFFER_SIZE = 4096
file_locks = {}
file_locks_guard = threading.Lock()


def get_file_lock(file_path):
    with file_locks_guard:
        if file_path not in file_locks:
            file_locks[file_path] = threading.Lock()

        return file_locks[file_path]

def receive_file(sock, destination_path, file_size, expected_hash):
    os.makedirs(
        os.path.dirname(destination_path),
        exist_ok=True
    )

    bytes_received = 0
    temp_path = None

    try:
        # Write to a temporary file first
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=os.path.dirname(destination_path),
            prefix=".sync-",
            delete=False
        ) as temp_file:

            temp_path = temp_file.name

            while bytes_received < file_size:
                remaining = file_size - bytes_received

                chunk = sock.recv(
                    min(BUFFER_SIZE, remaining)
                )

                if not chunk:
                    raise ConnectionError(
                        "Connection closed during file transfer"
                    )

                temp_file.write(chunk)
                bytes_received += len(chunk)

        # Verify the received file's integrity
        actual_hash = calculate_sha256(temp_path)

        if actual_hash != expected_hash:
            raise ValueError(
                "SHA-256 verification failed"
            )

        # Replace the destination only after verification
        os.replace(temp_path, destination_path)
        temp_path = None

        return bytes_received

    finally:
        if temp_path is not None and os.path.exists(temp_path):
            os.remove(temp_path)

def handle_client(conn):
    while True:
        metadata = recv_json(conn)

        if metadata["type"] == "DONE":
            print("[INFO] Client finished scanning")
            break

        if metadata["type"] != "FILE":
            raise ValueError("Unknown message type")

        filename = metadata["filename"]
        client_hash = metadata["sha256"]
        file_size = metadata["size"]

        if (
            not isinstance(file_size, int)
            or isinstance(file_size, bool)
            or file_size < 0
        ):
            raise ValueError("Invalid file size")

        destination_root = os.path.realpath(DEST_DIR)

        destination_path = os.path.realpath(
            os.path.join(destination_root, filename)
        )

        if os.path.commonpath(
            [destination_root, destination_path]
        ) != destination_root:
            raise ValueError("Invalid destination path")

        print(
            f"\n[CHECK] {filename} "
            f"[Thread: {threading.current_thread().name}]"
        )

        # Get the lock with the destination file
        file_lock = get_file_lock(destination_path)

        # Protect checksum comparison AND file replacement
        with file_lock:

            if os.path.isfile(destination_path):
                server_hash = calculate_sha256(
                    destination_path
                )

                if server_hash == client_hash:
                    print(f"[SKIP] {filename}")

                    send_json(conn, {
                        "status": "SKIP"
                    })

                    continue

            print(f"[SEND] {filename}")

            send_json(conn, {
                "status": "SEND"
            })

            bytes_received = receive_file(
                conn,
                destination_path,
                file_size,
                client_hash
            )

            print(
                f"[RECEIVED] {filename}: "
                f"{bytes_received} bytes"
            )

            send_json(conn, {
                "status": "STORED"
            })

def client_worker(conn, addr):
    print(
        f"[CONNECTED] {addr} "
        f"[Thread: {threading.current_thread().name}]"
    )

    try:
        with conn:
            handle_client(conn)

    except (
        ConnectionError,
        OSError,
        ValueError,
        KeyError,
        TypeError
    ) as error:
        print(f"[ERROR] Client {addr}: {error}")

    finally:
        print(f"[DISCONNECTED] {addr}")

def start_server():
    os.makedirs(DEST_DIR, exist_ok=True)

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as server:

        server.setsockopt(
            socket.SOL_SOCKET,
            socket.SO_REUSEADDR,
            1
        )

        server.bind((HOST, PORT))
        server.listen(5)

        print(
            f"[READY] Server listening on {HOST}:{PORT}"
        )

        while True:
            conn, addr = server.accept()

            thread = threading.Thread(
                target=client_worker,
                args=(conn, addr),
                daemon=True
            )

            thread.start()


if __name__ == "__main__":
    start_server()
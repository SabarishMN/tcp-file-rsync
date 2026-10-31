import os
import socket
import tempfile
import threading

from utils import calculate_sha256, send_json, recv_json


HOST = "127.0.0.1"
PORT = 9001
DEST_DIR = "received_files"

BUFFER_SIZE = 4096


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

        # Resolve the destination path
        destination_root = os.path.realpath(DEST_DIR)

        destination_path = os.path.realpath(
            os.path.join(destination_root, filename)
        )

        if os.path.commonpath(
            [destination_root, destination_path]
        ) != destination_root:
            raise ValueError("Invalid destination path")

        print(f"\n[CHECK] {filename}")
        print("[DEBUG] Checking destination file", flush=True)
        print("[DEBUG] Path:", destination_path, flush=True)
        print("[DEBUG] Exists:", os.path.isfile(destination_path), flush=True)

        if os.path.isfile(destination_path):
            print("[DEBUG] Starting SHA-256 calculation", flush=True)
            server_hash = calculate_sha256(
                destination_path
            )
            print("[DEBUG] SHA-256 calculation completed", flush=True)

            if server_hash == client_hash:
                print("[SKIP] File unchanged")

                send_json(conn, {
                    "status": "SKIP"
                })
                print("[DEBUG] SKIP response transmitted", flush=True)

                continue

        print("[SEND] File missing or modified")

        file_size = metadata["size"]

        if (
            not isinstance(file_size, int)
            or isinstance(file_size, bool)
            or file_size < 0
        ):
            raise ValueError("Invalid file size")

        send_json(conn, {
            "status": "SEND"
        })

        print("[DEBUG] SEND response transmitted", flush=True)

        bytes_received = receive_file(
            conn,
            destination_path,
            file_size,
            client_hash
        )

        print(f"[RECEIVED] {bytes_received} bytes")
        print("[VERIFIED] SHA-256 checksum matched")

        send_json(conn, {
            "status": "STORED"
        })


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

            print(f"\n[CONNECTED] {addr}")

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
                print(f"[ERROR] {error}")

            print(f"[DISCONNECTED] {addr}")


if __name__ == "__main__":
    start_server()
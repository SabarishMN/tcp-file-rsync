import os
import socket

from utils import (
    get_all_files,
    get_file_metadata,
    send_json,
    recv_json
)


SERVER_IP = "127.0.0.1"
PORT = 9001

SOURCE_DIR = "test_data"

BUFFER_SIZE = 4096


def send_file(sock, file_path):
    bytes_sent = 0

    with open(file_path, "rb") as file:
        while True:
            chunk = file.read(BUFFER_SIZE)

            if not chunk:
                break

            sock.sendall(chunk)
            bytes_sent += len(chunk)

    return bytes_sent

def start_client():
    if not os.path.isdir(SOURCE_DIR):
        print("[ERROR] Source directory does not exist")
        return

    files = get_all_files(SOURCE_DIR)

    print(f"[SCAN] Found {len(files)} files")

    with socket.socket(
        socket.AF_INET,
        socket.SOCK_STREAM
    ) as client:

        client.connect((SERVER_IP, PORT))

        print(
            f"[CONNECTED] Server {SERVER_IP}:{PORT}"
        )

        for full_path, relative_path in files:
            metadata = get_file_metadata(
                full_path,
                relative_path
            )

            metadata["type"] = "FILE"

            print(
                f"\n[CHECK] {metadata['filename']}"
            )

            send_json(client, metadata)

            response = recv_json(client)

            if response["status"] == "SKIP":
                print("[SKIP] File unchanged")

            elif response["status"] == "SEND":
                print("[SEND] Server requested file")

                bytes_sent = send_file(client, full_path)

                print(f"[TRANSFER] Sent {bytes_sent} bytes")

                acknowledgment = recv_json(client)

                if acknowledgment["status"] != "STORED":
                    raise RuntimeError(
                        f"File transfer failed: {acknowledgment}"
                )

                print("[SUCCESS] File stored and verified")

            else:
                raise ValueError(
                    "Unknown server response"
                )

        send_json(client, {
            "type": "DONE"
        })

        print("\n[COMPLETE] Metadata exchange finished")


if __name__ == "__main__":
    start_client()
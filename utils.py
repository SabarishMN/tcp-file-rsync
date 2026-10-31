import os
import hashlib
import json
import struct

MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MiB
BUFFER_SIZE = 4096

# The hashing process uses approximately O(n) time for a file 
# of n bytes and O(1) auxiliary memory with a fixed-size buffer

def calculate_sha256(file_path):
    sha256 = hashlib.sha256() # SHA-256 hashing object

    with open(file_path, "rb") as file: # read in binary mode
        while True:
            chunk = file.read(BUFFER_SIZE) # Reads 4 KiB at a time

            if not chunk:
                break

            sha256.update(chunk) # Adds each chunk to the running hash

    return sha256.hexdigest() # final hexadecimal string

def get_all_files(directory):
    files = []

    for root, dirs, filenames in os.walk(directory):
        for filename in filenames:
            full_path = os.path.join(root, filename)

            relative_path = os.path.relpath(
                full_path,
                directory
            )

            files.append((full_path, relative_path))

    return files

# [
#    ("test_data/file1.txt", "file1.txt"),
#    ("test_data/documents/file2.txt", "documents/file2.txt"),
#    ("test_data/documents/notes.txt", "documents/notes.txt"),
#    ("test_data/images/photo.png", "images/photo.png")
# ]


def get_file_metadata(file_path, relative_path):
    return {
        "filename": relative_path.replace(os.sep, "/"),
        "size": os.path.getsize(file_path),
        "sha256": calculate_sha256(file_path)
    }


MAX_MESSAGE_SIZE = 1024 * 1024  # 1 MiB


def recv_exact(sock, num_bytes):
    data = bytearray()

    while len(data) < num_bytes:
        chunk = sock.recv(num_bytes - len(data))

        if not chunk:
            raise ConnectionError(
                "Connection closed unexpectedly"
            )

        data.extend(chunk)

    return bytes(data)


def send_json(sock, message):
    json_data = json.dumps(message).encode("utf-8")

    if len(json_data) > MAX_MESSAGE_SIZE:
        raise ValueError("JSON message too large")

    header = struct.pack("!I", len(json_data))

    sock.sendall(header + json_data)


def recv_json(sock):
    header = recv_exact(sock, 4)

    message_length = struct.unpack("!I", header)[0]

    if message_length > MAX_MESSAGE_SIZE:
        raise ValueError("JSON message too large")

    json_data = recv_exact(sock, message_length)

    return json.loads(json_data.decode("utf-8"))
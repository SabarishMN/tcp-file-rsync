from utils import (
    calculate_sha256,
    get_all_files,
    get_file_metadata
)

SOURCE_DIR = "test_data"


def main():
    files = get_all_files(SOURCE_DIR)

    print(f"Found {len(files)} files\n")

    for full_path, relative_path in files:
        metadata = get_file_metadata(
            full_path,
            relative_path
        )

        print("Filename:", metadata["filename"])
        print("Size:", metadata["size"], "bytes")
        print("SHA-256:", metadata["sha256"])
        print("-" * 50)


if __name__ == "__main__":
    main()
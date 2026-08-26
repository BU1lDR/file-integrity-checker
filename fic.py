import hashlib

def calculate_hash(file_path):
    hasher = hashlib.sha256()

    with open(file_path, "rb") as file:
        while chunk := file.read(4096):
            hasher.update(chunk)

    return hasher.hexdigest()

file_hash = calculate_hash("test_data/1.txt")
print("SHA-256:", file_hash)
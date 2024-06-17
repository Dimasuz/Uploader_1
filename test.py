import os

print("test file")

CURR_DIR = os.path.dirname(os.path.realpath(__file__))
file = os.path.join(CURR_DIR, "test_file.txt")

with open(file, "r") as f:
    print(f.read())


CURR_DIR = os.path.dirname(os.path.realpath(__file__))
print(CURR_DIR)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
print(BASE_DIR)

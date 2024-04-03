# Extract version number from source file. Written in such a way as to enable
# use from a shell script or from a Sphinx conf.py file.

import re
import sys


def get_version(source_file):
    with open(source_file) as f:
        while True:
            line = next(f)
            if line.startswith('__version__'):
                break
    return re.search("'([^']*)'", line)[1]


if __name__ == "__main__":
    sys.stdout.write(get_version(sys.argv[1]))

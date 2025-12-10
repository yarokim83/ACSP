import sys
import os
from pathlib import Path

# Add the current directory to sys.path to allow imports from ACSP
current_dir = Path(__file__).parent.absolute()
sys.path.append(str(current_dir))

from ACSP.main import main

if __name__ == '__main__':
    main()

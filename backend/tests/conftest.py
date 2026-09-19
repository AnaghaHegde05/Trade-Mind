import sys
from pathlib import Path

# Allow `from backend.x import y` regardless of the working directory
# pytest is invoked from.
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# General
DATE = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
PROJECT_PATH = PROJECT_DIR = Path(__file__).resolve().parent.parent

# Data
DATA_PATH = PROJECT_PATH / "data"
CACHE_PATH = DATA_PATH / ".cache"
PLOTS_PATH = DATA_PATH / "plots"
HISTORY_PATH = DATA_PATH / "history"
PYTHON_NOTEBOOKS_PATH = DATA_PATH / "python_notebooks"

for path in [CACHE_PATH, PLOTS_PATH, HISTORY_PATH, PYTHON_NOTEBOOKS_PATH]:
    path.mkdir(parents=True, exist_ok=True)

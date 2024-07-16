from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()


# General
DATE = datetime.now().strftime("%Y-%m-%d")
PROJECT_PATH = PROJECT_DIR = Path(__file__).resolve().parent.parent

# Data
DATA_PATH = PROJECT_PATH / "data"
CACHE_PATH = DATA_PATH / ".cache"
PLOTS_PATH = DATA_PATH / "plots"

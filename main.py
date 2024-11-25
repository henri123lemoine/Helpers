import logging
from dataclasses import dataclass

import fire

from src.prompt_maker.prompt_maker import PromptMaker

logging.basicConfig(
    level=logging.NOTSET,
    format=f"[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logging.getLogger("matplotlib.font_manager").setLevel(
    logging.ERROR
)  # Deactivate bugged matplotlib DEBUG logger
logger = logging.getLogger(__name__)


@dataclass
class Helpers:
    def prompt_maker(self):
        return PromptMaker()


if __name__ == "__main__":
    fire.Fire(Helpers)

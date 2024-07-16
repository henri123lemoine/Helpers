import logging
from dataclasses import dataclass

import fire

from src.logging.helpers import log_all_methods

logging.basicConfig(
    level=logging.NOTSET,
    format=f"[%(levelname)s|%(module)s|L%(lineno)d] %(asctime)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
logging.getLogger("matplotlib.font_manager").setLevel(
    logging.ERROR
)  # Deactivate bugged matplotlib DEBUG logger
logger = logging.getLogger("main")


@dataclass
@log_all_methods
class Main:
    def prompt_maker(self, *args, **kwargs):
        from src.prompt_maker.prompt_maker import PromptMaker

        getattr(PromptMaker(), args[0])(*args[1:], **kwargs)


if __name__ == "__main__":
    fire.Fire(Main)

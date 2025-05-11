import logging
from typing import Any

import yaml

logger = logging.getLogger('rfcrew.utils')


def read_yaml(file_path) -> dict[str, Any]:
    logger.info(f'Reading YAML file: {file_path}')
    with open(file_path, 'r') as file:
        data = yaml.safe_load(file)
    logger.debug(f'YAML data: {data}')
    return data

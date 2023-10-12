from os.path import join
from typing import Dict

from hdx.utilities.loader import load_and_merge_yaml
from hdx.utilities.path import script_dir_plus_file
from hdx.utilities.typehint import ListTuple


def load_yamls(config_files: ListTuple[str]) -> Dict:
    input_files = [
        script_dir_plus_file(join("..", "configs", file), load_yamls)
        for file in config_files
    ]
    project_config = load_and_merge_yaml(input_files)
    return project_config

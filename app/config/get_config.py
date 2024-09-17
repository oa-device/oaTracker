




from typing import List, Literal, TypedDict
import yaml


class Cors(TypedDict):
    allowed_origins: List[str]
    allowed_methods: List[Literal['OPTIONS', 'GET']]
    allowed_headers: List[str]

class Config(TypedDict):
    default_camera: int
    default_model: str
    default_server_port: int
    cors: Cors
    

def getConfig() -> Config:
    with open("config.yaml", "r") as config_file:
        config: Config  = yaml.safe_load(config_file)
        return config
    
    raise ValueError('Config error')
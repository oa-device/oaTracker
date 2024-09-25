




from dataclasses import dataclass
from typing import List, Literal, TypedDict
import torch
import yaml
from ultralytics import settings

# dimension of the camera output
IMG_WIDTH = 640
IMG_HEIGHT = 480

# torch device detection, enables cross-platform hardware acceleration
TORCH_DEVICE = (
    0
    if hasattr(torch.backends, "cuda") and torch.backends.cuda.is_built()
    else "mps"
    if hasattr(torch.backends, "mps") and torch.backends.mps.is_built()
    else "cpu"
)

# Disabled Google Analytics tracking from Yolov8
if settings.get("sync") == True:
    settings["sync"] = False
    settings.save()

class Cors(TypedDict):
    allowed_origins: List[str]
    allowed_methods: List[Literal['OPTIONS', 'GET']]
    allowed_headers: List[str]

class Config(TypedDict):
    default_classes: str
    default_camera: int
    default_model: str
    default_server_port: int
    cors: Cors
    

def get_config() -> Config:
    with open("config.yaml", "r") as config_file:
        config = Config(yaml.safe_load(config_file)) # type: ignore
        return config
    
    raise ValueError('Config error')

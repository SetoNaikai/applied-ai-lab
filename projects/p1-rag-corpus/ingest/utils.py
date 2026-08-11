import yaml

def load_config(config_path: str) -> dict:
    """Load configuration from a YAML file."""
    
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def save_config(config: dict, config_path: str) -> None:
    """Save configuration to a YAML file."""
    
    with open(config_path, "w") as f:
        yaml.safe_dump(config, f)
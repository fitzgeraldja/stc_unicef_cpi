import yaml


def read_yaml_file(yaml_file):
    """Load yaml configurations"""
    config = None
    try:
        with open(yaml_file, "r") as f:
            config = yaml.safe_load(f)
    except:
        raise FileNotFoundError("Couldnt load the file")

    return config


def get_facebook_credentials(creds_file):
    """Get credentials for accessing FB API from the credentials file"""
    creds = read_yaml_file(creds_file)["facebook"]
    token = creds["access_token"]
    id = creds["account_id"]
    limit = creds["limit"]
    radius = creds["radius"]
    optimization = creds["optimization"]

    return token, id, limit, radius, optimization

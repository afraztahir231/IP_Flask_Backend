from app import create_app
from config import DevConfig

if __name__=="__main__":
    APP = create_app(DevConfig)
    APP.run()
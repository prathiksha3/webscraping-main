# config.py

import os

class Config:
    DEBUG = True
    DATABASE_URI = 'sqlite:///scraped_data.db'  # SQLite database URI

class ProductionConfig(Config):
    DEBUG = False
    # Add production database URI

class DevelopmentConfig(Config):
    DEBUG = True
    # Add development database URI

# Choose the appropriate configuration based on your environment
config = DevelopmentConfig if os.environ.get('FLASK_ENV') == 'development' else ProductionConfig

from tortoise import Tortoise
import logging

logger = logging.getLogger(__name__)

CONFIG = {
    "connections":{
        "default":{
            "engine": "tortoise.backends.mysql",
            "credentials":{
                "database": "tegivebot",
                "host": "localhost",
                "password": "",
                "port": 3306,
                "user": "root",
                "minsize": 1,
                "maxsize": 10,
                "charset": "utf8mb4",
                "sql_mode": "STRICT_TRANS_TABLES",
            }
        }
    },
    "apps": {
        "models": {
            "models": ["database.models", "aerich.models"],
            "default_connection": "default",
        }
    },
    "use_tz": False,
    "timezone": "UTC",
}

async def init_db():
    try:
        await Tortoise.init(config=CONFIG)
        await Tortoise.generate_schemas()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
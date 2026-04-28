import logging

from app.settings import Settings


logger = logging.getLogger(__name__)


def load_settings() -> Settings:
    return Settings()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    settings = load_settings()
    logger.info("loaded:%s@%s", settings.oracle_username, settings.oracle_dsn)

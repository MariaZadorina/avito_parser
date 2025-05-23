import os

from dotenv import load_dotenv


load_dotenv()

# DATABASE_URL = os.getenv("POSTGRESQL_DATABASE_URL")
DATABASE_URL = os.getenv("MYSQL_DATABASE_URL")

START_TIME = int(os.getenv("START_TIME", 21))
ESHMAKAR_API_TOKEN = os.getenv("ESHMAKAR_API_TOKEN")
ESHMAKAR_COUNT_OF_PAGE_TO_PARSE = os.getenv("ESHMAKAR_COUNT_OF_PAGE_TO_PARSE")

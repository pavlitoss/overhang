from .base import *

DEBUG = True

ALLOWED_HOSTS = ["*"]

# Use dotenv for local dev
from dotenv import load_dotenv
load_dotenv()

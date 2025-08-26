from datetime import timedelta
import os
from dotenv import load_dotenv

load_dotenv()
class Config:
    #SQLALCHEMY_DATABASE_URI = "sqlite:///mydatabase.db"
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY")
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=24)

    MAIL_SERVER = 'smtp.gmail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USERNAME = os.getenv("USERNAME_FOR_EMAIL")
    MAIL_PASSWORD = os.getenv("PASSWORD_FOR_EMAIL")
    MAIL_DEFAULT_SENDER = os.getenv("USERNAME_FOR_EMAIL")

    CLOUDINARY_CLOUD_NAME = os.environ.get("CLOUDINARY_CLOUD_NAME")
    CLOUDINARY_API_KEY = os.environ.get("CLOUDINARY_API_KEY")
    CLOUDINARY_API_SECRET = os.environ.get("CLOUDINARY_API_SECRET")
    

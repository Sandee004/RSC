from flask import Flask, request, jsonify, Blueprint, render_template, redirect, url_for, current_app
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager, get_jwt
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from flask_migrate import Migrate
from sqlalchemy import text, inspect
from flask_bcrypt import Bcrypt
from flasgger import Swagger
from flask_mail import Mail, Message
from flask_cors import CORS
from sqlalchemy import func
from datetime import datetime, timedelta
import random
import secrets
import string
import uuid
import requests
import cloudinary
import os
import hashlib
import base64
import hmac
from dotenv import load_dotenv
from io import BytesIO
import re
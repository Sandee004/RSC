from flask import Flask, request, jsonify, Blueprint, render_template, redirect, url_for
from flask_jwt_extended import create_access_token, get_jwt_identity, jwt_required, JWTManager
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from sqlalchemy import text, inspect
from flask_bcrypt import Bcrypt
from flasgger import Swagger
from flask_mail import Mail, Message
from flask_cors import CORS
from sqlalchemy import func
from datetime import datetime, timedelta
import random
import string
import requests
import cloudinary
import os
from dotenv import load_dotenv

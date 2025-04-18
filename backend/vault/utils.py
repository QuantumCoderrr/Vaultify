import base64
from cryptography.fernet import Fernet

def generate_key():
    return Fernet.generate_key()

def encrypt_data(data, key):
    return Fernet(key).encrypt(data.encode()).decode()

def decrypt_data(token, key):
    return Fernet(key).decrypt(token.encode()).decode()


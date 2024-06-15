import hmac
import hashlib

def generate_hmac(secret, message):
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

def verify_hmac(secret, message, received_hmac):
    expected_hmac = generate_hmac(secret, message)
    return hmac.compare_digest(expected_hmac, received_hmac)

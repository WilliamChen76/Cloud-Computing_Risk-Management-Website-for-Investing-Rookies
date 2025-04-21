from extensions import db

# This model will be stored in the default database (login.db)
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(256), nullable=False)
    # Add any other fields

# These models will be stored in the profile database (profile.db)
class UserProfile(db.Model):
    __bind_key__ = 'profile'
    id = db.Column(db.Integer, primary_key=True)
    # Removed ForeignKey constraint; store the user_id as an integer.
    user_id = db.Column(db.Integer, nullable=False)
    age = db.Column(db.Integer)
    income_level = db.Column(db.String(50))
    budget = db.Column(db.Float)
    risk_amount = db.Column(db.Float)
    risk_percentage = db.Column(db.Float)
    term_length = db.Column(db.String(50))  # Consider using db.Integer if only whole numbers are expected.
    term_type = db.Column(db.String(50))
    # Add any other fields

class Portfolio(db.Model):
    __bind_key__ = 'profile'
    id = db.Column(db.Integer, primary_key=True)
    # Removed ForeignKey constraint here as well.
    user_id = db.Column(db.Integer, nullable=False)
    # Define additional columns as needed

class Stock(db.Model):
    __bind_key__ = 'profile'
    id = db.Column(db.Integer, primary_key=True)
    # Removed ForeignKey constraint here.
    user_id = db.Column(db.Integer, nullable=False)
    name = db.Column(db.String(50))
    shares = db.Column(db.Integer)
    # Add any additional fields if needed
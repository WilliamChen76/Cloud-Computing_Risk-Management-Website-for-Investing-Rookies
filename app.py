import os
from dotenv import load_dotenv
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from extensions import db
from news_api_utils import get_stock_news
from risk_calculator import analyze_portfolio, get_price_data

# Load variables from .env into os.environ
load_dotenv()

# Create the Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.urandom(24)

# Get database credentials from environment variables
DB_USER = os.environ.get("DB_USER", "postgres")
DB_PASSWORD = os.environ.get("DB_PASSWORD")
DB_ENDPOINT = os.environ.get("DB_ENDPOINT")
DB_PORT = os.environ.get("DB_PORT", "5432")

# Configure PostgreSQL databases in RDS
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/login_db'
app.config['SQLALCHEMY_BINDS'] = {
    'profile': f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_ENDPOINT}:{DB_PORT}/profile_db'
}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# API configuration
app.config['FINLIGHT_API_KEY'] = os.environ.get("FINLIGHT_API_KEY")
app.config['NEWS_CACHE_TIMEOUT'] = 3600  # Cache news for 1 hour (in seconds)

# Initialize the database
db.init_app(app)

# Delay importing models until after the app and db are initialized
with app.app_context():
    from models import User, UserProfile, Portfolio, Stock
    db.create_all()

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        user = User.query.filter_by(email=email).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password')
    
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash('Email already registered')
            return redirect(url_for('signup'))
        
        hashed_password = generate_password_hash(password)
        new_user = User(email=email, password=hashed_password)
        
        db.session.add(new_user)
        db.session.commit()
        
        flash('Account created successfully')
        return redirect(url_for('login'))
    
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/user_info', methods=['GET', 'POST'])
def user_info():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        # Personal info
        age = request.form.get('age')
        income_level = request.form.get('income_level')
        
        # Financial info
        budget = request.form.get('budget')
        risk_tolerance = request.form.get('risk_tolerance')
        
        # Determine risk_amount and risk_percentage based on risk_tolerance
        risk_percentage = 0
        if risk_tolerance == 'low':
            risk_percentage = 0.05
        elif risk_tolerance == 'medium':
            risk_percentage = 0.10
        elif risk_tolerance == 'high':
            risk_percentage = 0.20
            
        risk_amount = float(budget) * risk_percentage
        
        term_length = request.form.get('term_length')
        term_type = request.form.get('term_type')
        
        # Check if profile already exists
        profile = UserProfile.query.filter_by(user_id=user_id).first()
        
        if profile:
            # Update existing profile
            profile.age = age
            profile.income_level = income_level
            profile.budget = budget
            profile.risk_amount = risk_amount
            profile.risk_percentage = risk_percentage
            profile.term_length = term_length
            profile.term_type = term_type
        else:
            # Create new profile
            profile = UserProfile(
                user_id=user_id,
                age=age,
                income_level=income_level,
                budget=budget,
                risk_amount=risk_amount,
                risk_percentage=risk_percentage,
                term_length=term_length,
                term_type=term_type
            )
            db.session.add(profile)
        
        # Process stocks
        stocks = request.form.getlist('stock')
        shares = request.form.getlist('share')
        
        stock_dict = {}  # accumulating shares of same stock

        for i in range(len(stocks)):
            if stocks[i]:  
                stock_name = stocks[i]
                share_count = int(shares[i]) if i < len(shares) and shares[i] else 0

                if stock_name in stock_dict:
                    stock_dict[stock_name] += share_count  # if existing, accumulate it.
                else:
                    stock_dict[stock_name] = share_count # if not existing, initialize share count

        # updating to db
        for stock_name, total_shares in stock_dict.items():
            existing_stock = Stock.query.filter_by(user_id=user_id, name=stock_name).first()
            
            if existing_stock:
                existing_stock.shares += total_shares  
            else:
                new_stock = Stock(user_id=user_id, name=stock_name, shares=total_shares)
                db.session.add(new_stock)
        
        db.session.commit()
        return redirect(url_for('dashboard'))
    
    return render_template('user_info.html', user=user)

@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    profile = UserProfile.query.filter_by(user_id=user_id).first()
    
    # If the profile is not set up yet, redirect to complete user info.
    if not profile:
        flash("Please complete your profile information first.")
        return redirect(url_for('user_info'))
    
    stocks = Stock.query.filter_by(user_id=user_id).all()
    stock_codes = [stock.name for stock in stocks if stock.name]
    
    # Call risk calculator and ensure the result has the expected keys.
    try:
        risk_analysis = analyze_portfolio(user_id)
    except Exception as e:
        print("Error analyzing portfolio:", e)
        risk_analysis = {}
    
    # Ensure that the risk_metrics key exists; set defaults if not.
    if not risk_analysis.get("risk_metrics"):
        risk_analysis["risk_metrics"] = {"risk_score": "N/A", "var_scaled": 0, "daily_volatility": 0, "var_1d": 0, "investment_horizon_days": 0}

    # Convert risk driver DataFrames to lists if they are not empty
    if "top_risk_drivers" in risk_analysis:
        if hasattr(risk_analysis["top_risk_drivers"], "empty") and risk_analysis["top_risk_drivers"].empty:
            risk_analysis["top_risk_drivers"] = []
        else:
            risk_analysis["top_risk_drivers"] = risk_analysis["top_risk_drivers"].to_dict(orient="records")
    else:
        risk_analysis["top_risk_drivers"] = []

    if "bottom_risk_drivers" in risk_analysis:
        if hasattr(risk_analysis["bottom_risk_drivers"], "empty") and risk_analysis["bottom_risk_drivers"].empty:
            risk_analysis["bottom_risk_drivers"] = []
        else:
            risk_analysis["bottom_risk_drivers"] = risk_analysis["bottom_risk_drivers"].to_dict(orient="records")
    else:
        risk_analysis["bottom_risk_drivers"] = []

    if not risk_analysis.get("insights"):
        risk_analysis["insights"] = {"risk_distribution": "N/A", "diversification": "N/A"}
    if not risk_analysis.get("recommendations"):
        risk_analysis["recommendations"] = {"risk_gap": {"gap_amount": 0, "risk_allowed": 0}}
    
    # Prepare historical chart data: last 15 days of portfolio values.
    historical_chart_data = {}
    if stock_codes:
        try:
            price_df = get_price_data(stock_codes)
            if price_df.empty:
                historical_chart_data = {"dates": [], "values": []}
            else:
                pivot = price_df.pivot(index='date', columns='ticker', values='close').fillna(0)
                shares_dict = {stock.name: stock.shares for stock in stocks}
                pivot["portfolio_value"] = pivot.apply(
                    lambda row: sum(row.get(ticker, 0) * shares_dict.get(ticker, 0) for ticker in stock_codes), axis=1)
                chart_df = pivot.sort_index(ascending=False).head(15).sort_index()
                historical_chart_data = {
                    "dates": chart_df.index.astype(str).tolist(),
                    "values": chart_df["portfolio_value"].tolist()
                }
        except Exception as e:
            print("Error retrieving historical price data:", e)
            historical_chart_data = {"dates": [], "values": []}
    else:
        historical_chart_data = {"dates": [], "values": []}
    
    # Retrieve current prices and Day-over-Day (DoD) changes.
    current_prices = {}
    day_over_day_change = {}
    if stock_codes:
        try:
            price_df = get_price_data(stock_codes)
            for ticker, group in price_df.groupby("ticker"):
                group = group.sort_values("date")
                if len(group) >= 2:
                    prev = group.iloc[-2]["close"]
                    curr = group.iloc[-1]["close"]
                    current_prices[ticker] = curr
                    day_over_day_change[ticker] = ((curr - prev) / prev) * 100
                else:
                    current_prices[ticker] = group.iloc[-1]["close"]
                    day_over_day_change[ticker] = 0
        except Exception as e:
            print("Error retrieving current prices:", e)
    
    # Fetch news for stocks
    news_items = []
    if stock_codes:
        try:
            finlight_api_key = app.config['FINLIGHT_API_KEY']
            if finlight_api_key:
                print(f"Fetching news for stock codes: {stock_codes}")
                news_items = get_stock_news(stock_codes, finlight_api_key)
                print(f"Found {len(news_items)} news items")
            else:
                print("Warning: FINLIGHT_API_KEY is not set in environment variables")
        except Exception as e:
            print("Error fetching news:", e)
    
    now = datetime.now()
    
    return render_template(
        'dashboard.html',
        user=user,
        profile=profile,
        stocks=stocks,
        portfolio_value=risk_analysis["risk_metrics"].get("risk_score", "N/A"),
        risk_analysis=risk_analysis,
        historical_chart_data=historical_chart_data,
        current_prices=current_prices,
        day_over_day_change=day_over_day_change,
        now=now,
        news_items=news_items
    )


@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user_id = session['user_id']
    user = User.query.get(user_id)
    
    # Get existing stocks for this user
    existing_stocks = Stock.query.filter_by(user_id=user_id).all()
    
    if request.method == 'POST':
        # Delete all existing stocks for this user
        Stock.query.filter_by(user_id=user_id).delete()
        
        # Process updated stocks
        stocks = request.form.getlist('stock')
        shares = request.form.getlist('share')
        
        stock_dict = {}

        # Accumulating shares
        for i in range(len(stocks)):
            if stocks[i]:
                stock_name = stocks[i]
                share_count = int(shares[i]) if i < len(shares) and shares[i] else 0

                if stock_name in stock_dict:
                    stock_dict[stock_name] += share_count
                else:
                    stock_dict[stock_name] = share_count

        # Delete original data
        Stock.query.filter_by(user_id=user_id).delete()

        # Updating users' stock list
        for stock_name, total_shares in stock_dict.items():
            new_stock = Stock(user_id=user_id, name=stock_name, shares=total_shares)
            db.session.add(new_stock)
        
        db.session.commit()
        flash('Portfolio settings updated successfully')
        return redirect(url_for('dashboard'))
    
    return render_template('settings.html', user=user, stocks=existing_stocks)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
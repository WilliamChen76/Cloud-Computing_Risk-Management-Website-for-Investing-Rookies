# Investment App

This full-stack investment platform allows users to manage their portfolios, assess risks, and view personalized stock news. Built using Flask, PostgreSQL, and various front-end technologies, the app provides an interactive and informative user experience.

## Features

-   **User Authentication**: Secure login and signup functionality with password hashing.
-   **Portfolio Management**: Users can create and manage stock portfolios, specifying the number of shares for each stock.
-   **Risk Analysis**: Portfolio risk score and detailed risk analysis are calculated, offering insights on diversification and asset contributions.
-   **Stock News**: Fetches and displays the latest news articles relevant to the stocks in the user’s portfolio.
-   **Settings**: Users can modify their personal information, financial settings, and stock holdings.

## Folder Structure

```         
├── app.py                # Main application file, where routes and logic are defined
├── db_setup.py           # Script to set up PostgreSQL databases
├── extensions.py         # Contains database setup (SQLAlchemy)
├── instance
│   ├── login.db          # Database for user authentication
│   └── profile.db        # Database for user profiles and portfolio data
├── models.py             # Contains database models (User, UserProfile, Portfolio, Stock)
├── news_api_utils.py     # Utility functions to fetch stock news from an external API
├── news_cache.json       # Caches news data to improve performance
├── requirements.txt      # Lists the required Python packages
├── risk_calculator.py    # Contains functions for calculating portfolio risks and returns
├── static
│   ├── css
│   │   ├── dashboard.css
│   │   └── styles.css
│   ├── images
│   │   └── logo.png
│   └── js
│       ├── dashboard.js
│       └── form.js
└── templates
    ├── dashboard.html    # User dashboard page
    ├── login.html        # Login page
    ├── settings.html     # Settings page for user profile management
    ├── signup.html       # User signup page
    └── user_info.html    # Page to input personal and financial information
├── lambda_market_upload    # Folder for lambda_market_upload functionality
│   └── lambda_market_upload.py  # Lambda function for market upload
└── lambda_rds_loader       # Folder for lambda_rds_loader functionality
    └── lambda_loader_script.py   # Lambda function for RDS data loading
```

## Requirements

To run this project, you need to install the required dependencies:

``` bash
pip install -r requirements.txt
```

### Key Libraries

-   **Flask**: Web framework for building the application.
-   **Flask-SQLAlchemy**: ORM for interacting with PostgreSQL databases.
-   **psycopg2**: PostgreSQL database adapter.
-   **python-dotenv**: For loading environment variables.
-   **requests**: For making HTTP requests to external APIs.
-   **werkzeug**: For password hashing.
-   **gunicorn**: Production-ready server for Flask.

## Environment Setup

The `.env` file is included in the package to help you easily set up the environment variables. You only need to modify it if you want to use your own database or API keys. The `.env` file includes placeholders for database and API configuration.

### .env File Configuration

You can find the `.env` file in the root directory. It contains the following variables:

```         
# Database Configuration
# For user profile and portfolio (credentials database)
DB_ENDPOINT=your_db_endpoint
DB_PORT=5432
DB_USER=your_db_user
DB_PASSWORD=your_db_password

# For stock data (prices database)
DB_STOCK_ENDPOINT=your_stock_db_endpoint
DB_STOCK_PORT=5432
DB_STOCK_DBNAME=your_stock_db_name
DB_STOCK_USER=your_stock_db_user
DB_STOCK_PASSWORD=your_stock_db_password

# API Keys
NEWS_API_KEY=your_news_api_key
FINLIGHT_API_KEY=your_finlight_api_key
```

-   **DB_ENDPOINT**: The endpoint of your PostgreSQL database for user profiles and portfolios.
-   **DB_PORT**: The port of your PostgreSQL database (default is `5432`).
-   **DB_USER**: The username for accessing your database.
-   **DB_PASSWORD**: The password for your database user.
-   **DB_STOCK_ENDPOINT**: The endpoint of your PostgreSQL database for stock price data.
-   **DB_STOCK_DBNAME**: The name of the stock data database.
-   **DB_STOCK_USER**: The username for accessing the stock data database.
-   **DB_STOCK_PASSWORD**: The password for the stock data database user.
-   **NEWS_API_KEY**: Your API key for fetching stock-related news.
-   **FINLIGHT_API_KEY**: Your API key for the Finlight service (stock price data).

If you want to use your own database, replace the placeholders in the `.env` file with your custom values. Otherwise, the default configuration will work for the included databases.

## Database Setup

Run the following command to set up the required databases:

``` bash
python db_setup.py
```

This script will create two PostgreSQL databases: `login_db` and `profile_db` if they don't already exist.

## Running the Application

To start the Flask development server, run:

``` bash
flask run
```

The app will be accessible at `http://3.87.94.5:5000`.

### Access for Professor

You can also access the app through the following link:

[**Investment App Demo**](http://3.87.94.5:5000)

To log in, you can use the credentials for the trial accounts that have been created:

-   User 1 (with portfolio of Grade A as of 17 Apr, 10:03 pm): [account1\@test.com](mailto:account1@test.com){.email} (Password: example123)

-   User 2 (with portfolio of Grade B as of 17 Apr, 10:03 pm): [accountb\@gmail.com](mailto:accountb@gmail.com){.email} (Password: bbb)

-   User 3 (with portfolio of Grade C as of 17 Apr, 10:03 pm): [account3\@test.com](mailto:account3@test.com){.email} (Password: example123)

## User Interface

### Dashboard

-   **Portfolio Overview**: Displays the user’s portfolio risk score and visualizes the portfolio performance.
-   **Risk Contributors**: Shows top and bottom risk contributors to the portfolio.
-   **Financial Metrics**: Provides insights into risk distribution, diversification, and investment term recommendations.
-   **Recent News**: Displays the latest news related to stocks in the user’s portfolio.
-   **Stock Holdings**: Lists the stocks, their current prices, and their day-over-day price changes.

### Profile Setup

-   **Step 1**: Collects personal information such as age and income level.
-   **Step 2**: Collects financial information, including budget, risk tolerance, and investment term details.
-   **Step 3**: Users can add stocks to their portfolio with stock name and share details.

## Lambda Functions

### 1. `lambda_market_upload`

This folder contains the `lambda_market_upload.py` file, which is used as a Lambda function for uploading market data.

-   **lambda_market_upload.py**: This Lambda function is designed to handle the upload of market data to a specified target (e.g., S3 or other storage). It processes incoming data and prepares it for further processing or storage.

### 2. `lambda_rds_loader`

This folder contains the `lambda_loader_script.py` file, which is a Lambda function for loading data into an RDS instance.

-   **lambda_loader_script.py**: This Lambda function connects to an RDS database and loads the necessary data into the database, facilitating easy management and integration of data across different parts of the application.

## Future Improvements

-   Extend the risk analysis features with more detailed metrics.
-   Implement multi-currency support for portfolio management.
-   Optimize the news API for faster retrieval and display of real-time stock news.

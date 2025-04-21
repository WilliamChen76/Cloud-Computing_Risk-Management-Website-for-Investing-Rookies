import os
import psycopg2
import pandas as pd
import numpy as np
from math import sqrt
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Connection settings for user profile and portfolio data (credentials database)
DB_SETTINGS_PROFILE = {
    "host": os.environ.get("DB_ENDPOINT"),  # e.g. rainmaker.coj66s6eaw9l.us-east-1.rds.amazonaws.com
    "port": int(os.environ.get("DB_PORT", 5432)),
    "dbname": "profile_db",
    "user": os.environ.get("DB_USER", "postgres"),
    "password": os.environ.get("DB_PASSWORD", "rainmaker"),
    "sslmode": "require"
}

# Connection settings for price data (stock data database)
DB_SETTINGS_STOCK = {
    "host": os.environ.get("DB_STOCK_ENDPOINT", "database-1.clsgi4mo0yva.ap-southeast-2.rds.amazonaws.com"),
    "port": int(os.environ.get("DB_STOCK_PORT", 5432)),
    "dbname": os.environ.get("DB_STOCK_DBNAME", "postgres"),
    "user": os.environ.get("DB_STOCK_USER", "postgres"),
    "password": os.environ.get("DB_STOCK_PASSWORD", "rainmaker"),
    "sslmode": "require"
}

# --------------------- Data Retrieval Functions --------------------- #
def get_user_profile(user_id):
    """
    Retrieve the user profile details for a given user_id from the credentials database.
    """
    conn = psycopg2.connect(**DB_SETTINGS_PROFILE)
    query = """
        SELECT budget, risk_percentage, term_length, term_type 
        FROM user_profile 
        WHERE user_id = %s;
    """
    df = pd.read_sql(query, conn, params=[user_id])
    conn.close()
    if df.empty:
        raise ValueError(f"No profile found for user_id {user_id}")
    return df.iloc[0]

def get_user_stocks(user_id):
    """
    Retrieve the user's stock portfolio from the credentials database.
    """
    conn = psycopg2.connect(**DB_SETTINGS_PROFILE)
    query = "SELECT name, shares FROM stock WHERE user_id = %s;"
    df = pd.read_sql(query, conn, params=[user_id])
    conn.close()
    return df

def get_price_data(tickers):
    """
    Retrieve historical price data for the specified tickers from the stock data database.
    """
    conn = psycopg2.connect(**DB_SETTINGS_STOCK)
    placeholders = ', '.join(['%s'] * len(tickers))
    query = f"SELECT date, ticker, close FROM prices WHERE ticker IN ({placeholders}) ORDER BY date ASC;"
    df = pd.read_sql(query, conn, params=tickers)
    conn.close()
    return df

# --------------------- Calculation Functions --------------------- #
def calculate_portfolio_returns(price_df, weights, tickers):
    pivot = price_df.pivot(index='date', columns='ticker', values='close')
    daily_returns = pivot.pct_change().dropna()

    # Ensure weights are aligned with the pivot's column order
    weights_series = pd.Series(weights, index=tickers)
    weights_aligned = weights_series[pivot.columns]

    portfolio_returns = daily_returns.dot(weights_aligned)
    return daily_returns, portfolio_returns


def calculate_risk_metrics(weighted_returns, portfolio_value, risk_amount, term_length, term_type):
    """
    Compute volatility and VaR metrics for the portfolio and assign a risk score.
    """
    daily_vol = np.std(weighted_returns)
    var_95 = np.percentile(weighted_returns, 5)
    var_1d = -var_95 * portfolio_value

    days = int(term_length) * 30
    var_scaled = var_1d * sqrt(days)

    # Assign risk score based on var_scaled relative to risk_amount thresholds
    if var_scaled <= risk_amount:
        risk_score = "A"
    elif var_scaled <= risk_amount * 1.2:
        risk_score = "B"
    else:
        risk_score = "C"

    return {
        "daily_volatility": daily_vol,
        "var_1d": var_1d,
        "var_scaled": var_scaled,
        "risk_score": risk_score,
        "investment_horizon_days": days
    }

def calculate_risk_contributions(daily_returns, weights, tickers):
    """
    Calculate risk contributions from each asset in the portfolio.
    """
    cov_matrix = daily_returns.cov()

    
    portfolio_std = np.sqrt(np.dot(weights, np.dot(cov_matrix, weights)))
    marginal_contributions = np.dot(cov_matrix, weights) / portfolio_std
    vol_contributions = weights * marginal_contributions
    percent_contributions = vol_contributions / portfolio_std

    # Align weights with ticker names from daily_returns.columns
    weights_series = pd.Series(weights, index=tickers)
    weights_aligned = weights_series[daily_returns.columns]

    # Risk contribution
    portfolio_std = np.sqrt(np.dot(weights_aligned, np.dot(cov_matrix, weights_aligned)))
    marginal_contributions = np.dot(cov_matrix, weights_aligned) / portfolio_std
    vol_contributions = weights_aligned * marginal_contributions
    percent_contributions = vol_contributions / portfolio_std

    contribution_df = pd.DataFrame({
        'Ticker': daily_returns.columns,
        'Weight': weights_aligned.values,
        'Risk_Contribution': percent_contributions * 100
    })

    return contribution_df

# --------------------- Aggregation & Recommendation Functions --------------------- #
def analyze_portfolio(user_id):
    """
    Aggregate portfolio data, calculate risk metrics, and generate insights and recommendations.
    Returns a dictionary with all results.
    """
    # Data retrieval from the credentials database
    profile = get_user_profile(user_id)
    portfolio = get_user_stocks(user_id)
    tickers = portfolio['name'].tolist()
    shares = portfolio['shares'].astype(float).tolist()
    risk_amount = profile['budget'] * profile['risk_percentage']

    # Retrieve price data from the stock database
    prices = get_price_data(tickers)
    if prices.empty:
        raise ValueError("No price data available for these tickers.")

    # Get the latest price for each ticker
    latest_prices = prices.sort_values("date").groupby("ticker").last().reset_index()
    latest_dict = dict(zip(latest_prices["ticker"], latest_prices["close"]))

    # Calculate weights based on current market values
    weights_value = [latest_dict[t] * s for t, s in zip(tickers, shares)]
    total_value = sum(weights_value)
    weights = [v / total_value for v in weights_value]

    # Calculate portfolio returns
    daily_returns, weighted_returns = calculate_portfolio_returns(prices, weights, tickers)


    # Now calculate risk metrics
    risk_metrics = calculate_risk_metrics(
        weighted_returns,
        total_value,
        risk_amount,
        profile['term_length'],
        profile['term_type']
    )


    # Calculate risk contributions
    contribution_df = calculate_risk_contributions(daily_returns, weights, tickers)
    top_risk_drivers = contribution_df.sort_values(by='Risk_Contribution', ascending=False).head(3)
    bottom_risk_drivers = contribution_df.sort_values(by='Risk_Contribution', ascending=True).head(3)

    # Portfolio breakdown data
    portfolio_breakdown = []
    for t, s in zip(tickers, shares):
        portfolio_breakdown.append({
            "Ticker": t,
            "Shares": int(s),
            "Value_USD": latest_dict[t] * s
        })

    # Generate insights
    insights = {}
    dominant = contribution_df.iloc[0]
    if dominant['Risk_Contribution'] > contribution_df['Risk_Contribution'][1:].sum():
        insights["concentration"] = f"Concentration Alert: {dominant['Ticker']} alone contributes more to portfolio risk than all other assets combined!"
    else:
        top_contrib = contribution_df.head(3)
        insights["risk_distribution"] = (
            f"Risk Distribution Insight: Your top {len(top_contrib)} assets "
            f"({', '.join(top_contrib['Ticker'])}) make up {top_contrib['Risk_Contribution'].sum():.1f}% of total portfolio risk."
        )

    insights["diversification"] = (
        f"Diversification Insight: '{bottom_risk_drivers.iloc[0]['Ticker']}' currently contributes only "
        f"{bottom_risk_drivers.iloc[0]['Risk_Contribution']:.2f}% to your total risk."
    )

    # Recommendations based on risk score
    recommendations = {}
    gap = risk_metrics["var_scaled"] - risk_amount

    recommendations["risk_gap"] = {
        "gap_amount": gap,
        "status": "over" if gap > 0 else "under",
        "risk_allowed": risk_amount
    }
    
    if risk_metrics["risk_score"] == "C":
        reduction_ratio = (risk_amount / risk_metrics["var_1d"]) ** 2
        recommended_days = int(reduction_ratio)
        recommendations["investment_term"] = f"Reduce investment term to ~{recommended_days} days to meet your risk allowance."
        
        top_asset = top_risk_drivers.iloc[0]['Ticker']
        current_units = portfolio[portfolio['name'] == top_asset]['shares'].values[0]
        top_asset_price = latest_dict[top_asset]
        top_asset_risk_pct = top_risk_drivers.iloc[0]['Risk_Contribution'] / 100
        top_asset_var_contribution = top_asset_risk_pct * risk_metrics["var_scaled"]

        if top_asset_var_contribution > 0:
            risk_per_unit = top_asset_var_contribution / (current_units * top_asset_price)
            units_to_remove = gap / (risk_per_unit * top_asset_price)
            units_to_remove = min(current_units, round(units_to_remove, 2))
        else:
            units_to_remove = 0

        recommendations["asset_adjustment"] = {
            "action": f"Reduce {top_asset} holdings by approximately {units_to_remove} units.",
            "alternative_budget": f"Increase your budget to ${risk_metrics['var_scaled'] / profile['risk_percentage']:.2f} to absorb the risk."
        }
    elif risk_metrics["risk_score"] == "B":
        margin = risk_amount / 1.15 - risk_metrics["var_scaled"]
        extension_days = ((risk_amount / 1.15) / risk_metrics["var_1d"]) ** 2
        added_days = int(extension_days - risk_metrics["investment_horizon_days"])
        recommendations["watch_warning"] = (
            f"Watch out for {top_risk_drivers.iloc[0]['Ticker']} which is nearing your risk boundary. "
            f"You can increase risk by ${margin:,.2f} before hitting your limit. "
            f"Consider extending your investment period by ~{added_days} days."
        )
    elif risk_metrics["risk_score"] == "A":
        spare_risk = risk_amount - risk_metrics["var_scaled"]
        positive_contributors = contribution_df[contribution_df["Risk_Contribution"] >= 0]
        if not positive_contributors.empty:
            potential_asset = positive_contributors.sort_values("Risk_Contribution").iloc[0]["Ticker"]
            current_units = portfolio[portfolio["name"] == potential_asset]["shares"].values[0]
            current_price = latest_dict[potential_asset]
            risk_pct = contribution_df[contribution_df["Ticker"] == potential_asset]["Risk_Contribution"].values[0] / 100
            contribution_to_var = risk_pct * risk_metrics["var_scaled"]

            if current_units > 0 and contribution_to_var > 0 and spare_risk > 0:
                risk_per_dollar = contribution_to_var / (current_units * current_price)
                additional_dollars = spare_risk / risk_per_dollar
                units_to_add = int(additional_dollars / current_price)
                recommendations["asset_adjustment"] = (
                    f"You could add approximately {units_to_add} units of {potential_asset} without exceeding your risk limit."
                )
            else:
                recommendations["asset_adjustment"] = f"Consider allocating to {potential_asset}, but a safe unit suggestion could not be computed."
        else:
            best_hedge = contribution_df.sort_values("Risk_Contribution").iloc[0]["Ticker"]
            recommendations["asset_adjustment"] = (
                f"All assets contribute negatively to portfolio risk. Consider {best_hedge} as a potential hedge."
            )

    return {
        "portfolio_breakdown": portfolio_breakdown,
        "risk_metrics": risk_metrics,
        "risk_contributions": contribution_df,
        "top_risk_drivers": top_risk_drivers,
        "bottom_risk_drivers": bottom_risk_drivers,
        "insights": insights,
        "recommendations": recommendations,
        "total_portfolio_value": total_value
    }
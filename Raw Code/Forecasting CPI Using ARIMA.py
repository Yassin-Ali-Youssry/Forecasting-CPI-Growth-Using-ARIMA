import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.ticker import MultipleLocator
import pandas_datareader.data as web
from pmdarima.arima import auto_arima
import warnings

# Suppress warnings
warnings.filterwarnings("ignore")

# === User Inputs ===
start_date = input("Enter start date (DD-MM-YYYY): ")
end_date = input("Enter end date (DD-MM-YYYY): ")
forecast_period = int(input("Enter forecast period in months: "))

# === Load CPI Data ===
df = web.DataReader('CPIAUCSL', 'fred', start_date, end_date)
df.rename(columns={'CPIAUCSL': 'CPI'}, inplace=True)
df.index = pd.to_datetime(df.index)

# === Calculate Year-over-Year Inflation ===
df['YoY_Inflation'] = df['CPI'].pct_change(periods=12) * 100

# === Calculate Quarterly Inflation Rate (QoQ) ===
df['QoQ_Inflation'] = df['CPI'].pct_change(periods=3) * 100

# === Fit ARIMA Model (silently) ===
def fit_arima_silently(series):
    with open(os.devnull, 'w') as f, warnings.catch_warnings():
        warnings.simplefilter("ignore")
        sys.stdout = f
        model = auto_arima(series,
                           seasonal=False,
                           stepwise=True,
                           suppress_warnings=True,
                           trace=False)
        sys.stdout = sys.__stdout__
    return model

model = fit_arima_silently(df['CPI'])

# === Forecast with Confidence Intervals ===
forecast, conf_int = model.predict(n_periods=forecast_period, return_conf_int=True)

# Forecast index (same as before)
forecast_index = pd.date_range(start=df.index[-1] + pd.DateOffset(months=1),
                               periods=forecast_period, freq='MS')

# Convert forecast and confidence intervals to Series/DataFrame
forecast_series = pd.Series(forecast, index=forecast_index)
conf_df = pd.DataFrame(conf_int, index=forecast_index, columns=['Lower CI', 'Upper CI'])

import statsmodels.api as sm
from statsmodels.stats.diagnostic import acorr_ljungbox

#=========================================================================================
# === Optional: Residual Diagnostics ===

# Calculate residuals: actual - fitted
#residuals = pd.Series(model.resid(), index=df.index)

# Plot residuals over time
#plt.figure(figsize=(12, 6))
#plt.plot(residuals, color='tab:red')
#plt.title('ARIMA Model Residuals Over Time')
#plt.xlabel('Date')
#plt.ylabel('Residual')
#plt.grid(True)
#plt.show()

# Plot ACF and PACF of residuals
#fig, axes = plt.subplots(1, 2, figsize=(16, 5))

# ACF plot
#sm.graphics.tsa.plot_acf(residuals, lags=40, ax=axes[0])
#axes[0].set_title('Residuals Autocorrelation Function (ACF)')

# PACF plot
#sm.graphics.tsa.plot_pacf(residuals, lags=40, ax=axes[1])
#axes[1].set_title('Residuals Partial Autocorrelation Function (PACF)')

#plt.tight_layout()
#plt.show()

# Ljung-Box test for autocorrelation in residuals
#lb_test = acorr_ljungbox(residuals, lags=[10, 20], return_df=True)

#print("Ljung-Box test results (p-values):")
#print(lb_test[['lb_stat', 'lb_pvalue']])

# Interpretation:
# If p-values > 0.05, residuals behave like white noise → model is adequate.
# If p-values < 0.05, residuals show autocorrelation → model needs improvement.
#=========================================================================================

# === Combined Plot with YoY and QoQ on top, CPI Forecast below ===
fig = plt.figure(figsize=(18, 12))

# Top-left: YoY Inflation
ax1 = fig.add_subplot(2, 2, 1)
ax1.plot(df.index, df['YoY_Inflation'], color='tab:blue', label='YoY Inflation Rate (%)')
ax1.set_title('U.S. YoY Inflation Rate', fontsize=14)
ax1.set_xlabel('Year', fontsize=12)
ax1.set_ylabel('Inflation Rate (%)', fontsize=12)
ax1.grid(True)
ax1.legend()
ax1.xaxis.set_major_locator(mdates.YearLocator())
ax1.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax1.tick_params(axis='x', rotation=45)

# Top-right: QoQ Inflation
ax2 = fig.add_subplot(2, 2, 2)
ax2.plot(df.index, df['QoQ_Inflation'], label='QoQ Inflation Rate (%)', color='tab:green', linestyle=':')
ax2.set_title('U.S. QoQ Inflation Rate', fontsize=14)
ax2.set_xlabel('Year', fontsize=12)
ax2.set_ylabel('Inflation Rate (%)', fontsize=12)
ax2.grid(True)
ax2.legend()
ax2.xaxis.set_major_locator(mdates.YearLocator())
ax2.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax2.tick_params(axis='x', rotation=45)

# Bottom (spanning full width): CPI Forecast
ax3 = fig.add_subplot(2, 1, 2)  # spans both columns since 2 rows, 1 col here
ax3.plot(df.index, df['CPI'], label='CPI (Actual)', color='tab:green')
ax3.plot(forecast_series.index, forecast_series, label='CPI Forecast', color='tab:orange', linestyle='--')

# Add confidence interval shading
ax3.fill_between(conf_df.index, conf_df['Lower CI'], conf_df['Upper CI'], color='orange', alpha=0.3, label='Confidence Interval')

ax3.axvspan(df.index[-1], forecast_series.index[-1], color='gray', alpha=0.15, label="Forecast Period")

ax3.set_title('CPI Forecast (ARIMA)', fontsize=14)
ax3.set_xlabel('Year', fontsize=12)
ax3.set_ylabel('CPI Index', fontsize=12)
ax3.grid(True)
ax3.legend()
ax3.xaxis.set_major_locator(mdates.YearLocator())
ax3.xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
ax3.tick_params(axis='x', rotation=45)

# Adjust whitespace between plots
fig.subplots_adjust(wspace=0.3, hspace=0.4)

plt.tight_layout()
plt.show()

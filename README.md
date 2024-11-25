# Optimizing Schedules Based on Weather Predictions
## Overview
This project is a Streamlit dashboard that optimizes activity schedules based on real-time weather data and user-defined preferences. By leveraging Constraint Satisfaction Problems (CSP), Weighted CSP (WCSP), and Conditional Preference Networks (CP-Nets), the application assists users in planning activities efficiently while considering weather conditions such as temperature and precipitation.

## Features
- **Activity Scheduling**: Input multiple activities with unique names, durations (in 15-minute intervals), and weather preferences.
- **Weather Preferences**:
  - **WCSP**: Supports multiple weather preferences in order of priority.
  - **CSP and CP-Nets**: Allow a single weather preference per activity.
- **Planning Parameters**:
  - Select planning dates (up to the next 3 days).
  - Specify start and end times.
- **Validation**: Provides error messages for invalid inputs, such as overlapping activity names or improper time ranges.
- **Visualization**: Generates activity timelines to visualize optimized schedules.
- **Real-Time Weather Integration**: Fetches live weather data using the WeatherAPI for accurate scheduling.

## Installation

### Clone the Repository
```bash
git clone https://github.com/yourusername/yourrepository.git
cd yourrepository
```

### Create a Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
```

### Install Dependencies
```bash
pip install -r requirements.txt
```
Ensure that the `requirements.txt` file includes all necessary libraries such as:
- `streamlit`
- `pandas`
- `matplotlib`
- `networkx`
- `requests`
- `python-constraint`
- `seaborn`

### Set Up Weather API Key
1. Obtain an API key from [WeatherAPI](https://www.weatherapi.com/).
2. Replace the placeholder `api_key` in the code with your actual API key.

## Usage

### Run the Streamlit App
```bash
streamlit run app.py
```

### Interact with the Dashboard
1. **Enter Activities**: Provide activity names, durations, and weather preferences.
2. **Set Planning Parameters**: Choose the date and time range for scheduling.
3. **Submit**: Click the "Submit" button to generate the optimized schedule.
4. **View Results**: The app will display the scheduled activities along with execution time and a visual timeline.

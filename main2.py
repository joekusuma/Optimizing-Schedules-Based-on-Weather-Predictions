# Library Imports
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import requests
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
from constraint import Problem, AllDifferentConstraint, FunctionConstraint, BacktrackingSolver

# Constants and Global Variables
api_key = "28c300a25e5245d6ba3223640231511"
location = "Los Angeles"

# Function to Fetch and Process Weather Data for a Specific Day
def fetch_weather_data(api_key, location, selected_date):
    url = f"http://api.weatherapi.com/v1/history.json?key={api_key}&q={location}&dt={selected_date}"
    response = requests.get(url)
    data = response.json()

    df_weather = pd.DataFrame()
    for hour in data['forecast']['forecastday'][0]['hour']:
        df_weather = df_weather.append({
            'date': selected_date,
            'time': hour['time'],
            'temp_c': hour['temp_c'],
            'wind_kph': hour['wind_kph'],
            'humidity': hour['humidity'],
            'chance_of_rain': hour['chance_of_rain'],
            'precip_mm': hour['precip_mm'],
            'vis_km': hour['vis_km'],
        }, ignore_index=True)

    df_weather['datetime'] = pd.to_datetime(df_weather['time'])
    df_weather['datetime_numeric'] = df_weather['datetime'].apply(lambda x: x.timestamp() if not pd.isnull(x) else None) / 10**9
    return df_weather

# Function to check weather conditions
def weather_condition_check(temp_c, wind_kph, humidity, chance_of_rain, condition):
    if condition == 'Sunny':
        return chance_of_rain < 20
    elif condition == 'Cloudy':
        return 20 <= chance_of_rain <= 70
    elif condition == 'Rainy':
        return chance_of_rain > 70
    else:
        return True  # Default case

# Function to Create WCSP with Weather and Activities
def create_wcsp_with_weather_and_activities(weather_data, activities, start_hour, end_hour):
    wcsp_problem = Problem(BacktrackingSolver())

    # Trim the weather data to the specified hours
    weather_data_filtered = weather_data[(weather_data['datetime'].dt.hour >= start_hour) & (weather_data['datetime'].dt.hour < end_hour)]
    
    # Add variables for each time slot
    for index in weather_data_filtered.index:
        wcsp_problem.addVariable(str(index), [1, 0])  # 1 for activity scheduled, 0 for not

    # Adding weather constraints for each time slot
    for index, row in weather_data_filtered.iterrows():
        wcsp_problem.addConstraint(
            FunctionConstraint(
                lambda x, temp=row['temp_c'], wind=row['wind_kph'],
                humidity=row['humidity'], rain=row['chance_of_rain']: 
                x == 0 or weather_condition_check(temp, wind, humidity, rain, "Any")
            ), 
            [str(index)]
        )

    # Adding constraints for activities
    for activity in activities:
        duration = activity['duration']
        condition = activity['weather_condition']
        
        # Check for each possible starting time slot for the activity
        for i in range(len(weather_data_filtered) - duration + 1):
            time_slots = [str(weather_data_filtered.index[j]) for j in range(i, i + duration)]
            wcsp_problem.addConstraint(
                FunctionConstraint(
                    lambda *args, cond=condition, data=weather_data_filtered: all(
                        weather_condition_check(data.loc[int(arg), 'temp_c'], 
                                                data.loc[int(arg), 'wind_kph'],
                                                data.loc[int(arg), 'humidity'],
                                                data.loc[int(arg), 'chance_of_rain'],
                                                cond) for arg in args
                    ),
                    time_slots
                )
            )

    return wcsp_problem, list(wcsp_problem._variables)

# Function to Solve WCSP and Generate Optimized Schedule
def generate_optimized_schedule(wcsp_problem, weather_data):
    solution = wcsp_problem.getSolution()
    if solution:
        schedule = []
        for index in sorted(solution.keys(), key=lambda x: weather_data.loc[int(x), 'datetime']):
            if solution[index] == 1:
                time_slot = weather_data.loc[int(index), 'datetime'].strftime("%Y-%m-%d %H:%M:%S")
                schedule.append(time_slot)
        return schedule
    else:
        return None
# Function to Solve WCSP and Generate Optimized Schedule
def generate_optimized_schedule(wcsp_problem, weather_data):
    solution = wcsp_problem.getSolution()
    if solution:
        schedule = []
        for index in sorted(solution.keys(), key=lambda x: weather_data.loc[int(x), 'datetime']):
            time_slot = weather_data.loc[int(index), 'datetime'].strftime("%Y-%m-%d %H:%M:%S")
            activity_index = solution[index]
            schedule.append((time_slot, activity_index))
        return schedule
    else:
        return None

# Main Function for Streamlit Dashboard
def main():
    st.title("Weather Optimization Dashboard")
    
    selected_date = st.date_input("Select a Date", min_value=datetime.now())
    start_time = st.time_input("Start Time")
    end_time = st.time_input("End Time")
    start_hour = start_time.hour
    end_hour = end_time.hour

    df_weather = fetch_weather_data(api_key, location, selected_date.strftime("%Y-%m-%d"))
    st.write(df_weather)

    activities = []
    num_activities = st.number_input("Number of Activities", min_value=0, step=1)
    for i in range(num_activities):
        duration = st.slider(f"Activity {i+1} Duration (Hours)", 1, 24, 2)
        weather_condition = st.selectbox(f"Activity {i+1} Weather Condition", ['Sunny', 'Cloudy', 'Rainy'])
        activities.append({'duration': duration, 'weather_condition': weather_condition})
    
    wcsp_problem, variable_list = create_wcsp_with_weather_and_activities(df_weather, activities, start_hour, end_hour)
    optimized_schedule = generate_optimized_schedule(wcsp_problem, df_weather)

    if optimized_schedule:
        st.write("Optimized Schedule:", optimized_schedule)
    else:
        st.write("No feasible schedule found.")

# Entry Point of the Application
if __name__ == "__main__":
    main()

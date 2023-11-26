# Library Imports
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import requests
from datetime import datetime, timedelta
from constraint import Problem, AllDifferentConstraint, FunctionConstraint, BacktrackingSolver
import seaborn as sns
import logging

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
    return df_weather

# Function to check weather conditions
def weather_condition_check(chance_of_rain, condition):
    if condition == 'Sunny':
        return chance_of_rain < 20
    elif condition == 'Cloudy':
        return 20 <= chance_of_rain <= 70
    elif condition == 'Rainy':
        return chance_of_rain > 70
    else:
        return True  # Default case

def is_within_time_range(start_time, end_time, activity_start, activity_duration):
    activity_end = activity_start + activity_duration
    return start_time <= activity_start and activity_end <= end_time

def combine_date_time(date_obj, time_obj):
    return datetime.combine(date_obj, time_obj)

def solve_wcsp(activities, weather_data, start_datetime, end_datetime):
    # Create a constraint problem
    problem = Problem(BacktrackingSolver())

    # Convert weather data to a dictionary for easy access
    weather_dict = {pd.to_datetime(row['datetime']): row for index, row in weather_data.iterrows()}

    # Add variables for each activity (activity start time)
    for activity in activities:
        # Define possible start times for each activity
        possible_start_times = []
        for hour in range(int((end_datetime - start_datetime).total_seconds() // 3600) - int(activity['duration'])):
            possible_start = start_datetime + timedelta(hours=hour)
            possible_end = possible_start + timedelta(hours=activity['duration'])
            if possible_end <= end_datetime:
                possible_start_times.append(possible_start)

        problem.addVariable(activity['name'], possible_start_times)

    # Add AllDifferentConstraint to ensure no overlapping activities
    problem.addConstraint(AllDifferentConstraint())

    # Add weather constraints for each activity
    def weather_constraint(activity_start, activity, weather_dict):
        activity_end = activity_start + timedelta(hours=activity['duration'])
        while activity_start < activity_end:
            weather_info = weather_dict.get(activity_start)
            if weather_info and not weather_condition_check(weather_info['chance_of_rain'], activity['weather']):
                return False
            activity_start += timedelta(hours=1)
        return True

    for activity in activities:
        problem.addConstraint(FunctionConstraint(lambda start, act=activity: weather_constraint(start, act, weather_dict)), [activity['name']])

    # Solve the problem
    solution = problem.getSolution()

    if solution is None:
        return "No feasible schedule found."

    # Convert solution to a more readable format
    schedule = {}
    for activity in activities:
        start_time = solution[activity['name']]
        end_time = start_time + timedelta(hours=activity['duration'])
        schedule[activity['name']] = {'start': start_time, 'end': end_time}

    return schedule

# Streamlit User Interface for Activity Input
def add_activity_input(key):
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_name = st.text_input("Activity Name", key=f"activity_{key}")
        with col2:
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=12.0, step=0.5, key=f"duration_{key}")
        with col3:
            weather_preference = st.selectbox("Preferred Weather", ["Sunny", "Cloudy", "Rainy", "No Preference"], key=f"weather_{key}")
    return {"name": activity_name, "duration": duration, "weather": weather_preference}

def user_interface():
    st.title("Activity Scheduler Using Weather Constraints")
    st.subheader("Enter Activities")
    activities = []
    activity_count = st.number_input("How many activities do you want to schedule?", min_value=1, max_value=10, step=1)

    for i in range(activity_count):
        activity = add_activity_input(i)
        activities.append(activity)

    st.subheader("Planning Day and Time")
    planning_day = st.date_input("Select the Day for Planning")
    start_time = st.time_input("Start Time", key="start_time")
    end_time = st.time_input("End Time", key="end_time")

    if st.button("Submit"):
        st.write("Scheduled Activities:")
        for activity in activities:
            st.write(activity)
        
        start_datetime = combine_date_time(planning_day, start_time)
        end_datetime = combine_date_time(planning_day, end_time)

        weather_data = fetch_weather_data(api_key, location, planning_day.strftime("%Y-%m-%d"))
        wcsp_schedule = solve_wcsp(activities, weather_data, start_datetime, end_datetime)

        if isinstance(wcsp_schedule, str):
            st.write(wcsp_schedule)
        else:
            st.write("Optimized Schedule:")
            for activity in wcsp_schedule:
                start = wcsp_schedule[activity]['start']
                end = wcsp_schedule[activity]['end']
                st.write(f"{activity}: Start at {start.strftime('%Y-%m-%d %H:%M')}, End by {end.strftime('%Y-%m-%d %H:%M')}")

# Main Function
def main():
    user_interface()

if __name__ == "__main__":
    main()
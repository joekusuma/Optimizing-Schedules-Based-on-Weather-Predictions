# Library Imports
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import requests
from datetime import datetime, timedelta
from constraint import Problem, AllDifferentConstraint, FunctionConstraint, BacktrackingSolver
import seaborn as sns

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

# Enhanced WCSP Algorithm Implementation
def solve_wcsp(activities, weather_data, start_datetime, end_datetime):
    problem = Problem()

    # Generate time slots
    time_slots = pd.date_range(start=start_datetime, end=end_datetime, freq='H').tolist()

    # Prepare activity data and constraints
    for activity in activities:
        duration = timedelta(hours=activity['duration'])
        valid_slots = [time for time in time_slots if time + duration <= end_datetime]
        problem.addVariable(activity['name'], valid_slots)

    # Add weather constraints
    for activity in activities:
        def weather_constraint(slot, activity=activity):
            duration = timedelta(hours=activity['duration'])
            for delta in range(int(duration.total_seconds() // 3600)):
                time = slot + timedelta(hours=delta)
                weather_row = weather_data.loc[weather_data['datetime'] == time]
                if weather_row.empty or not weather_condition_check(weather_row.iloc[0]['chance_of_rain'], activity['weather']):
                    return False
            return True

        problem.addConstraint(weather_constraint, [activity['name']])

    def no_overlap_constraint(slot1, slot2, name1, name2):
        if name1 == name2:  # Skip checking overlap for the same activity
            return True

        duration1 = next((timedelta(hours=act['duration']) for act in activities if act['name'] == name1), timedelta())
        end1 = slot1 + duration1

        duration2 = next((timedelta(hours=act['duration']) for act in activities if act['name'] == name2), timedelta())
        end2 = slot2 + duration2

        # Check if there is an overlap
        overlap = (slot1 < end2) and (slot2 < end1)
        return not overlap

    activity_names = [act['name'] for act in activities]
    for i, name1 in enumerate(activity_names):
        for j, name2 in enumerate(activity_names):
            if i != j:
                problem.addConstraint(no_overlap_constraint, [name1, name2, name1, name2])

    # Solve the problem
    solutions = problem.getSolutions()
    if solutions:
        optimized_schedule = {}
        for activity_name in solutions[0]:
            start = solutions[0][activity_name]
            duration = next((timedelta(hours=act['duration']) for act in activities if act['name'] == activity_name), timedelta())
            end = start + duration
            optimized_schedule[activity_name] = {'start': start, 'end': end}
        return optimized_schedule
    else:
        return "No feasible schedule found"
        
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

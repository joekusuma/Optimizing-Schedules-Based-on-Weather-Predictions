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
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
from datetime import date

# Constants and Global Variables
api_key = ""
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

def add_activity_input(key):
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_name = st.text_input("Activity Name", key=f"activity_{key}")
        with col2:
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=12.0, step=0.5, key=f"duration_{key}")
        with col3:
            # Updated weather preferences
            weather_preference = st.multiselect("Weather Preference (Select in order of preference)", 
                                                ["Sunny", "Cloudy", "Rainy"], 
                                                key=f"weather_{key}")
    return {"name": activity_name, "duration": duration, "weather": weather_preference}

def weather_condition_check(chance_of_rain, preferences):
    # Mapping conditions to chance of rain
    condition_map = {
        'Sunny': lambda rain_chance: rain_chance < 20,
        'Cloudy': lambda rain_chance: 20 <= rain_chance <= 70,
        'Rainy': lambda rain_chance: rain_chance > 70
    }

    # Check weather conditions based on preferences
    for preference in preferences:
        if condition_map[preference](chance_of_rain):
            return True
    return False

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
        for minute in range(0, int((end_datetime - start_datetime).total_seconds() // 60) - int(activity['duration']*60) + 1):
            possible_start = start_datetime + timedelta(minutes=minute)
            possible_end = possible_start + timedelta(hours=activity['duration'])
            if possible_end <= end_datetime:
                possible_start_times.append((possible_start, possible_end))



        problem.addVariable(activity['name'], possible_start_times)
        
    # Custom constraint to ensure no overlapping activities
    def no_overlap(time1, time2):
        start1, end1 = time1
        start2, end2 = time2
        return end1 <= start2 or start1 >= end2

    # Apply the no_overlap constraint to all pairs of activities
    for activity1 in activities:
        for activity2 in activities:
            if activity1 != activity2:
                problem.addConstraint(no_overlap, (activity1['name'], activity2['name']))

    # Weather constraints for each activity
    def weather_constraint(activity_time, activity, weather_dict):
        activity_start, activity_end = activity_time
        while activity_start < activity_end:
            weather_info = weather_dict.get(activity_start)
            if weather_info is not None:
                # Ensure we are dealing with single values, not Series
                chance_of_rain = weather_info['chance_of_rain']
                if isinstance(chance_of_rain, pd.Series):
                    chance_of_rain = chance_of_rain.iloc[0]  # Handle Series
                elif isinstance(chance_of_rain, pd.DataFrame):
                    chance_of_rain = chance_of_rain.iloc[0, 0]  # Handle DataFrame
                # Now chance_of_rain should be a single value (int or float)
                if not weather_condition_check(chance_of_rain, activity['weather']):
                    return False
            activity_start += timedelta(hours=1)
        return True

    for activity in activities:
        problem.addConstraint(FunctionConstraint(lambda time, act=activity: weather_constraint(time, act, weather_dict)), [activity['name']])

    # Function to calculate average weather data
    def calculate_average_weather(activity_start, activity_duration, weather_dict):
        activity_end = activity_start + timedelta(hours=activity_duration)
        temp_sum = 0
        rain_chance_sum = 0
        count = 0

        while activity_start < activity_end:
            # Find the nearest hour for weather data
            nearest_hour = activity_start.replace(minute=0, second=0, microsecond=0)
            if activity_start.minute >= 30:  # Round up if past 30 minutes
                nearest_hour += timedelta(hours=1)

            weather_info = weather_dict.get(nearest_hour)
            if weather_info is not None:  # Check if weather_info is not None
                temp_sum += weather_info['temp_c']
                rain_chance_sum += int(weather_info['chance_of_rain'])
                count += 1
            activity_start += timedelta(hours=1)

        if count > 0:
            avg_temp = temp_sum / count
            avg_rain_chance = rain_chance_sum / count
        else:
            avg_temp = None
            avg_rain_chance = None

        return avg_temp, avg_rain_chance
    
    # Solve the problem
    solution = problem.getSolution()

    if solution is None:
        return "No feasible schedule found."

    # Convert solution to a more readable format and calculate average weather data
    schedule = {}
    for activity in activities:
        start_time, end_time = solution[activity['name']]
        avg_temp, avg_rain_chance = calculate_average_weather(start_time, activity['duration'], weather_dict)
        schedule[activity['name']] = {
            'start': start_time, 
            'end': end_time, 
            'average_temperature': avg_temp, 
            'average_chance_of_rain': avg_rain_chance
        }

    return schedule

def add_activity_input(key):
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_name = st.text_input("Activity Name", key=f"activity_{key}")
        with col2:
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=12.0, step=0.5, key=f"duration_{key}")
        with col3:
            # Updated weather preferences with multiselect
            weather_preference = st.multiselect("Weather Preference (Select in order of preference)", 
                                                ["Sunny", "Cloudy", "Rainy"], 
                                                key=f"weather_{key}")
    return {"name": activity_name, "duration": duration, "weather": weather_preference}

def plot_activity_timeline(schedule, planning_day):
    fig, ax = plt.subplots(figsize=(10, 3))

    # Generate distinct colors for each activity
    colors = list(mcolors.TABLEAU_COLORS.values())
    color_idx = 0

    for activity, details in schedule.items():
        start = details['start']
        end = details['end']
        ax.plot([start, end], [1, 1], color=colors[color_idx], linewidth=6, label=activity)
        color_idx = (color_idx + 1) % len(colors)

    ax.set_yticks([])
    ax.set_xlabel('Time')
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
    plt.xticks(rotation=45)
    plt.title(f'Activity Timeline for {planning_day.strftime("%Y-%m-%d")}')
    plt.grid(True)
    plt.legend()

    return fig


def user_interface():
    st.title("Activity Scheduler Using Weather Constraints")
    st.subheader("Enter Activities")
    activities = []
    activity_names = set()
    activity_count = st.number_input("How many activities do you want to schedule?", min_value=1, max_value=10, step=1)

    valid_input = True

    for i in range(activity_count):
        activity = add_activity_input(i)
        if not activity['name']:
            st.error("Activity name cannot be blank.")
            valid_input = False
        if activity['name'] in activity_names:
            st.error(f"Activity name '{activity['name']}' is already used. Please use a unique name.")
            valid_input = False
        activity_names.add(activity['name'])
        activities.append(activity)

    st.subheader("Planning Day and Time")
    planning_day = st.date_input("Select the Day for Planning", min_value=date.today())
    start_time = st.time_input("Start Time", key="start_time")
    end_time = st.time_input("End Time", key="end_time")

    # Check for valid time inputs
    if start_time >= end_time:
        st.error("Start time cannot be after end time.")
        valid_input = False
    if planning_day > date.today() + timedelta(days=2):
        st.error("Date chosen must be within the next 3 days.")
        valid_input = False

    if st.button("Submit") and valid_input:
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
                avg_temp = wcsp_schedule[activity]['average_temperature']
                avg_rain_chance = wcsp_schedule[activity]['average_chance_of_rain']
                st.write(f"{activity}: Start at {start.strftime('%Y-%m-%d %H:%M')}, End by {end.strftime('%Y-%m-%d %H:%M')}, Average Temperature: {avg_temp}°C, Chance of Rain: {avg_rain_chance}%")

            # Plot and display the activity timeline
            fig = plot_activity_timeline(wcsp_schedule, planning_day)
            st.pyplot(fig)

# Main Function
def main():
    user_interface()

if __name__ == "__main__":
    main()

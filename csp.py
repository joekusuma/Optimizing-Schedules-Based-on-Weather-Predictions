# Library Imports
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import networkx as nx
import requests
from datetime import datetime, timedelta, date
from constraint import Problem, AllDifferentConstraint, FunctionConstraint, BacktrackingSolver
import seaborn as sns
import logging
import time
import math

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

def add_activity_input(activity_id):
    unique_key = lambda field: f"{field}_{activity_id}"  # Unique key generator

    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_name = st.text_input("Activity Name", key=unique_key("activity_name"))
        with col2:
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=12.0, step=0.5, key=unique_key("duration"))
        with col3:
            weather_preference = st.selectbox("Preferred Weather", ["Sunny", "Cloudy", "Rainy"], key=f"weather_{activity_id}")
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

def weather_constraint(start_time, duration, preferences, weather_dict):
    for hour_offset in range(int(duration)):
        hour = start_time + timedelta(hours=hour_offset)
        weather_data = weather_dict.get(hour)
        if weather_data:
            chance_of_rain = weather_data['chance_of_rain']
            if not weather_condition_check(chance_of_rain, preferences):
                return False
    return True

def calculate_average_weather(activity_start, activity_duration, weather_dict):
    activity_end = activity_start + timedelta(hours=activity_duration)
    temp_sum = 0
    rain_chance_sum = 0
    count = 0

    while activity_start < activity_end:
        nearest_hour = activity_start.replace(minute=0, second=0, microsecond=0)
        if activity_start.minute >= 30:
            nearest_hour += timedelta(hours=1)

        weather_info = weather_dict.get(nearest_hour)
        if weather_info is not None:
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

def solve_csp(activities, weather_data, start_datetime, end_datetime):
    estart_time = time.time()

    problem = Problem(BacktrackingSolver())

    # Convert weather data to a dictionary for easy access
    weather_dict = {pd.to_datetime(row['datetime']): row for index, row in weather_data.iterrows()}

    # Debugging: Print activities to check input
    print("Activities:", activities)

    # Add variables for each activity (activity start time)
    for activity in activities:
        possible_start_times = []
        # Ensure duration is correctly formatted (as an integer)
        duration = int(activity['duration'] * 2)  # Convert hours to half-hour increments

        # Calculate possible start times
        for hour in range(int((end_datetime - start_datetime).total_seconds() // 1800) - duration):
            possible_start = start_datetime + timedelta(minutes=hour * 60)
            possible_end = possible_start + timedelta(minutes=duration * 60)
            if possible_end <= end_datetime:
                possible_start_times.append(possible_start)

        # Ensure the variable name is unique and a string
        problem.addVariable(str(activity['name']), possible_start_times)

    # Apply the no_overlap constraint to all pairs of activities
    def no_overlap(start1, start2, dur1, dur2):
        end1 = start1 + timedelta(hours=dur1)
        end2 = start2 + timedelta(hours=dur2)

        # Check if the first activity ends before the second starts or vice versa
        return end1 <= start2 or end2 <= start1

    for i in range(len(activities)):
        for j in range(i + 1, len(activities)):
            problem.addConstraint(lambda start1, start2, dur1=activities[i]['duration'], dur2=activities[j]['duration']: 
                                  no_overlap(start1, start2, dur1, dur2), 
                                  [str(activities[i]['name']), str(activities[j]['name'])])

    # Weather constraints for each activity
    for activity in activities:
        problem.addConstraint(FunctionConstraint(lambda start_time, dur=activity['duration'], prefs=activity['weather']: 
                                                weather_constraint(start_time, dur, prefs, weather_dict)), 
                                                [str(activity['name'])])

    # Solve the problem
    solution = problem.getSolution()

    if solution is None:
        return "No feasible schedule found."

    # Convert solution to a readable format
    schedule = {}
    for activity_name, start_time in solution.items():
        activity = next(act for act in activities if act['name'] == activity_name)
        end_time = start_time + timedelta(minutes=activity['duration'] * 60)
        avg_temp, avg_rain_chance = calculate_average_weather(start_time, activity['duration'], weather_dict)
        schedule[activity_name] = {
            'start': start_time, 
            'end': end_time, 
            'average_temperature': avg_temp, 
            'average_chance_of_rain': avg_rain_chance
        }
    eend_time = time.time()
    # Calculate execution time
    execution_time = eend_time - estart_time
    print(f"Execution Time: {execution_time} seconds")
    return schedule, execution_time

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
    st.title("Activity Scheduler Using Weather Constraints and CSP")
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
    if start_time > end_time:
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
        csp_schedule, execution_time = solve_csp(activities, weather_data, start_datetime, end_datetime)  # Modified to capture execution time

        if isinstance(csp_schedule, str):
            st.write(csp_schedule)
        else:
            st.write("Optimized Schedule:")
            for activity in csp_schedule:
                start = csp_schedule[activity]['start']
                end = csp_schedule[activity]['end']
                avg_temp = csp_schedule[activity]['average_temperature']
                if avg_temp is not None:
                    avg_temp = math.ceil(avg_temp)
                avg_rain_chance = csp_schedule[activity]['average_chance_of_rain']
                if avg_rain_chance is not None:
                    avg_rain_chance = math.ceil(avg_rain_chance)
                st.write(f"{activity}: Start at {start.strftime('%Y-%m-%d %H:%M')}, End by {end.strftime('%Y-%m-%d %H:%M')}, Average Temperature: {avg_temp}°C, Chance of Rain: {avg_rain_chance}%")

            # Display execution time
            st.write(f"Execution Time: {execution_time:.2f} seconds")  # Display execution time

            # Plot and display the activity timeline
            fig = plot_activity_timeline(csp_schedule, planning_day)
            st.pyplot(fig)

# Main Function
def main():
    user_interface()


if __name__ == "__main__":
    main()
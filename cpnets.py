import streamlit as st
from itertools import permutations
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors
import pandas as pd
import requests
import time
import math

# Constants and Global Variables
api_key = ""
location = "London"

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

# Streamlit User Interface for Activity Input
def add_activity_input(key):
    with st.container():
        col1, col2, col3 = st.columns(3)
        with col1:
            activity_name = st.text_input("Activity Name", key=f"activity_{key}")
        with col2:
            duration = st.number_input("Duration (in hours)", min_value=0.5, max_value=12.0, step=0.5, key=f"duration_{key}")
        with col3:
            weather_preference = st.selectbox("Preferred Weather", ["Sunny", "Cloudy", "Rainy"], key=f"weather_{key}")
    return {"name": activity_name, "duration": duration, "weather": weather_preference}

def interpret_weather_score(precip_mm, preferred_weather):
    # Example interpretation: lower score if chance of rain is high but preference is sunny
    if preferred_weather == "Sunny":
        return 3 if precip_mm == 0 else 1
    elif preferred_weather == "Cloudy":
        return 2
    else:  # Rainy
        return 1 if precip_mm > 0.30 else 3

def adjust_preferences_based_on_weather(activity_name, start_time, duration, preferred_weather, weather_data):
    end_time = start_time + timedelta(hours=duration)
    average_weather_score = 0
    count = 0

    # Calculate average weather preference score for the activity duration
    while start_time < end_time:
        hour_weather = weather_data.get(start_time.hour)
        if hour_weather is not None and not hour_weather.empty:
            # Example: Score based on chance of rain
            precip_mm = hour_weather['precip_mm']
            # Use .iloc[0] if 'precip_mm' is a Series
            if isinstance(precip_mm, pd.Series):
                precip_mm = precip_mm.iloc[0]
            weather_score = interpret_weather_score(precip_mm, preferred_weather)
            average_weather_score += weather_score
            count += 1
        start_time += timedelta(hours=1)

    if count > 0:
        return average_weather_score / count
    return {"Sunny": 3, "Cloudy": 2, "Rainy": 1}[preferred_weather]  # Default to initial preference if no weather data

# Function implementing CP-Net logic
def CPNet(activities, weather_data, start_datetime, end_datetime):
    estart_time = time.time()
    preferences = {}
    conditions = {}

    for activity in activities:
        activity_name = activity["name"]
        activity_duration = activity["duration"]
        activity_weather = activity["weather"]

        # Initial preference based on user input
        initial_pref = {"Sunny": 3, "Cloudy": 2, "Rainy": 1}[activity_weather]

        # Adjust preferences based on weather data
        adjusted_pref = adjust_preferences_based_on_weather(activity_name, start_datetime, activity_duration, activity_weather, weather_data)

        preferences[activity_name] = adjusted_pref
        conditions[activity_name] = {"duration": activity_duration, "time_range": (start_datetime, end_datetime)}

    # Generate all possible permutations of activities
    activity_names = [activity["name"] for activity in activities]
    all_permutations = list(permutations(activity_names))
    
    # Find the best schedule based on preferences and conditions
    best_schedule = None
    best_score = -float("inf")

    for perm in all_permutations:
        current_schedule = []
        current_time = start_datetime
        total_score = 0

        for activity_name in perm:
            activity_duration = conditions[activity_name]["duration"]
            activity_end_time = current_time + timedelta(hours=activity_duration)

            if activity_end_time <= conditions[activity_name]["time_range"][1]:
                current_schedule.append({"name": activity_name, "start_time": current_time, "end_time": activity_end_time})
                current_time = activity_end_time
                total_score += preferences[activity_name]

        if total_score > best_score:
            best_score = total_score
            best_schedule = current_schedule

        if best_schedule:
            # Calculate average weather data for each activity in the schedule
            for activity in best_schedule:
                start_time = activity['start_time']
                duration = conditions[activity['name']]['duration']
                avg_temp, avg_rain_chance = calculate_average_weather(start_time, duration, weather_data)
                activity['average_temperature'] = avg_temp
                activity['average_precip_mm'] = avg_rain_chance

    eend_time = time.time()
    # Calculate execution time
    execution_time = eend_time - estart_time
    print(f"Execution Time: {execution_time} seconds")
    return best_schedule, execution_time

def calculate_average_weather(activity_start, activity_duration, weather_dict):
    activity_end = activity_start + timedelta(hours=activity_duration)
    temp_sum = 0
    rain_chance_sum = 0
    count = 0

    while activity_start < activity_end:
        nearest_hour = activity_start.replace(minute=0, second=0, microsecond=0)
        if activity_start.minute >= 30:
            nearest_hour += timedelta(hours=1)

        weather_info = weather_dict.get(nearest_hour.hour)
        if weather_info is not None:
            temp_sum += weather_info['temp_c']

            # Debugging: Print the retrieved weather info
            print(f"Weather info for hour {nearest_hour.hour}: {weather_info}")

            # Extract and process 'precip_mm'
            precip_mm = weather_info['precip_mm']
            if isinstance(precip_mm, str) and precip_mm.endswith('%'):
                precip_mm = int(precip_mm.rstrip('%'))
            elif isinstance(precip_mm, pd.Series):
                precip_mm = precip_mm.iloc[0]
            
            rain_chance_sum += precip_mm
            count += 1
        else:
            print(f"No weather data for hour: {nearest_hour.hour}")
        activity_start += timedelta(hours=1)

    if count > 0:
        avg_temp = temp_sum / count
        avg_rain_chance = rain_chance_sum / count
    else:
        avg_temp = None
        avg_rain_chance = None

    return avg_temp, avg_rain_chance

# Function for plotting the activity timeline
def plot_activity_timeline(schedule, planning_day):
    fig, ax = plt.subplots(figsize=(10, 3))
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

# Streamlit UI for scheduling activities
def user_interface():
    st.title("Activity Scheduler Using CP-Nets and Weather Preferences")
    st.subheader("Enter Activities")
    activities = []
    activity_names = set()
    valid_input = True

    activity_count = st.number_input("How many activities do you want to schedule?", min_value=1, max_value=10, step=1)

    for i in range(activity_count):
        activity = add_activity_input(i)
        if not activity['name']:
            st.error("Activity name cannot be blank.")
            valid_input = False
        elif activity['name'] in activity_names:
            st.error(f"Activity name '{activity['name']}' is already used. Please use a unique name.")
            valid_input = False
        else:
            activity_names.add(activity['name'])
            activities.append(activity)

    st.subheader("Planning Day and Time")
    planning_day = st.date_input("Select the Day for Planning", min_value=datetime.today())
    start_time = st.time_input("Start Time", key="start_time")
    end_time = st.time_input("End Time", key="end_time")

    if start_time >= end_time:
        st.error("Start time cannot be after end time.")
        valid_input = False

    if st.button("Submit") and valid_input:
        start_datetime = datetime.combine(planning_day, start_time)
        end_datetime = datetime.combine(planning_day, end_time)

        # Fetch weather data
        weather_data = fetch_weather_data(api_key, location, planning_day.strftime("%Y-%m-%d"))
        hourly_weather_data = {pd.to_datetime(row['time']).hour: row for index, row in weather_data.iterrows()}

        best_schedule, execution_time = CPNet(activities, hourly_weather_data, start_datetime, end_datetime)

        if best_schedule:
            st.write("Optimized Schedule:")
            schedule_dict = {}
            for activity in best_schedule:
                start = activity['start_time']
                end = activity['end_time']
                avg_temp = activity.get('average_temperature')
                avg_rain_chance = activity.get('average_precip_mm')
                st.write(f"{activity['name']} - Start: {start}, End: {end}, Avg Temp: {round(avg_temp, 1)}°C, Precipitation: {round(avg_rain_chance, 2)}mm")
                schedule_dict[activity['name']] = {'start': start, 'end': end}

            fig = plot_activity_timeline(schedule_dict, planning_day)
            # Display execution time
            st.write(f"Execution Time: {execution_time:.2f} seconds")  # Display execution time

            st.pyplot(fig)
        else:
            st.write("No feasible schedule found.")

def main():
    user_interface()

if __name__ == "__main__":
    main()
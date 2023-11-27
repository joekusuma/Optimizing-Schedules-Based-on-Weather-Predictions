import streamlit as st
from itertools import permutations
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.colors as mcolors

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

# Function implementing CP-Net logic
def CPNet(activities, start_datetime, end_datetime):
    preferences = {}
    conditions = {}

    for activity in activities:
        activity_name = activity["name"]
        activity_duration = activity["duration"]
        activity_weather = activity["weather"]

        preferences[activity_name] = {"Sunny": 3, "Cloudy": 2, "Rainy": 1}[activity_weather]
        conditions[activity_name] = {"duration": activity_duration, "time_range": (start_datetime, end_datetime)}

    activity_names = [activity["name"] for activity in activities]
    all_permutations = list(permutations(activity_names))

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

    return best_schedule

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

        best_schedule = CPNet(activities, start_datetime, end_datetime)

        if best_schedule:
            st.write("Optimized Schedule:")
            schedule_dict = {activity['name']: {'start': activity['start_time'], 'end': activity['end_time']} for activity in best_schedule}
            for activity in best_schedule:
                st.write(f"{activity['name']} - Start: {activity['start_time']}, End: {activity['end_time']}")

            fig = plot_activity_timeline(schedule_dict, planning_day)
            st.pyplot(fig)
        else:
            st.write("No feasible schedule found.")
            
def main():
    user_interface()

if __name__ == "__main__":
    main()


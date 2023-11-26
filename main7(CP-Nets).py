import streamlit as st
from itertools import permutations
from datetime import datetime, timedelta

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

# Streamlit UI for scheduling activities
def user_interface():
    st.title("Activity Scheduler Using CP-Nets and Weather Preferences")
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
        
        start_datetime = datetime.combine(planning_day, start_time)
        end_datetime = datetime.combine(planning_day, end_time)

        # Define preferences and conditions
        preferences = {}
        conditions = {}

        for activity in activities:
            activity_name = activity["name"]
            activity_duration = activity["duration"]
            activity_weather = activity["weather"]
            
            # Assign preference values (higher values indicate higher preference)
            if activity_weather == "Sunny":
                preferences[activity_name] = 3
            elif activity_weather == "Cloudy":
                preferences[activity_name] = 2
            elif activity_weather == "Rainy":
                preferences[activity_name] = 1
            
            # Define conditions based on duration and time constraints
            conditions[activity_name] = {
                "duration": activity_duration,
                "time_range": (start_datetime, end_datetime)
            }

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
                
                # Check if the condition (duration and time range) is satisfied
                if (
                    conditions[activity_name]["duration"] <= activity_duration
                    and conditions[activity_name]["time_range"][1] >= current_time + timedelta(hours=activity_duration)
                ):
                    current_schedule.append({
                        "name": activity_name,
                        "start_time": current_time,
                        "end_time": current_time + timedelta(hours=activity_duration),
                    })
                    current_time += timedelta(hours=activity_duration)
                    total_score += preferences[activity_name]
            
            if total_score > best_score:
                best_score = total_score
                best_schedule = current_schedule

        # Print the best schedule
        if best_schedule:
            st.write("Optimized Schedule:")
            for activity in best_schedule:
                st.write(f"{activity['name']} - Start: {activity['start_time']}, End: {activity['end_time']}")
        else:
            st.write("No feasible schedule found.")

# Main Function
def main():
    user_interface()

if __name__ == "__main__":
    main()

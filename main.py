import streamlit as st
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import networkx as nx
from constraint import Problem, AllDifferentConstraint, FunctionConstraint
import requests

api_key = "28c300a25e5245d6ba3223640231511"
location = "Los Angeles"

end_date = datetime.now()
start_date = end_date - timedelta(days=10)

start_date_str = start_date.strftime("%Y-%m-%d")
end_date_str = end_date.strftime("%Y-%m-%d")

url = f"http://api.weatherapi.com/v1/history.json?key={api_key}&q={location}&dt={start_date_str}&end_dt={end_date_str}"

response = requests.get(url)
data = response.json()

df_weather = pd.DataFrame()
for forecastday in data['forecast']['forecastday']:
    date = forecastday['date']
    for hour in forecastday['hour']:
        df_weather = df_weather.append({
            'date': date,
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
st.write(df_weather)

def create_wcsp_with_weather_and_activities(weather_data, activities):
    wcsp_problem = Problem()
    for index, row in weather_data.iterrows():
        variable = index
        wcsp_problem.addVariable(variable, range(24))
        wcsp_problem.addConstraint(
            FunctionConstraint(
                lambda time_slot, temp_c=row['temp_c'], wind_kph=row['wind_kph'],
                humidity=row['humidity'], chance_of_rain=row['chance_of_rain']:
                5 <= temp_c <= 30 and 0 <= wind_kph <= 15 and 30 <= humidity <= 70 and chance_of_rain < 30
            ),
            (variable,)
        )
    for activity in activities:
        wcsp_problem.addConstraint(
            FunctionConstraint(
                lambda time_slot, activity=activity: activity['start'] <= time_slot <= activity['end']
            ),
            tuple(range(len(weather_data)))
        )
    wcsp_problem.addConstraint(AllDifferentConstraint())
    return wcsp_problem, list(wcsp_problem._variables)

def visualize_wcsp(problem, variables, title="WCSP Graph"):
    st.write(title)
    G = nx.DiGraph()
    G.add_nodes_from(variables)
    for constraint in problem._constraints:
        variables_in_constraint = constraint[0]
        if hasattr(constraint[1], '__call__'): 
            for edge in zip(variables_in_constraint, variables_in_constraint[1:]):
                G.add_edge(*edge)
    pos = nx.spring_layout(G)
    fig, ax = plt.subplots(figsize=(10, 6))
    nx.draw(G, pos, with_labels=True, font_weight='bold', node_color='skyblue', node_size=800, arrowsize=20, edge_color='gray', ax=ax)
    plt.title(title)
    plt.axis("off")
    st.pyplot(fig)
    st.write("Variables:", variables)

def main():
    st.title("Weather Optimization Dashboard")
    activities = []
    num_activities = st.number_input("Number of Activities", min_value=0, step=1)
    for i in range(num_activities):
        duration = st.slider(f"Activity {i+1} Duration (Hours)", 1, 24, 2)
        weather_condition = st.selectbox(f"Activity {i+1} Weather Condition", ['Sunny', 'Cloudy', 'Rainy'])
        activities.append({'duration': duration, 'weather_condition': weather_condition})
    wcsp_problem, variable_list = create_wcsp_with_weather_and_activities(df_weather, activities)
    visualize_wcsp(wcsp_problem, variable_list, title="WCSP Graph with User Activities")
    X = df_weather[['datetime_numeric']]
    y = df_weather['temp_c']
    X_train, X_test, y_train, y_test = train_test_split(X[['datetime_numeric']], y, test_size=0.2, random_state=42)
    model = LinearRegression()
    model.fit(X_train, y_train)
    df_weather['temp_c_predicted'] = model.predict(df_weather[['datetime_numeric']])
    st.line_chart(df_weather.set_index('datetime')['temp_c'], use_container_width=True)

if __name__ == "__main__":
    main()

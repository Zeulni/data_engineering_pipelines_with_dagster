import streamlit as st
import pandas as pd
import duckdb
import matplotlib.pyplot as plt
import os
import random
import time


# Function to inject JavaScript for auto-refresh
def auto_refresh(interval=1):  # Interval in seconds
    # Using Streamlit's components to inject custom JavaScript for auto-refresh (page reload of localhost does not trigger streamlit script within container. This reload is just to get the updated from the local streamlit app, which is also refreshed every 1 second.)
    st.html(
        f"""
        <script>
        setTimeout(function() {{
            window.location.reload();
        }}, {interval*1000});
        console.log("Page will refresh every {interval} seconds.");
        </script>
        """,
    )


def load_data():
    conn = duckdb.connect(database="data/dagster_tutorial.duckdb", read_only=True)
    df_top_words = pd.read_sql("SELECT * FROM top_words", conn)
    conn.close()
    return df_top_words


def plot_top_words(df_top_words, placeholder):
    # Create a new figure for each plot to avoid interference
    plt.figure(figsize=(10, 6))
    # Generate a random color for the bars
    random_color = (random.random(), random.random(), random.random())
    # Create the bar plot
    plt.bar(df_top_words["word"], df_top_words["count"], color=random_color)
    plt.xlabel("Words")
    plt.ylabel("Count")
    plt.xticks(rotation=45, ha="right")
    plt.title("Top 25 Words in Hacker News Titles")
    # Display the plot in the specified Streamlit container
    placeholder.pyplot(plt)
    plt.close()  # Close the figure to free up memory


def check_for_updates():
    signal_file_path = "frontend/streamlit_reload_signal.txt"
    if os.path.exists(signal_file_path):
        with open(signal_file_path, "r") as file:
            timestamp = file.read().strip()
            return timestamp
    return None


# df = load_data()
# plot_top_words(df)

# last_update = check_for_updates()
# print(f"Last update: {last_update}")


# # Continuously check for updates and rerun the app if an update is detected
# while True:
#     time.sleep(1)
#     current_update = check_for_updates()
#     if current_update != last_update:
#         st.experimental_rerun()


def main():
    auto_refresh(interval=1)  # Refresh every second
    plot_container = st.empty()  # Create an empty container for the plot

    if "last_update" not in st.session_state:
        st.session_state["last_update"] = check_for_updates()

    while True:
        time.sleep(1)  # Sleep to simulate a time delay for demonstration purposes
        current_update = check_for_updates()
        if current_update != st.session_state["last_update"]:
            st.session_state["last_update"] = current_update
            df = load_data()
            plot_top_words(
                df, plot_container
            )  # Pass the container to the plotting function


if __name__ == "__main__":
    main()

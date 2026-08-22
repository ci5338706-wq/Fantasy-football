import streamlit as st

st.set_page_config(page_title="Holland Family Fantasy", page_icon="🏈", layout="centered")

st.title("🏈 Holland Family Fantasy")
st.write("App is working!")

st.header("Teams")
teams = ["Team 1", "Team 2", "Team 3", "Team 4", "Team 5", 
         "Team 6", "Team 7", "Team 8", "Team 9", "Team 10"]

for t in teams:
    st.write(t)

st.success("If you can see this, the app is loading correctly.")

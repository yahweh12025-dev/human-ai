# SWARM GUI BLUEPRINT
# Goal: A centralized dashboard to monitor agent activity, logs, and prompt the swarm.

import streamlit as st
import os
import subprocess

st.set_page_config(page_title="Human AI Swarm Control", layout="wide")

st.title("🧬 Human AI Swarm Dashboard")

# Sidebar for Agent Status
st.sidebar.header("Agent Status")
agents = ["Researcher", "Builder", "Prompter", "Navigator", "Critic", "Planner"]
for agent in agents:
    st.sidebar.success(f"{agent}: Active")

# Main Interaction Area
st.subheader("Swarm Command Center")
user_input = st.text_input("Prompt the Swarm:", placeholder="e.g., Research X and implement Y...")

if st.button("Execute"):
    st.info(f"Dispatching request: {user_input}")
    # Logic to call the Comm-Bridge and trigger the Planner
    st.text_area("Live Logs", value="Initiating Planner... \nResearcher scanning... \nBuilder implementing...", height=300)

# History & Vault Access
st.subheader("System State")
col1, col2 = st.columns(2)
with col1:
    if st.button("View Error Queue"):
        st.write("Loading /home/ubuntu/human-ai/error_queue.md...")
with col2:
    if st.button("Sync Cloud Vault"):
        st.write("Synchronizing with Supabase...")

st.markdown("---")
st.caption("Connected to OpenClaw via SSH Terminal. All actions pushed to GitHub.")

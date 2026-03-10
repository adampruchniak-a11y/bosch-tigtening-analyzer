import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.title("Bosch Tightening Analyzer")

uploaded_file = st.file_uploader("Wrzuć plik z Boscha", type=["txt","json"])

if uploaded_file:

    data = json.load(uploaded_file)

    st.write("Program:", data.get("prg name"))
    st.write("Cycle:", data.get("cycle"))
    st.write("Result:", data.get("result"))

    steps = data.get("tightening steps", [])

    for step in steps:

        st.subheader(step.get("name"))

        graph = step.get("graph", {})

        angle = graph.get("angle values", [])
        torque = graph.get("torque values", [])

        if angle and torque:

            n = min(len(angle), len(torque))

            fig, ax = plt.subplots()

            ax.plot(angle[:n], torque[:n])

            ax.set_xlabel("Angle")
            ax.set_ylabel("Torque")

            st.pyplot(fig)

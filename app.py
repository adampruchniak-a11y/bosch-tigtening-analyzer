import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Bosch Tightening Analyzer", layout="wide")

st.title("Bosch Tightening Analyzer")
st.write("Wgraj plik JSON/TXT z Boscha i zobacz analizę kroków dokręcania.")

uploaded_file = st.file_uploader("Wrzuć plik z Boscha", type=["txt", "json"])

def extract_step_features(step):
    graph = step.get("graph", {})
    angle = graph.get("angle values", [])
    torque = graph.get("torque values", [])
    gradient = graph.get("gradient values", [])

    return {
        "step_name": step.get("name"),
        "step_result": step.get("result"),
        "points_angle": len(angle),
        "points_torque": len(torque),
        "points_gradient": len(gradient),
        "max_angle": max(angle) if angle else None,
        "max_torque": max(torque) if torque else None,
        "max_gradient": max(gradient) if gradient else None,
    }

if uploaded_file is not None:
    try:
        data = json.load(uploaded_file)

        st.subheader("Informacje o cyklu")
        col1, col2, col3 = st.columns(3)
        col1.metric("Program", data.get("prg name"))
        col2.metric("Cycle", data.get("cycle"))
        col3.metric("Result", data.get("result"))

        st.write("**Data:**", data.get("date"))
        st.write("**ID code:**", data.get("id code"))

        steps = data.get("tightening steps", [])
        st.write("**Liczba kroków:**", len(steps))

        if not steps:
            st.warning("Brak kroków dokręcania w pliku.")
        else:
            st.subheader("Podsumowanie kroków")
            features = [extract_step_features(step) for step in steps]
            df = pd.DataFrame(features)
            st.dataframe(df, use_container_width=True)

            step_names = [step.get("name", f"Krok {i+1}") for i, step in enumerate(steps)]
            selected_step_name = st.selectbox("Wybierz krok do analizy", step_names)

            selected_step = next(
                (step for step in steps if step.get("name") == selected_step_name),
                steps[0]
            )

            graph = selected_step.get("graph", {})
            angle = graph.get("angle values", [])
            torque = graph.get("torque values", [])
            gradient = graph.get("gradient values", [])
            time_vals = graph.get("time values", [])

            st.subheader(f"Wykresy dla kroku: {selected_step_name}")

            col_left, col_right = st.columns(2)

            with col_left:
                if angle and torque:
                    n = min(len(angle), len(torque))
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.plot(angle[:n], torque[:n])
                    ax.set_xlabel("Kąt [deg]")
                    ax.set_ylabel("Moment")
                    ax.set_title("Moment vs Kąt")
                    ax.grid(True)
                    st.pyplot(fig)
                else:
                    st.info("Brak danych do wykresu Moment vs Kąt")

            with col_right:
                if angle and gradient:
                    n = min(len(angle), len(gradient))
                    fig, ax = plt.subplots(figsize=(8, 4))
                    ax.plot(angle[:n], gradient[:n])
                    ax.set_xlabel("Kąt [deg]")
                    ax.set_ylabel("Gradient")
                    ax.set_title("Gradient vs Kąt")
                    ax.grid(True)
                    st.pyplot(fig)
                else:
                    st.info("Brak danych do wykresu Gradient vs Kąt")

            if time_vals and torque:
                n = min(len(time_vals), len(torque))
                fig, ax = plt.subplots(figsize=(10, 4))
                ax.plot(time_vals[:n], torque[:n])
                ax.set_xlabel("Czas")
                ax.set_ylabel("Moment")
                ax.set_title("Moment vs Czas")
                ax.grid(True)
                st.pyplot(fig)

    except Exception as e:
        st.error(f"Błąd podczas wczytywania pliku: {e}")

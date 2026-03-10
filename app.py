import json
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Bosch Tightening Analyzer", layout="wide")

st.title("Bosch Tightening Analyzer")
st.write("Wgraj jeden lub wiele plików JSON/TXT z Boscha i zobacz analizę kroków dokręcania.")

uploaded_files = st.file_uploader(
    "Wrzuć pliki z Boscha",
    type=["txt", "json"],
    accept_multiple_files=True
)

def extract_step_features(step, file_name, cycle, program, overall_result):
    graph = step.get("graph", {})
    angle = graph.get("angle values", [])
    torque = graph.get("torque values", [])
    gradient = graph.get("gradient values", [])
    time_vals = graph.get("time values", [])

    return {
        "file_name": file_name,
        "program": program,
        "cycle": cycle,
        "overall_result": overall_result,
        "step_name": step.get("name"),
        "step_result": step.get("result"),
        "points_angle": len(angle),
        "points_torque": len(torque),
        "points_gradient": len(gradient),
        "points_time": len(time_vals),
        "max_angle": max(angle) if angle else None,
        "max_torque": max(torque) if torque else None,
        "max_gradient": max(gradient) if gradient else None,
        "final_angle": angle[-1] if angle else None,
        "final_torque": torque[-1] if torque else None,
    }

all_rows = []
all_data = []

if uploaded_files:
    for uploaded_file in uploaded_files:
        try:
            data = json.load(uploaded_file)

            file_name = uploaded_file.name
            program = data.get("prg name")
            cycle = data.get("cycle")
            overall_result = data.get("result")
            steps = data.get("tightening steps", [])

            all_data.append({
                "file_name": file_name,
                "data": data
            })

            for step in steps:
                row = extract_step_features(
                    step=step,
                    file_name=file_name,
                    cycle=cycle,
                    program=program,
                    overall_result=overall_result
                )
                all_rows.append(row)

        except Exception as e:
            st.error(f"Błąd w pliku {uploaded_file.name}: {e}")

    if all_rows:
        df = pd.DataFrame(all_rows)

        st.subheader("Podsumowanie wszystkich plików")
        col1, col2, col3 = st.columns(3)
        col1.metric("Liczba plików", len(uploaded_files))
        col2.metric("Liczba rekordów kroków", len(df))
        col3.metric("Liczba cykli OK", int((df["overall_result"] == "OK").sum()) if "overall_result" in df.columns else 0)

        st.dataframe(df, use_container_width=True)

        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "Pobierz CSV z analizą",
            data=csv,
            file_name="bosch_multi_analysis.csv",
            mime="text/csv"
        )

        st.subheader("Filtrowanie")
        file_list = ["Wszystkie"] + sorted(df["file_name"].dropna().unique().tolist())
        selected_file = st.selectbox("Wybierz plik", file_list)

        filtered_df = df.copy()
        if selected_file != "Wszystkie":
            filtered_df = filtered_df[filtered_df["file_name"] == selected_file]

        step_list = ["Wszystkie"] + sorted(filtered_df["step_name"].dropna().unique().tolist())
        selected_step = st.selectbox("Wybierz krok", step_list)

        if selected_step != "Wszystkie":
            filtered_df = filtered_df[filtered_df["step_name"] == selected_step]

        st.subheader("Tabela po filtrach")
        st.dataframe(filtered_df, use_container_width=True)

        st.subheader("Wykres dla wybranego pliku i kroku")

        if selected_file == "Wszystkie":
            st.info("Najpierw wybierz konkretny plik, aby zobaczyć wykres.")
        elif selected_step == "Wszystkie":
            st.info("Wybierz także konkretny krok, aby zobaczyć wykres.")
        else:
            selected_data_item = next(
                (item for item in all_data if item["file_name"] == selected_file),
                None
            )

            if selected_data_item:
                data = selected_data_item["data"]
                steps = data.get("tightening steps", [])

                selected_step_data = next(
                    (step for step in steps if step.get("name") == selected_step),
                    None
                )

                if selected_step_data:
                    graph = selected_step_data.get("graph", {})
                    angle = graph.get("angle values", [])
                    torque = graph.get("torque values", [])
                    gradient = graph.get("gradient values", [])
                    time_vals = graph.get("time values", [])

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
                else:
                    st.warning("Nie znaleziono wybranego kroku w pliku.")
    else:
        st.warning("Nie udało się wyciągnąć danych z przesłanych plików.")

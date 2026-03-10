import json
from io import BytesIO

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.set_page_config(page_title="Bosch Tightening Analyzer ", layout="wide")

st.title("Bosch Tightening Analyzer ")
st.write("Wgraj jeden lub wiele plików JSON/TXT z Boscha i zobacz analizę kroków dokręcania.")


uploaded_files = st.file_uploader(
    "Wrzuć pliki z Boscha",
    type=["txt", "json"],
    accept_multiple_files=True
)


def extract_step_features(step, file_name, cycle, program, overall_result, date_value, id_code):
    graph = step.get("graph", {})
    angle = graph.get("angle values", [])
    torque = graph.get("torque values", [])
    gradient = graph.get("gradient values", [])
    time_vals = graph.get("time values", [])
    angle_red = graph.get("angleRed values", [])
    torque_red = graph.get("torqueRed values", [])

    return {
        "file_name": file_name,
        "program": program,
        "cycle": cycle,
        "overall_result": overall_result,
        "date": date_value,
        "id_code": id_code,
        "step_name": step.get("name"),
        "step_result": step.get("result"),
        "points_angle": len(angle),
        "points_torque": len(torque),
        "points_gradient": len(gradient),
        "points_time": len(time_vals),
        "points_angle_red": len(angle_red),
        "points_torque_red": len(torque_red),
        "max_angle": max(angle) if angle else None,
        "max_torque": max(torque) if torque else None,
        "max_gradient": max(gradient) if gradient else None,
        "final_angle": angle[-1] if angle else None,
        "final_torque": torque[-1] if torque else None,
        "final_gradient": gradient[-1] if gradient else None,
        "max_angle_red": max(angle_red) if angle_red else None,
        "max_torque_red": max(torque_red) if torque_red else None,
        "final_angle_red": angle_red[-1] if angle_red else None,
        "final_torque_red": torque_red[-1] if torque_red else None,
    }


def create_excel_file(dataframe):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        dataframe.to_excel(writer, index=False, sheet_name="Analiza")
        ws = writer.sheets["Analiza"]

        # Zamrożenie pierwszego wiersza
        ws.freeze_panes = "A2"

        # Filtr na całym zakresie
        ws.auto_filter.ref = ws.dimensions

        # Pogrubienie nagłówków
        for cell in ws[1]:
            cell.font = cell.font.copy(bold=True)

        # Ustawienie szerokości kolumn
        for column_cells in ws.columns:
            max_length = 0
            column_letter = column_cells[0].column_letter

            for cell in column_cells:
                try:
                    value = "" if cell.value is None else str(cell.value)
                    if len(value) > max_length:
                        max_length = len(value)
                except Exception:
                    pass

            adjusted_width = min(max(max_length + 2, 12), 40)
            ws.column_dimensions[column_letter].width = adjusted_width

    output.seek(0)
    return output


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
            date_value = data.get("date")
            id_code = data.get("id code")
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
                    overall_result=overall_result,
                    date_value=date_value,
                    id_code=id_code
                )
                all_rows.append(row)

        except Exception as e:
            st.error(f"Błąd w pliku {uploaded_file.name}: {e}")

    if all_rows:
        df = pd.DataFrame(all_rows)

        st.subheader("Podsumowanie wszystkich plików")

        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Liczba plików", len(uploaded_files))
        col2.metric("Liczba rekordów kroków", len(df))
        col3.metric("Unikalne cykle", df["cycle"].nunique() if "cycle" in df.columns else 0)
        col4.metric(
            "Kroki OK",
            int((df["step_result"] == "OK").sum()) if "step_result" in df.columns else 0
        )

        st.dataframe(df, use_container_width=True)

        # CSV
        csv_data = df.to_csv(index=False, sep=";").encode("utf-8")
        st.download_button(
            "Pobierz CSV z analizą",
            data=csv_data,
            file_name="bosch_multi_analysis.csv - TYLKO NA PRÓBĘ - SŁABO DZIAŁA",
            mime="text/csv"
        )

        # Excel PRO
        excel_file = create_excel_file(df)
        st.download_button(
            "Pobierz Excel (.xlsx)",
            data=excel_file,
            file_name="bosch_multi_analysis.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

        st.subheader("Filtrowanie")

        colf1, colf2, colf3 = st.columns(3)

        with colf1:
            file_list = ["Wszystkie"] + sorted(df["file_name"].dropna().unique().tolist())
            selected_file = st.selectbox("Wybierz plik", file_list)

        filtered_df = df.copy()
        if selected_file != "Wszystkie":
            filtered_df = filtered_df[filtered_df["file_name"] == selected_file]

        with colf2:
            step_list = ["Wszystkie"] + sorted(filtered_df["step_name"].dropna().unique().tolist())
            selected_step = st.selectbox("Wybierz krok", step_list)

        if selected_step != "Wszystkie":
            filtered_df = filtered_df[filtered_df["step_name"] == selected_step]

        with colf3:
            result_list = ["Wszystkie"] + sorted(filtered_df["overall_result"].dropna().unique().tolist())
            selected_result = st.selectbox("Wybierz wynik cyklu", result_list)

        if selected_result != "Wszystkie":
            filtered_df = filtered_df[filtered_df["overall_result"] == selected_result]

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
                    angle_red = graph.get("angleRed values", [])
                    torque_red = graph.get("torqueRed values", [])

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

                    col_left2, col_right2 = st.columns(2)

                    with col_left2:
                        if time_vals and torque:
                            n = min(len(time_vals), len(torque))
                            fig, ax = plt.subplots(figsize=(8, 4))
                            ax.plot(time_vals[:n], torque[:n])
                            ax.set_xlabel("Czas")
                            ax.set_ylabel("Moment")
                            ax.set_title("Moment vs Czas")
                            ax.grid(True)
                            st.pyplot(fig)
                        else:
                            st.info("Brak danych do wykresu Moment vs Czas")

                    with col_right2:
                        if angle_red and torque_red:
                            n = min(len(angle_red), len(torque_red))
                            fig, ax = plt.subplots(figsize=(8, 4))
                            ax.plot(angle_red[:n], torque_red[:n])
                            ax.set_xlabel("KątRed [deg]")
                            ax.set_ylabel("MomentRed")
                            ax.set_title("MomentRed vs KątRed")
                            ax.grid(True)
                            st.pyplot(fig)
                        else:
                            st.info("Brak danych do wykresu MomentRed vs KątRed")

                    st.subheader("Funkcje dokręcania dla wybranego kroku")
                    funcs = selected_step_data.get("tightening functions", [])

                    if funcs:
                        funcs_rows = []
                        for func in funcs:
                            funcs_rows.append({
                                "name": func.get("name"),
                                "nom": func.get("nom"),
                                "act": func.get("act"),
                                "unit": func.get("unit"),
                                "result": func.get("result")
                            })

                        funcs_df = pd.DataFrame(funcs_rows)
                        st.dataframe(funcs_df, use_container_width=True)
                    else:
                        st.info("Brak tightening functions dla tego kroku.")

                else:
                    st.warning("Nie znaleziono wybranego kroku w pliku.")
    else:
        st.warning("Nie udało się wyciągnąć danych z przesłanych plików.")
else:
    st.info("Wgraj pliki, aby rozpocząć analizę.")

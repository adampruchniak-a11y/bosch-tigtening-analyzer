import json
from io import BytesIO

import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt


st.set_page_config(page_title="Bosch Tightening Analyzer", layout="wide")
st.title("Bosch Tightening Analyzer")
st.write("Wrzuć pliki JSON/TXT z Boscha, wybierz konkretny krok albo wszystkie kroki i eksportuj wykresy do Excela.")


uploaded_files = st.file_uploader(
    "Wrzuć pliki z Boscha",
    type=["txt", "json"],
    accept_multiple_files=True
)


def get_graph_data(step):
    graph = step.get("graph", {})
    return {
        "angle": graph.get("angle values", []) or [],
        "torque": graph.get("torque values", []) or [],
        "gradient": graph.get("gradient values", []) or [],
        "time_vals": graph.get("time values", []) or [],
        "angle_red": graph.get("angleRed values", []) or [],
        "torque_red": graph.get("torqueRed values", []) or [],
    }


def extract_step_features(step, file_name, cycle, program, overall_result, date_value, id_code):
    g = get_graph_data(step)
    angle = g["angle"]
    torque = g["torque"]
    gradient = g["gradient"]
    time_vals = g["time_vals"]
    angle_red = g["angle_red"]
    torque_red = g["torque_red"]

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


def show_plot(x, y, xlabel, ylabel, title):
    if not x or not y:
        st.info(f"Brak danych: {title}")
        return

    n = min(len(x), len(y))
    if n == 0:
        st.info(f"Brak danych: {title}")
        return

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x[:n], y[:n])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True)
    st.pyplot(fig)
    plt.close(fig)


def build_raw_points_rows(file_name, cycle, program, overall_result, step):
    g = get_graph_data(step)
    angle = g["angle"]
    torque = g["torque"]
    gradient = g["gradient"]
    time_vals = g["time_vals"]
    angle_red = g["angle_red"]
    torque_red = g["torque_red"]

    max_len = max(
        len(angle), len(torque), len(gradient), len(time_vals),
        len(angle_red), len(torque_red), 1
    )

    rows = []
    for i in range(max_len):
        rows.append({
            "file_name": file_name,
            "program": program,
            "cycle": cycle,
            "overall_result": overall_result,
            "step_name": step.get("name"),
            "step_result": step.get("result"),
            "point_index": i,
            "angle": angle[i] if i < len(angle) else None,
            "torque": torque[i] if i < len(torque) else None,
            "gradient": gradient[i] if i < len(gradient) else None,
            "time": time_vals[i] if i < len(time_vals) else None,
            "angle_red": angle_red[i] if i < len(angle_red) else None,
            "torque_red": torque_red[i] if i < len(torque_red) else None,
        })
    return rows


def create_excel_with_native_charts(summary_df, raw_df):
    output = BytesIO()

    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        summary_df.to_excel(writer, index=False, sheet_name="Summary")
        raw_df.to_excel(writer, index=False, sheet_name="Raw_Data")

        workbook = writer.book
        ws_summary = writer.sheets["Summary"]
        ws_raw = writer.sheets["Raw_Data"]
        ws_charts = workbook.add_worksheet("Charts")

        header_fmt = workbook.add_format({"bold": True, "bg_color": "#D9EAF7", "border": 1})
        normal_fmt = workbook.add_format({"border": 1})

        for ws, df_sheet in [(ws_summary, summary_df), (ws_raw, raw_df)]:
            ws.freeze_panes(1, 0)
            if len(df_sheet.columns) > 0:
                ws.autofilter(0, 0, max(len(df_sheet), 1), len(df_sheet.columns) - 1)

            for col_num, value in enumerate(df_sheet.columns.values):
                ws.write(0, col_num, value, header_fmt)

            for idx, col in enumerate(df_sheet.columns):
                sample_values = df_sheet[col].astype(str).head(200).tolist()
                max_len = max([len(str(col))] + [len(v) for v in sample_values]) if sample_values else len(str(col))
                ws.set_column(idx, idx, min(max(max_len + 2, 12), 35), normal_fmt)

        # indeksy kolumn w Raw_Data
        cols = {name: i for i, name in enumerate(raw_df.columns)}

        current_row = 0

        # grupowanie po step_name
        for step_name, grp in raw_df.groupby("step_name", sort=False):
            start_excel_row = grp.index.min() + 1  # +1 bo nagłówek jest w wierszu 0
            end_excel_row = grp.index.max() + 1

            ws_charts.write(current_row, 0, f"Krok: {step_name}", header_fmt)

            # Moment vs Kąt
            if grp["angle"].notna().any() and grp["torque"].notna().any():
                chart1 = workbook.add_chart({"type": "scatter", "subtype": "straight"})
                chart1.add_series({
                    "name":       f"{step_name} - Moment vs Kąt",
                    "categories": ["Raw_Data", start_excel_row, cols["angle"], end_excel_row, cols["angle"]],
                    "values":     ["Raw_Data", start_excel_row, cols["torque"], end_excel_row, cols["torque"]],
                })
                chart1.set_title({"name": f"{step_name} - Moment vs Kąt"})
                chart1.set_x_axis({"name": "Kąt [deg]"})
                chart1.set_y_axis({"name": "Moment"})
                chart1.set_legend({"none": True})
                ws_charts.insert_chart(current_row + 1, 0, chart1, {"x_scale": 1.2, "y_scale": 1.2})

            # Gradient vs Kąt
            if grp["angle"].notna().any() and grp["gradient"].notna().any():
                chart2 = workbook.add_chart({"type": "scatter", "subtype": "straight"})
                chart2.add_series({
                    "name":       f"{step_name} - Gradient vs Kąt",
                    "categories": ["Raw_Data", start_excel_row, cols["angle"], end_excel_row, cols["angle"]],
                    "values":     ["Raw_Data", start_excel_row, cols["gradient"], end_excel_row, cols["gradient"]],
                })
                chart2.set_title({"name": f"{step_name} - Gradient vs Kąt"})
                chart2.set_x_axis({"name": "Kąt [deg]"})
                chart2.set_y_axis({"name": "Gradient"})
                chart2.set_legend({"none": True})
                ws_charts.insert_chart(current_row + 1, 8, chart2, {"x_scale": 1.2, "y_scale": 1.2})

            # Moment vs Czas
            if grp["time"].notna().any() and grp["torque"].notna().any():
                chart3 = workbook.add_chart({"type": "scatter", "subtype": "straight"})
                chart3.add_series({
                    "name":       f"{step_name} - Moment vs Czas",
                    "categories": ["Raw_Data", start_excel_row, cols["time"], end_excel_row, cols["time"]],
                    "values":     ["Raw_Data", start_excel_row, cols["torque"], end_excel_row, cols["torque"]],
                })
                chart3.set_title({"name": f"{step_name} - Moment vs Czas"})
                chart3.set_x_axis({"name": "Czas"})
                chart3.set_y_axis({"name": "Moment"})
                chart3.set_legend({"none": True})
                ws_charts.insert_chart(current_row + 18, 0, chart3, {"x_scale": 1.2, "y_scale": 1.2})

            # MomentRed vs KątRed
            if grp["angle_red"].notna().any() and grp["torque_red"].notna().any():
                chart4 = workbook.add_chart({"type": "scatter", "subtype": "straight"})
                chart4.add_series({
                    "name":       f"{step_name} - MomentRed vs KątRed",
                    "categories": ["Raw_Data", start_excel_row, cols["angle_red"], end_excel_row, cols["angle_red"]],
                    "values":     ["Raw_Data", start_excel_row, cols["torque_red"], end_excel_row, cols["torque_red"]],
                })
                chart4.set_title({"name": f"{step_name} - MomentRed vs KątRed"})
                chart4.set_x_axis({"name": "KątRed [deg]"})
                chart4.set_y_axis({"name": "MomentRed"})
                chart4.set_legend({"none": True})
                ws_charts.insert_chart(current_row + 18, 8, chart4, {"x_scale": 1.2, "y_scale": 1.2})

            current_row += 36

    output.seek(0)
    return output


all_rows = []
all_data = []
all_raw_rows = []

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
                all_rows.append(
                    extract_step_features(
                        step=step,
                        file_name=file_name,
                        cycle=cycle,
                        program=program,
                        overall_result=overall_result,
                        date_value=date_value,
                        id_code=id_code
                    )
                )

                all_raw_rows.extend(
                    build_raw_points_rows(
                        file_name=file_name,
                        cycle=cycle,
                        program=program,
                        overall_result=overall_result,
                        step=step
                    )
                )

        except Exception as e:
            st.error(f"Błąd w pliku {uploaded_file.name}: {e}")

    if all_rows:
        df = pd.DataFrame(all_rows)
        raw_df = pd.DataFrame(all_raw_rows)

        st.subheader("Podsumowanie")
        c1, c2, c3 = st.columns(3)
        c1.metric("Liczba plików", len(uploaded_files))
        c2.metric("Liczba kroków", len(df))
        c3.metric("Unikalne cykle", df["cycle"].nunique())

        st.dataframe(df, use_container_width=True)

        st.subheader("Wybór wykresów")

        file_list = sorted(df["file_name"].dropna().unique().tolist())
        selected_file = st.selectbox("Wybierz plik", file_list)

        selected_file_data = next((item for item in all_data if item["file_name"] == selected_file), None)

        if selected_file_data:
            data = selected_file_data["data"]
            steps = data.get("tightening steps", [])

            step_names = [step.get("name", "Unnamed step") for step in steps]
            step_mode = st.radio("Tryb", ["Konkretny krok", "Wszystkie kroki"], horizontal=True)

            if step_mode == "Konkretny krok":
                selected_step_name = st.selectbox("Wybierz krok programu", step_names)
                selected_step = next((s for s in steps if s.get("name") == selected_step_name), None)

                if selected_step:
                    g = get_graph_data(selected_step)

                    st.subheader(f"Wykresy dla kroku: {selected_step_name}")

                    col1, col2 = st.columns(2)
                    with col1:
                        show_plot(g["angle"], g["torque"], "Kąt [deg]", "Moment", f"{selected_step_name} - Moment vs Kąt")
                    with col2:
                        show_plot(g["angle"], g["gradient"], "Kąt [deg]", "Gradient", f"{selected_step_name} - Gradient vs Kąt")

                    col3, col4 = st.columns(2)
                    with col3:
                        show_plot(g["time_vals"], g["torque"], "Czas", "Moment", f"{selected_step_name} - Moment vs Czas")
                    with col4:
                        show_plot(g["angle_red"], g["torque_red"], "KątRed [deg]", "MomentRed", f"{selected_step_name} - MomentRed vs KątRed")

                    filtered_summary_df = df[
                        (df["file_name"] == selected_file) &
                        (df["step_name"] == selected_step_name)
                    ].copy()

                    filtered_raw_df = raw_df[
                        (raw_df["file_name"] == selected_file) &
                        (raw_df["step_name"] == selected_step_name)
                    ].copy()

                    try:
                        excel_file = create_excel_with_native_charts(filtered_summary_df, filtered_raw_df)
                        st.download_button(
                            "Pobierz Excel z wykresami",
                            data=excel_file,
                            file_name="bosch_analysis_with_charts.xlsx",
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                    except Exception as e:
                        st.warning(f"Nie udało się wygenerować Excela: {e}")

            else:
                st.subheader("Wykresy dla wszystkich kroków")

                for step in steps:
                    step_name = step.get("name", "Unnamed step")
                    g = get_graph_data(step)

                    st.markdown(f"### {step_name}")

                    col1, col2 = st.columns(2)
                    with col1:
                        show_plot(g["angle"], g["torque"], "Kąt [deg]", "Moment", f"{step_name} - Moment vs Kąt")
                    with col2:
                        show_plot(g["angle"], g["gradient"], "Kąt [deg]", "Gradient", f"{step_name} - Gradient vs Kąt")

                    col3, col4 = st.columns(2)
                    with col3:
                        show_plot(g["time_vals"], g["torque"], "Czas", "Moment", f"{step_name} - Moment vs Czas")
                    with col4:
                        show_plot(g["angle_red"], g["torque_red"], "KątRed [deg]", "MomentRed", f"{step_name} - MomentRed vs KątRed")

                filtered_summary_df = df[df["file_name"] == selected_file].copy()
                filtered_raw_df = raw_df[raw_df["file_name"] == selected_file].copy()

                try:
                    excel_file = create_excel_with_native_charts(filtered_summary_df, filtered_raw_df)
                    st.download_button(
                        "Pobierz Excel z wykresami",
                        data=excel_file,
                        file_name="bosch_analysis_with_charts.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
                except Exception as e:
                    st.warning(f"Nie udało się wygenerować Excela: {e}")
    else:
        st.warning("Nie udało się wyciągnąć danych z plików.")
else:
    st.info("Wgraj pliki, aby rozpocząć analizę.")

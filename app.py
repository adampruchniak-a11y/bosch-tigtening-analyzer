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


def make_plot_image(x, y, xlabel, ylabel, title):
    if not x or not y:
        return None

    n = min(len(x), len(y))
    if n == 0:
        return None

    fig, ax = plt.subplots(figsize=(8, 4))
    ax.plot(x[:n], y[:n])
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True)

    buf = BytesIO()
    fig.tight_layout()
    fig.savefig(buf, format="png", dpi=150, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf


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


def create_excel_with_charts(summary_df, raw_df, charts_to_export):
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
            ws.autofilter(0, 0, max(len(df_sheet), 1), max(len(df_sheet.columns) - 1, 0))

            for col_num, value in enumerate(df_sheet.columns.values):
                ws.write(0, col_num, value, header_fmt)

            for idx, col in enumerate(df_sheet.columns):
                sample_values = df_sheet[col].astype(str).head(200).tolist()
                max_len = max([len(str(col))] + [len(v) for v in sample_values]) if sample_values else len(str(col))
                ws.set_column(idx, idx, min(max(max_len + 2, 12), 35), normal_fmt)

        row_cursor = 0
        for chart_item in charts_to_export:
            ws_charts.write(row_cursor, 0, chart_item["title"], header_fmt)

            if chart_item["image"] is not None:
                ws_charts.insert_image(
                    row_cursor + 1,
                    0,
                    "",
                    {"image_data": chart_item["image"], "x_scale": 0.9, "y_scale": 0.9}
                )
                row_cursor += 24
            else:
                ws_charts.write(row_cursor + 1, 0, "Brak danych do wykresu")
                row_cursor += 4

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

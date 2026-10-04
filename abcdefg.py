
import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import pycountry
import matplotlib.pyplot as plt

from io import BytesIO
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image as RLImage,
    PageBreak,
)


# ============================================================
# PAGE CONFIG
# ============================================================

st.set_page_config(
    page_title="Global COVID-19 Dashboard",
    page_icon="🦠",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# CUSTOM CSS
# ============================================================

st.markdown(
    """
<style>
html, body, [class*="css"] {
    font-family: Arial, sans-serif;
}

.stApp {
    background: #0b1220;
    color: #ffffff;
}

section[data-testid="stSidebar"] {
    background: #111827;
    border-right: 1px solid #263449;
}

section[data-testid="stSidebar"] h1,
section[data-testid="stSidebar"] h2,
section[data-testid="stSidebar"] h3,
section[data-testid="stSidebar"] label {
    color: #ffffff !important;
}

.dashboard-header {
    background: linear-gradient(135deg, #111827, #172554);
    border: 1px solid #334155;
    border-radius: 18px;
    padding: 22px 28px;
    margin-bottom: 20px;
    box-shadow: 0 8px 25px rgba(0,0,0,0.25);
}

.dashboard-header h1 {
    margin: 0;
    color: #ffffff;
    font-size: 30px;
}

.dashboard-header p {
    color: #94a3b8;
    margin-top: 6px;
}

.section-card {
    background: #111827;
    border: 1px solid #293548;
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 18px;
}

.section-title {
    font-size: 20px;
    font-weight: bold;
    color: #e2e8f0;
    margin-bottom: 12px;
}

.kpi-card {
    background: linear-gradient(145deg, #111827, #172033);
    border: 1px solid #334155;
    border-radius: 15px;
    padding: 18px;
    min-height: 125px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transition: 0.2s;
    margin-bottom: 12px;
}

.kpi-card:hover {
    border-color: #38bdf8;
    transform: translateY(-2px);
}

.kpi-icon {
    font-size: 25px;
}

.kpi-title {
    color: #94a3b8;
    font-size: 13px;
    margin-top: 5px;
}

.kpi-value {
    color: #ffffff;
    font-size: 25px;
    font-weight: bold;
    margin-top: 7px;
}

.kpi-sub {
    color: #64748b;
    font-size: 12px;
    margin-top: 4px;
}

.country-card {
    background: linear-gradient(135deg, #172554, #0f172a);
    border: 1px solid #2563eb;
    border-radius: 18px;
    padding: 25px;
    text-align: center;
    margin-bottom: 20px;
}

.country-name {
    font-size: 30px;
    font-weight: bold;
}

.country-label {
    color: #94a3b8;
}

.education-alert {
    background: rgba(59,130,246,0.12);
    border: 1px solid #3b82f6;
    border-radius: 12px;
    padding: 13px 17px;
    color: #bfdbfe;
    margin-bottom: 15px;
}

.patient-section {
    background: #111827;
    border: 1px solid #293548;
    border-radius: 16px;
    padding: 20px;
    margin: 15px 0;
}

.footer {
    text-align: center;
    color: #64748b;
    padding: 25px;
    margin-top: 30px;
}

.stButton > button {
    border-radius: 10px;
    border: 1px solid #334155;
    background: #172033;
    color: white;
    transition: 0.2s;
}

.stButton > button:hover {
    border-color: #38bdf8;
    color: #ffffff;
}

[data-testid="stDataFrame"] {
    border: 1px solid #334155;
    border-radius: 10px;
}
</style>
""",
    unsafe_allow_html=True,
)


# ============================================================
# COUNTRY LIST
# ============================================================

COUNTRIES = sorted({country.name for country in pycountry.countries})

if len(COUNTRIES) != 249:
    st.error(
        f"Your installed pycountry version returned {len(COUNTRIES)} "
        "countries/territories instead of 249. "
        "Please run: pip install -U pycountry"
    )
    st.stop()


# ============================================================
# CONSTANTS
# ============================================================

REQUIRED_COLUMNS = [
    "Country",
    "Population",
    "Confirmed",
    "Deaths",
    "Recovered",
    "Active",
    "Vaccinated",
]

NUMERIC_COLUMNS = [
    "Population",
    "Confirmed",
    "Deaths",
    "Recovered",
    "Active",
    "Vaccinated",
]

COVID_METRICS = [
    "Confirmed",
    "Deaths",
    "Recovered",
    "Active",
    "Vaccinated",
    "Population",
]

METRIC_ICONS = {
    "Population": "👥",
    "Confirmed": "🦠",
    "Deaths": "⚰️",
    "Recovered": "💚",
    "Active": "🔴",
    "Vaccinated": "💉",
    "Death Rate": "📉",
    "Recovery Rate": "📈",
}

CHART_TYPES = [
    "Bar Chart",
    "Line Chart",
    "Area Chart",
    "Pie Chart",
]

VIEW_TYPES = [
    "📊 Chart",
    "📈 Graph",
    "📋 Table",
    "🔢 Data",
    "🗺️ Map",
]


# ============================================================
# HELPERS
# ============================================================

def fmt(value):
    if pd.isna(value):
        return "0"

    try:
        value = float(value)
    except (TypeError, ValueError):
        return str(value)

    if value.is_integer():
        return f"{int(value):,}"

    return f"{value:,.2f}"


def get_country(country):
    result = df[df["Country"] == country]

    if result.empty:
        return df.iloc[0]

    return result.iloc[0]


def make_plotly_dark(fig):
    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#111827",
        plot_bgcolor="#111827",
        font=dict(color="#ffffff"),
        margin=dict(l=40, r=30, t=70, b=40),
    )
    return fig


def metric_value(row, metric):
    if metric in row.index:
        return row[metric]
    return 0


def safe_filename(text):
    return (
        str(text)
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
        .replace(" ", "_")
    )


# ============================================================
# DEMO DATA
# ============================================================

@st.cache_data
def create_demo_data():
    """
    Creates deterministic demonstration COVID data
    for all 249 countries/territories.
    """

    rng = np.random.default_rng(42)
    rows = []

    for country in COUNTRIES:
        population = int(rng.integers(50_000, 1_500_000_000))

        confirmed = int(
            population * rng.uniform(0.01, 0.35)
        )
        confirmed = max(confirmed, 1000)

        deaths = int(
            confirmed * rng.uniform(0.005, 0.04)
        )

        recovered = int(
            confirmed * rng.uniform(0.55, 0.90)
        )

        recovered = min(
            recovered,
            max(confirmed - deaths, 0)
        )

        active = max(
            confirmed - deaths - recovered,
            0
        )

        vaccinated = min(
            int(population * rng.uniform(0.30, 0.95)),
            population
        )

        rows.append(
            {
                "Country": country,
                "Population": population,
                "Confirmed": confirmed,
                "Deaths": deaths,
                "Recovered": recovered,
                "Active": active,
                "Vaccinated": vaccinated,
            }
        )

    demo = pd.DataFrame(rows)

    demo["Death Rate"] = np.where(
        demo["Confirmed"] > 0,
        demo["Deaths"] / demo["Confirmed"] * 100,
        0,
    )

    demo["Recovery Rate"] = np.where(
        demo["Confirmed"] > 0,
        demo["Recovered"] / demo["Confirmed"] * 100,
        0,
    )

    return demo.sort_values("Country").reset_index(drop=True)


df = create_demo_data()


# ============================================================
# FINAL VALIDATION
# ============================================================

if df["Country"].nunique() != 249:
    st.error(
        "Dataset validation failed. "
        f"Current unique country count: {df['Country'].nunique()}"
    )
    st.stop()

missing_columns = [
    column for column in REQUIRED_COLUMNS
    if column not in df.columns
]

if missing_columns:
    st.error(
        "Dataset is missing required columns: "
        + ", ".join(missing_columns)
    )
    st.stop()


# ============================================================
# PDF STYLES
# ============================================================

def pdf_styles():
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "CustomTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#172554"),
        spaceAfter=8,
    )

    subtitle_style = ParagraphStyle(
        "Subtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        leading=12,
        textColor=colors.HexColor("#475569"),
        spaceAfter=8,
    )

    heading_style = ParagraphStyle(
        "HeadingCustom",
        parent=styles["Heading2"],
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#1d4ed8"),
        spaceBefore=10,
        spaceAfter=7,
    )

    section_style = ParagraphStyle(
        "SectionCustom",
        parent=styles["Heading2"],
        alignment=TA_CENTER,
        fontSize=12,
        leading=15,
        textColor=colors.HexColor("#172554"),
        spaceBefore=8,
        spaceAfter=8,
    )

    normal_style = ParagraphStyle(
        "NormalCustom",
        parent=styles["Normal"],
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#111827"),
    )

    small_style = ParagraphStyle(
        "SmallCustom",
        parent=styles["Normal"],
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#334155"),
    )

    return {
        "title": title_style,
        "subtitle": subtitle_style,
        "heading": heading_style,
        "section": section_style,
        "normal": normal_style,
        "small": small_style,
    }


# ============================================================
# PDF CHART GENERATOR
# ============================================================

def create_chart_image(
    chart_type,
    title,
    labels,
    values,
    xlabel="",
    ylabel="Value",
):
    """
    Creates a chart as PNG for insertion into a PDF.
    Uses matplotlib so PDF generation does not require
    Plotly/Kaleido.
    """

    values = [float(v) if pd.notna(v) else 0 for v in values]
    labels = [str(x) for x in labels]

    fig, ax = plt.subplots(figsize=(8.5, 4.6))

    if chart_type == "Bar Chart":
        bars = ax.bar(labels, values)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)

        for bar, value in zip(bars, values):
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bar.get_height(),
                fmt(value),
                ha="center",
                va="bottom",
                fontsize=8,
            )

    elif chart_type == "Line Chart":
        ax.plot(labels, values, marker="o", linewidth=2)
        ax.set_ylabel(ylabel)
        ax.set_xlabel(xlabel)

        for x, value in zip(labels, values):
            ax.annotate(
                fmt(value),
                (x, value),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=8,
            )

    elif chart_type == "Area Chart":
        ax.fill_between(
            range(len(values)),
            values,
            alpha=0.30,
        )
        ax.plot(
            range(len(values)),
            values,
            marker="o",
            linewidth=2,
        )
        ax.set_xticks(range(len(labels)))
        ax.set_xticklabels(labels, rotation=25, ha="right")
        ax.set_ylabel(ylabel)

        for i, value in enumerate(values):
            ax.annotate(
                fmt(value),
                (i, value),
                textcoords="offset points",
                xytext=(0, 7),
                ha="center",
                fontsize=8,
            )

    else:
        positive_values = [max(v, 0) for v in values]

        if sum(positive_values) <= 0:
            positive_values = [1] * len(labels)

        ax.pie(
            positive_values,
            labels=labels,
            autopct=lambda pct: f"{pct:.1f}%",
            startangle=90,
        )
        ax.axis("equal")

    ax.set_title(title, fontsize=13, fontweight="bold")
    ax.grid(axis="y", alpha=0.20)

    fig.tight_layout()

    image_buffer = BytesIO()
    fig.savefig(
        image_buffer,
        format="png",
        dpi=170,
        bbox_inches="tight",
    )
    plt.close(fig)

    image_buffer.seek(0)
    return image_buffer.getvalue()


# ============================================================
# GENERIC PDF BUILDING
# ============================================================

def pdf_table(data, styles, col_widths=None):
    formatted = []

    for row_index, row in enumerate(data):
        formatted_row = []

        for cell in row:
            style = styles["small"]

            formatted_row.append(
                Paragraph(
                    str(cell).replace("&", "&amp;"),
                    style,
                )
            )

        formatted.append(formatted_row)

    table = Table(
        formatted,
        repeatRows=1,
        colWidths=col_widths,
    )

    table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#172554"),
                ),
                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white,
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#cbd5e1"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#f8fafc"),
                    ],
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    5,
                ),
            ]
        )
    )

    return table


def build_pdf(
    title,
    subtitle,
    story,
    output_name="COVID_Report.pdf",
):
    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=14 * mm,
        leftMargin=14 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
        title=title,
        author="Global COVID-19 Dashboard",
    )

    styles = pdf_styles()

    final_story = []

    final_story.append(
        Paragraph(title, styles["title"])
    )

    final_story.append(
        Paragraph(subtitle, styles["subtitle"])
    )

    final_story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime(
                "%d %B %Y, %H:%M:%S"
            ),
            styles["subtitle"],
        )
    )

    final_story.extend(story)

    document.build(final_story)

    buffer.seek(0)
    return buffer.getvalue()


# ============================================================
# COMMON PDF INFORMATION
# ============================================================

def add_control_summary(
    story,
    selected_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
    page_controls=None,
):
    styles = pdf_styles()

    data = [
        ["Dashboard Selection", "Selected Value"],
        ["Country", selected_country],
        ["Sidebar Metric", sidebar_metric],
        ["Sidebar Chart Type", sidebar_chart],
        ["Selected Page", selected_page],
    ]

    if page_controls:
        for key, value in page_controls.items():
            data.append([key, value])

    story.append(
        Paragraph(
            "📌 DASHBOARD SELECTION",
            styles["heading"],
        )
    )

    story.append(
        pdf_table(
            data,
            styles,
            col_widths=[58 * mm, 115 * mm],
        )
    )

    story.append(Spacer(1, 8))


# ============================================================
# HOME PDF
# ============================================================

def home_pdf(
    country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
):
    styles = pdf_styles()
    row = get_country(country)

    story = []

    add_control_summary(
        story,
        country,
        sidebar_metric,
        sidebar_chart,
        selected_page,
    )

    story.append(
        Paragraph(
            f"🌍 {country.upper()}",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "Selected Country COVID-19 Statistics",
            styles["subtitle"],
        )
    )

    metrics = [
        ("Population", row["Population"]),
        ("Confirmed", row["Confirmed"]),
        ("Deaths", row["Deaths"]),
        ("Recovered", row["Recovered"]),
        ("Active", row["Active"]),
        ("Vaccinated", row["Vaccinated"]),
        ("Death Rate", f"{row['Death Rate']:.2f}%"),
        ("Recovery Rate", f"{row['Recovery Rate']:.2f}%"),
    ]

    data = [["Metric", "Value"]]

    for metric, value in metrics:
        data.append([metric, fmt(value)])

    story.append(
        pdf_table(
            data,
            styles,
            col_widths=[75 * mm, 98 * mm],
        )
    )

    story.append(Spacer(1, 10))

    # Chart uses exactly the sidebar-selected metric
    chart_value = row[sidebar_metric]

    chart_image = create_chart_image(
        sidebar_chart,
        f"{country} - {sidebar_metric}",
        [sidebar_metric],
        [chart_value],
        xlabel="Metric",
        ylabel=sidebar_metric,
    )

    story.append(
        Paragraph(
            f"📊 SELECTED CHART - {sidebar_chart}",
            styles["heading"],
        )
    )

    story.append(
        RLImage(
            BytesIO(chart_image),
            width=175 * mm,
            height=92 * mm,
        )
    )

    story.append(
        Paragraph(
            f"<b>{sidebar_metric} value:</b> {fmt(chart_value)}",
            styles["normal"],
        )
    )

    return build_pdf(
        "GLOBAL COVID-19 COUNTRY REPORT",
        f"{country} | Sidebar Metric: {sidebar_metric} | Chart: {sidebar_chart}",
        story,
        f"{safe_filename(country)}_COVID_Report.pdf",
    )


# ============================================================
# GLOBAL MAP PDF
# ============================================================

def global_map_pdf(
    selected_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
    map_metric,
):
    styles = pdf_styles()
    story = []

    add_control_summary(
        story,
        selected_country,
        sidebar_metric,
        sidebar_chart,
        selected_page,
        {"Map Metric": map_metric},
    )

    story.append(
        Paragraph(
            "🗺️ GLOBAL COVID MAP REPORT",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            f"Map Metric: <b>{map_metric}</b>",
            styles["normal"],
        )
    )

    story.append(Spacer(1, 7))

    top = df.nlargest(10, map_metric)

    chart_image = create_chart_image(
        sidebar_chart,
        f"Top 10 Countries - {map_metric}",
        top["Country"].tolist(),
        top[map_metric].tolist(),
        xlabel="Country",
        ylabel=map_metric,
    )

    story.append(
        Paragraph(
            f"📊 CHART / GRAPH - {sidebar_chart}",
            styles["heading"],
        )
    )

    story.append(
        RLImage(
            BytesIO(chart_image),
            width=175 * mm,
            height=92 * mm,
        )
    )

    data = [["Rank", "Country", map_metric]]

    for rank, (_, row) in enumerate(
        top.iterrows(),
        start=1,
    ):
        data.append(
            [
                rank,
                row["Country"],
                fmt(row[map_metric]),
            ]
        )

    story.append(
        Paragraph(
            f"🏆 TOP 10 BY {map_metric.upper()}",
            styles["heading"],
        )
    )

    story.append(
        pdf_table(
            data,
            styles,
            col_widths=[20 * mm, 80 * mm, 65 * mm],
        )
    )

    story.append(Spacer(1, 8))

    story.append(
        Paragraph(
            "Countries / Territories: <b>249</b><br/>"
            "Map is interactive in the dashboard. "
            "The PDF includes the selected map metric and its "
            "corresponding chart and values.",
            styles["normal"],
        )
    )

    return build_pdf(
        "GLOBAL COVID-19 MAP REPORT",
        f"Map Metric: {map_metric}",
        story,
        "Global_COVID_Map_Report.pdf",
    )


# ============================================================
# COMPARISON PDF
# ============================================================

def comparison_pdf(
    country1,
    country2,
    metric,
    view,
    sidebar_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
):
    styles = pdf_styles()
    row1 = get_country(country1)
    row2 = get_country(country2)

    story = []

    add_control_summary(
        story,
        sidebar_country,
        sidebar_metric,
        sidebar_chart,
        selected_page,
        {
            "Comparison Country 1": country1,
            "Comparison Country 2": country2,
            "Comparison Metric": metric,
            "Comparison View": view,
        },
    )

    story.append(
        Paragraph(
            f"🌍 {country1} VS {country2}",
            styles["section"],
        )
    )

    comparison_data = [
        ["Metric", country1, country2],
    ]

    comparison_metrics = [
        "Population",
        "Confirmed",
        "Deaths",
        "Recovered",
        "Active",
        "Vaccinated",
        "Death Rate",
        "Recovery Rate",
    ]

    for item in comparison_metrics:
        if "Rate" in item:
            v1 = f"{row1[item]:.2f}%"
            v2 = f"{row2[item]:.2f}%"
        else:
            v1 = fmt(row1[item])
            v2 = fmt(row2[item])

        comparison_data.append(
            [item, v1, v2]
        )

    story.append(
        pdf_table(
            comparison_data,
            styles,
            col_widths=[55 * mm, 60 * mm, 60 * mm],
        )
    )

    story.append(Spacer(1, 10))

    # Main page-selected comparison chart
    chart_image = create_chart_image(
        sidebar_chart,
        f"{metric} Comparison",
        [country1, country2],
        [row1[metric], row2[metric]],
        xlabel="Country",
        ylabel=metric,
    )

    story.append(
        Paragraph(
            f"📊 COMPARISON CHART - {sidebar_chart}",
            styles["heading"],
        )
    )

    story.append(
        RLImage(
            BytesIO(chart_image),
            width=175 * mm,
            height=92 * mm,
        )
    )

    story.append(
        Paragraph(
            f"<b>{country1} {metric}:</b> {fmt(row1[metric])}<br/>"
            f"<b>{country2} {metric}:</b> {fmt(row2[metric])}",
            styles["normal"],
        )
    )

    return build_pdf(
        "COUNTRY COMPARISON REPORT",
        f"{country1} VS {country2} | Metric: {metric}",
        story,
        f"{safe_filename(country1)}_vs_{safe_filename(country2)}_COVID.pdf",
    )


# ============================================================
# TOP 10 PDF
# ============================================================

def top10_pdf(
    metric,
    view,
    selected_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
):
    styles = pdf_styles()
    story = []

    add_control_summary(
        story,
        selected_country,
        sidebar_metric,
        sidebar_chart,
        selected_page,
        {
            "Top 10 Metric": metric,
            "Top 10 View": view,
        },
    )

    top = (
        df.sort_values(metric, ascending=False)
        .head(10)
        .copy()
    )

    top["Rank"] = range(1, 11)

    chart_image = create_chart_image(
        sidebar_chart,
        f"Top 10 Countries by {metric}",
        top["Country"].tolist(),
        top[metric].tolist(),
        xlabel="Country",
        ylabel=metric,
    )

    story.append(
        Paragraph(
            f"🏆 TOP 10 COUNTRIES BY {metric.upper()}",
            styles["section"],
        )
    )

    story.append(
        RLImage(
            BytesIO(chart_image),
            width=175 * mm,
            height=92 * mm,
        )
    )

    data = [["Rank", "Country", metric]]

    for _, row in top.iterrows():
        data.append(
            [
                row["Rank"],
                row["Country"],
                fmt(row[metric]),
            ]
        )

    story.append(
        pdf_table(
            data,
            styles,
            col_widths=[22 * mm, 90 * mm, 63 * mm],
        )
    )

    return build_pdf(
        "TOP 10 COVID-19 COUNTRIES REPORT",
        f"Metric: {metric} | Chart: {sidebar_chart}",
        story,
        f"Top10_{safe_filename(metric)}.pdf",
    )


# ============================================================
# COMPLETE DATASET PDF
# ============================================================

def dataset_pdf(
    selected_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
    search_text="",
):
    styles = pdf_styles()
    story = []

    add_control_summary(
        story,
        selected_country,
        sidebar_metric,
        sidebar_chart,
        selected_page,
        {
            "Dataset Search": search_text if search_text else "All Countries",
            "Total Countries/Territories": "249",
        },
    )

    filtered = df.copy()

    if search_text:
        filtered = filtered[
            filtered["Country"].str.contains(
                search_text,
                case=False,
                na=False,
            )
        ]

    story.append(
        Paragraph(
            f"📋 COMPLETE COVID-19 DATASET ({len(filtered)} ROWS)",
            styles["section"],
        )
    )

    data = [[
        "Country",
        "Population",
        "Confirmed",
        "Deaths",
        "Recovered",
        "Active",
        "Vaccinated",
    ]]

    for _, row in filtered.iterrows():
        data.append(
            [
                row["Country"],
                fmt(row["Population"]),
                fmt(row["Confirmed"]),
                fmt(row["Deaths"]),
                fmt(row["Recovered"]),
                fmt(row["Active"]),
                fmt(row["Vaccinated"]),
            ]
        )

    story.append(
        pdf_table(
            data,
            styles,
            col_widths=[
                45 * mm,
                25 * mm,
                25 * mm,
                22 * mm,
                25 * mm,
                22 * mm,
                25 * mm,
            ],
        )
    )

    return build_pdf(
        "COMPLETE COVID-19 DATASET REPORT",
        f"249 Countries / Territories | Selected Metric: {sidebar_metric}",
        story,
        "Complete_COVID_Dataset.pdf",
    )


# ============================================================
# PATIENT PDF - REQUESTED DESIGN
# ============================================================

def patient_pdf(
    name,
    age,
    gender,
    symptoms,
    selected_country,
    sidebar_metric,
    sidebar_chart,
    selected_page,
):
    styles = pdf_styles()
    story = []

    symptom_names = [
        "🌡️ Fever",
        "😷 Cough",
        "🗣️ Sore Throat",
        "😴 Fatigue",
        "🤕 Headache",
        "💪 Body Pain",
        "👃 Loss of Taste or Smell",
        "🫁 Breathing Difficulty",
    ]

    selected_set = set(symptoms)

    # Header
    story.append(
        Paragraph(
            "🏥 COVID PATIENT REPORT",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "PATIENT EDUCATIONAL REPORT",
            styles["subtitle"],
        )
    )

    story.append(Spacer(1, 5))

    # Patient information
    story.append(
        Paragraph(
            "👤 PATIENT INFORMATION",
            styles["section"],
        )
    )

    selected_symptom_text = (
        ", ".join(symptoms)
        if symptoms
        else "No symptoms selected"
    )

    patient_data = [
        ["Information", "Patient Details"],
        ["👤 Patient Name", name],
        ["🎂 Age", age],
        ["⚧ Gender", gender],
        ["🤒 Symptoms", selected_symptom_text],
    ]

    story.append(
        pdf_table(
            patient_data,
            styles,
            col_widths=[58 * mm, 115 * mm],
        )
    )

    story.append(Spacer(1, 12))

    # Symptom section
    story.append(
        Paragraph(
            "🤒 COVID SYMPTOM INFORMATION",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "<b>Selected Symptoms:</b>",
            styles["normal"],
        )
    )

    for symptom in symptom_names:
        mark = "☑" if symptom in selected_set else "☐"

        story.append(
            Paragraph(
                f"{mark} {symptom}",
                styles["normal"],
            )
        )

        story.append(Spacer(1, 3))

    story.append(Spacer(1, 8))

    # Care section
    story.append(
        Paragraph(
            "💊 COVID CARE & RECOVERY",
            styles["section"],
        )
    )

    care_items = [
        "✓ 🧼 Maintain hygiene",
        "✓ 💧 Drink enough fluids",
        "✓ 🛌 Take proper rest",
        "✓ 📊 Monitor symptoms",
        "✓ 👨‍⚕️ Follow healthcare guidance",
    ]

    for item in care_items:
        story.append(
            Paragraph(
                item,
                styles["normal"],
            )
        )
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))

    # Urgent section
    story.append(
        Paragraph(
            "🚨 URGENT MEDICAL ATTENTION",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "<b>Seek urgent medical help for:</b>",
            styles["normal"],
        )
    )

    urgent_items = [
        "• 🫁 Breathing difficulty",
        "• ❤️ Chest pain or pressure",
        "• 🧠 Confusion or unusual tiredness",
        "• ⚠️ Severe weakness",
    ]

    for item in urgent_items:
        story.append(
            Paragraph(
                item,
                styles["normal"],
            )
        )
        story.append(Spacer(1, 4))

    story.append(Spacer(1, 8))

    # Educational disclaimer
    story.append(
        Paragraph(
            "ℹ️ EDUCATIONAL DISCLAIMER",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "This report is for educational purposes only and does not "
            "replace professional medical advice.",
            styles["normal"],
        )
    )

    story.append(Spacer(1, 12))

    # Dashboard selection, so patient PDF also records sidebar/page state
    story.append(
        Paragraph(
            "📌 DASHBOARD SESSION",
            styles["section"],
        )
    )

    session_data = [
        ["Setting", "Selected Value"],
        ["Selected Country", selected_country],
        ["Sidebar Metric", sidebar_metric],
        ["Sidebar Chart Type", sidebar_chart],
        ["Selected Page", selected_page],
    ]

    story.append(
        pdf_table(
            session_data,
            styles,
            col_widths=[58 * mm, 115 * mm],
        )
    )

    story.append(Spacer(1, 15))

    story.append(
        Paragraph(
            "Generated: "
            + datetime.now().strftime(
                "%d %B %Y, %H:%M:%S"
            ),
            styles["subtitle"],
        )
    )

    story.append(
        Paragraph(
            "🏥 COVID Patient Educational Module",
            styles["subtitle"],
        )
    )

    return build_pdf(
        "COVID PATIENT REPORT",
        "PATIENT EDUCATIONAL REPORT",
        story,
        "COVID_Patient_Report.pdf",
    )


# ============================================================
# SIDEBAR
# ============================================================

with st.sidebar:
    st.markdown(
        """
        <div style="
        text-align:center;
        padding:10px;
        font-size:24px;
        font-weight:bold;
        ">
        🦠 COVID-19 DASHBOARD
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown("---")

    selected_country = st.selectbox(
        "🌍 Select Country",
        COUNTRIES,
        index=COUNTRIES.index("India")
        if "India" in COUNTRIES
        else 0,
        key="sidebar_country",
    )

    selected_metric_sidebar = st.selectbox(
        "📊 Select Metric",
        [
            "Confirmed",
            "Deaths",
            "Recovered",
            "Active",
            "Vaccinated",
            "Population",
        ],
        key="sidebar_metric",
    )

    selected_chart_sidebar = st.selectbox(
        "📈 Select Chart Type",
        CHART_TYPES,
        key="sidebar_chart",
    )

    st.markdown("### 📄 Report / Dashboard Page")

    # Global Summary and Analytics REMOVED
    page = st.radio(
        "Navigate",
        [
            "🏠 Home",
            "🗺️ Global COVID Map",
            "⚖️ Compare Countries",
            "🏆 Top 10 Countries",
            "📋 Complete Dataset",
            "🏥 COVID Patient Module",
        ],
        label_visibility="collapsed",
        key="sidebar_page",
    )

    st.markdown("---")

    st.success("✓ COVID Dashboard Ready")

    st.markdown(
        f"""
        **Selected Country:**  
        🌍 {selected_country}

        **Selected Page:**  
        {page}

        **Selected Metric:**  
        📊 {selected_metric_sidebar}

        **Selected Chart:**  
        📈 {selected_chart_sidebar}

        **Available Countries/Territories:**  
        🌍 **{df['Country'].nunique()}**
        """
    )


# ============================================================
# MAIN HEADER
# ============================================================

# IMPORTANT:
# The old "● DATASET READY" live badge has been removed.

st.markdown(
    """
    <div class="dashboard-header">
        <h1>🦠 GLOBAL COVID-19 DATA VISUALIZATION DASHBOARD</h1>
        <p>🌍 Interactive COVID-19 country and global analytics</p>
    </div>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# HOME PAGE
# ============================================================

def show_home():
    row = get_country(selected_country)

    st.markdown(
        f"""
        <div class="country-card">
            <div class="country-name">
                🌍 {selected_country.upper()}
            </div>
            <div class="country-label">
                Selected Country: {selected_country}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    metrics = [
        ("👥", "POPULATION", row["Population"], "Total People"),
        ("🦠", "CONFIRMED", row["Confirmed"], "Total Cases"),
        ("⚰️", "DEATHS", row["Deaths"], "Total Deaths"),
        ("💚", "RECOVERED", row["Recovered"], "Recovered"),
        ("🔴", "ACTIVE", row["Active"], "Active Cases"),
        ("💉", "VACCINATED", row["Vaccinated"], "Vaccinated"),
    ]

    cols = st.columns(3)

    for i, (icon, title, value, subtitle) in enumerate(metrics):
        with cols[i % 3]:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-icon">{icon}</div>
                    <div class="kpi-title">{title}</div>
                    <div class="kpi-value">{fmt(value)}</div>
                    <div class="kpi-sub">{subtitle}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    rate_cols = st.columns(2)

    with rate_cols[0]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon">📉</div>
                <div class="kpi-title">DEATH RATE</div>
                <div class="kpi-value">{row["Death Rate"]:.2f}%</div>
                <div class="kpi-sub">Deaths / Confirmed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with rate_cols[1]:
        st.markdown(
            f"""
            <div class="kpi-card">
                <div class="kpi-icon">📈</div>
                <div class="kpi-title">RECOVERY RATE</div>
                <div class="kpi-value">{row["Recovery Rate"]:.2f}%</div>
                <div class="kpi-sub">Recovered / Confirmed</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown(
        f"### 📊 SELECTED CHART — {selected_metric_sidebar}"
    )

    chart_df = pd.DataFrame(
        {
            "Metric": [selected_metric_sidebar],
            "Value": [row[selected_metric_sidebar]],
        }
    )

    title = (
        f"{selected_country} - "
        f"{selected_metric_sidebar}"
    )

    if selected_chart_sidebar == "Bar Chart":
        fig = px.bar(
            chart_df,
            x="Metric",
            y="Value",
            text="Value",
            title=title,
        )

    elif selected_chart_sidebar == "Line Chart":
        fig = px.line(
            chart_df,
            x="Metric",
            y="Value",
            markers=True,
            title=title,
        )

    elif selected_chart_sidebar == "Area Chart":
        fig = px.area(
            chart_df,
            x="Metric",
            y="Value",
            title=title,
        )

    else:
        fig = px.pie(
            chart_df,
            names="Metric",
            values="Value",
            title=title,
        )

    make_plotly_dark(fig)

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    st.info(
        f"Selected country: {selected_country} | "
        f"Selected metric: {selected_metric_sidebar} | "
        f"Selected chart: {selected_chart_sidebar} | "
        f"Value: {fmt(row[selected_metric_sidebar])}"
    )

    pdf = home_pdf(
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
    )

    st.download_button(
        "📄 Generate Home PDF Report",
        data=pdf,
        file_name=f"{safe_filename(selected_country)}_COVID_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# GLOBAL MAP
# ============================================================

def show_global_map():
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                🗺️ GLOBAL COVID MAP
            </div>
            Interactive worldwide COVID-19 visualization
        </div>
        """,
        unsafe_allow_html=True,
    )

    # The sidebar metric is used as the default map metric.
    default_index = (
        COVID_METRICS.index(selected_metric_sidebar)
        if selected_metric_sidebar in COVID_METRICS
        else 0
    )

    map_metric = st.selectbox(
        "📊 SELECT MAP METRIC",
        COVID_METRICS,
        index=default_index,
        key="map_metric",
    )

    fig = px.choropleth(
        df,
        locations="Country",
        locationmode="country names",
        color=map_metric,
        hover_name="Country",
        hover_data=[
            "Confirmed",
            "Deaths",
            "Recovered",
            "Active",
            "Vaccinated",
        ],
        color_continuous_scale="Blues",
        title=f"Global COVID-19 - {map_metric}",
    )

    fig.update_layout(
        template="plotly_dark",
        paper_bgcolor="#0b1220",
        geo=dict(
            bgcolor="#0b1220",
            showframe=False,
        ),
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
    )

    top = df.nlargest(10, map_metric)

    st.markdown(
        f"### 🏆 TOP 10 COUNTRIES — {map_metric}"
    )

    top_chart = px.bar(
        top.sort_values(map_metric),
        x=map_metric,
        y="Country",
        orientation="h",
        text=map_metric,
        title=f"Top 10 Countries by {map_metric}",
    )

    make_plotly_dark(top_chart)

    st.plotly_chart(
        top_chart,
        use_container_width=True,
    )

    pdf = global_map_pdf(
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
        map_metric,
    )

    st.download_button(
        "📄 Generate Global Map PDF",
        data=pdf,
        file_name="Global_COVID_Map_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# COUNTRY COMPARISON
# ============================================================

def show_comparison():
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                ⚖️ COUNTRY COMPARISON
            </div>
            Compare COVID-19 statistics between two countries
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        country1 = st.selectbox(
            "🌍 First Country",
            COUNTRIES,
            index=COUNTRIES.index("India")
            if "India" in COUNTRIES
            else 0,
            key="comparison_country_1",
        )

    with c2:
        default_second = (
            COUNTRIES.index("United States")
            if "United States" in COUNTRIES
            else 0
        )

        country2 = st.selectbox(
            "🌍 Second Country",
            COUNTRIES,
            index=default_second,
            key="comparison_country_2",
        )

    st.markdown(
        f"""
        <div class="country-card">
            <div class="country-name">
                🌍 {country1} VS 🌍 {country2}
            </div>
            <div class="country-label">
                COVID Statistics Comparison
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_metric_index = (
        COVID_METRICS.index(selected_metric_sidebar)
        if selected_metric_sidebar in COVID_METRICS
        else 0
    )

    metric = st.selectbox(
        "📊 SELECT METRIC",
        COVID_METRICS,
        index=default_metric_index,
        key="comparison_metric",
    )

    view = st.selectbox(
        "👁️ SELECT VIEW",
        VIEW_TYPES,
        key="comparison_view",
    )

    row1 = get_country(country1)
    row2 = get_country(country2)

    comparison = pd.DataFrame(
        {
            "Country": [country1, country2],
            "Value": [
                row1[metric],
                row2[metric],
            ],
        }
    )

    if view == "📊 Chart":
        fig = px.bar(
            comparison,
            x="Country",
            y="Value",
            text="Value",
            title=f"{metric} Comparison",
        )

        make_plotly_dark(fig)
        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    elif view == "📈 Graph":
        fig = px.line(
            comparison,
            x="Country",
            y="Value",
            markers=True,
            title=f"{metric} Comparison Graph",
        )

        make_plotly_dark(fig)
        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    elif view == "📋 Table":
        table_data = {
            "Metric": [
                "Population",
                "Confirmed",
                "Deaths",
                "Recovered",
                "Active",
                "Vaccinated",
                "Death Rate",
                "Recovery Rate",
            ],
            country1: [],
            country2: [],
        }

        for item in table_data["Metric"]:
            table_data[country1].append(row1[item])
            table_data[country2].append(row2[item])

        st.dataframe(
            pd.DataFrame(table_data),
            use_container_width=True,
            hide_index=True,
        )

    elif view == "🔢 Data":
        st.json(
            {
                country1: row1.to_dict(),
                country2: row2.to_dict(),
            }
        )

    elif view == "🗺️ Map":
        map_df = pd.DataFrame(
            {
                "Country": [country1, country2],
                metric: [
                    row1[metric],
                    row2[metric],
                ],
            }
        )

        fig = px.choropleth(
            map_df,
            locations="Country",
            locationmode="country names",
            color=metric,
            hover_name="Country",
            title=f"{metric} Map Comparison",
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0b1220",
            geo=dict(
                bgcolor="#0b1220",
                showframe=False,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    # PDF always contains chart + values,
    # regardless of the selected screen view.
    pdf = comparison_pdf(
        country1,
        country2,
        metric,
        view,
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
    )

    st.download_button(
        "📄 Generate Comparison PDF Report",
        data=pdf,
        file_name=(
            f"{safe_filename(country1)}_vs_"
            f"{safe_filename(country2)}_COVID.pdf"
        ),
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# TOP 10
# ============================================================

def show_top10():
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                🏆 TOP 10 COUNTRIES
            </div>
            Top countries based on selected metric
        </div>
        """,
        unsafe_allow_html=True,
    )

    default_metric_index = (
        COVID_METRICS.index(selected_metric_sidebar)
        if selected_metric_sidebar in COVID_METRICS
        else 0
    )

    metric = st.selectbox(
        "📌 SELECT METRIC",
        COVID_METRICS,
        index=default_metric_index,
        key="top10_metric",
    )

    view = st.selectbox(
        "👁️ SELECT VIEW",
        VIEW_TYPES,
        key="top10_view",
    )

    top = (
        df.sort_values(metric, ascending=False)
        .head(10)
        .copy()
    )

    top["Rank"] = range(1, 11)

    if view == "📊 Chart":
        fig = px.bar(
            top.sort_values(metric),
            x=metric,
            y="Country",
            orientation="h",
            text=metric,
            title=f"Top 10 Countries by {metric}",
        )

        make_plotly_dark(fig)
        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    elif view == "📈 Graph":
        fig = px.line(
            top.sort_values("Rank"),
            x="Country",
            y=metric,
            markers=True,
            text=metric,
            title=f"Top 10 - {metric} Graph",
        )

        make_plotly_dark(fig)
        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    elif view == "📋 Table":
        display = top[
            [
                "Rank",
                "Country",
                "Population",
                metric,
            ]
        ]

        st.dataframe(
            display,
            use_container_width=True,
            hide_index=True,
        )

    elif view == "🔢 Data":
        st.json(
            top[
                [
                    "Rank",
                    "Country",
                    metric,
                ]
            ].to_dict(orient="records")
        )

    elif view == "🗺️ Map":
        fig = px.choropleth(
            top,
            locations="Country",
            locationmode="country names",
            color=metric,
            hover_name="Country",
            title=f"Top 10 Countries - {metric}",
        )

        fig.update_layout(
            template="plotly_dark",
            paper_bgcolor="#0b1220",
            geo=dict(
                bgcolor="#0b1220",
                showframe=False,
            ),
        )

        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    pdf = top10_pdf(
        metric,
        view,
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
    )

    st.download_button(
        "📄 Generate Top 10 PDF Report",
        data=pdf,
        file_name=f"Top10_{safe_filename(metric)}.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# COMPLETE DATASET
# ============================================================

def show_dataset():
    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                📋 COMPLETE COVID-19 DATASET
            </div>
            Complete world COVID-19 dataset
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.info(
        f"""
        **Dataset Information**

        Total Countries/Territories: **{len(df)}**

        Selected Country: **{selected_country}**

        Sidebar Metric: **{selected_metric_sidebar}**

        Sidebar Chart: **{selected_chart_sidebar}**
        """
    )

    search = st.text_input(
        "🔎 Search Country",
        key="dataset_search",
    )

    filtered = df.copy()

    if search:
        filtered = filtered[
            filtered["Country"].str.contains(
                search,
                case=False,
                na=False,
            )
        ]

    st.dataframe(
        filtered[
            [
                "Country",
                "Population",
                "Confirmed",
                "Deaths",
                "Recovered",
                "Active",
                "Vaccinated",
                "Death Rate",
                "Recovery Rate",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    # Dataset page chart uses the sidebar-selected metric.
    chart_data = filtered.nlargest(
        min(10, len(filtered)),
        selected_metric_sidebar,
    )

    if not chart_data.empty:
        fig = px.bar(
            chart_data.sort_values(selected_metric_sidebar),
            x=selected_metric_sidebar,
            y="Country",
            orientation="h",
            text=selected_metric_sidebar,
            title=(
                f"Dataset View - Top Countries by "
                f"{selected_metric_sidebar}"
            ),
        )

        make_plotly_dark(fig)
        st.plotly_chart(
            fig,
            use_container_width=True,
        )

    pdf = dataset_pdf(
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
        search,
    )

    st.download_button(
        "📄 Generate Complete Dataset PDF",
        data=pdf,
        file_name="Complete_COVID_Dataset.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# PATIENT MODULE
# ============================================================

def show_patient_module():
    st.markdown(
        """
        <div class="dashboard-header">
            <h1>🧑‍⚕️ COVID PATIENT EDUCATIONAL MODULE</h1>
            <p>Patient information & COVID symptom checker</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="education-alert">
            ℹ️ <b>EDUCATIONAL PURPOSE ONLY</b>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                👤 PATIENT INFORMATION
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2, c3 = st.columns(3)

    with c1:
        patient_name = st.text_input(
            "👤 Patient Name",
            key="patient_name",
        )

    with c2:
        age = st.number_input(
            "🎂 Age",
            min_value=1,
            max_value=120,
            value=25,
            key="patient_age",
        )

    with c3:
        gender = st.selectbox(
            "⚧ Gender",
            ["Male", "Female", "Other"],
            key="patient_gender",
        )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                🤒 COVID SYMPTOMS CHECKER
            </div>
            Select the symptoms currently experienced.
        </div>
        """,
        unsafe_allow_html=True,
    )

    symptoms_list = [
        "🌡️ Fever",
        "😷 Cough",
        "🗣️ Sore Throat",
        "😴 Fatigue",
        "🤕 Headache",
        "💪 Body Pain",
        "👃 Loss of Taste or Smell",
        "🫁 Breathing Difficulty",
    ]

    selected_symptoms = []
    symptom_cols = st.columns(2)

    for i, symptom in enumerate(symptoms_list):
        with symptom_cols[i % 2]:
            checked = st.checkbox(
                symptom,
                key=f"symptom_{i}",
            )

            if checked:
                selected_symptoms.append(symptom)

    check = st.button(
        "🔍 CHECK SYMPTOMS",
        use_container_width=True,
        key="check_symptoms",
    )

    if check:
        if not selected_symptoms:
            st.info("No symptoms selected.")

        elif "🫁 Breathing Difficulty" in selected_symptoms:
            st.error(
                "🚨 Breathing difficulty can require urgent "
                "medical attention. Seek professional medical help."
            )

        else:
            st.warning(
                f"{len(selected_symptoms)} symptom(s) selected. "
                "Monitor symptoms and follow healthcare guidance."
            )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                💊 COVID CARE & RECOVERY
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    c1, c2 = st.columns(2)

    with c1:
        st.markdown(
            """
            ### 🏠 Care & Recovery Tips

            ✓ 🧼 Maintain hygiene

            ✓ 💧 Drink enough fluids

            ✓ 🛌 Take proper rest

            ✓ 📊 Monitor symptoms

            ✓ 👨‍⚕️ Follow healthcare guidance
            """
        )

    with c2:
        st.markdown(
            """
            ### 🚨 Seek Urgent Medical Help

            • 🫁 Breathing difficulty

            • ❤️ Chest pain or pressure

            • 🧠 Confusion or unusual tiredness

            • ⚠️ Severe weakness
            """
        )

    st.markdown(
        """
        <div class="section-card">
            <div class="section-title">
                📄 PATIENT REPORT
            </div>
            The PDF contains the complete patient educational
            report, selected symptoms, care tips, urgent warning
            signs, disclaimer, generation time, and current
            dashboard/sidebar selections.
        </div>
        """,
        unsafe_allow_html=True,
    )

    pdf = patient_pdf(
        patient_name if patient_name else "Not Provided",
        str(age),
        gender,
        selected_symptoms,
        selected_country,
        selected_metric_sidebar,
        selected_chart_sidebar,
        page,
    )

    st.download_button(
        "📄 GENERATE PATIENT REPORT",
        data=pdf,
        file_name="COVID_Patient_Report.pdf",
        mime="application/pdf",
        use_container_width=True,
    )


# ============================================================
# PAGE ROUTER
# ============================================================

if page == "🏠 Home":
    show_home()

elif page == "🗺️ Global COVID Map":
    show_global_map()

elif page == "⚖️ Compare Countries":
    show_comparison()

elif page == "🏆 Top 10 Countries":
    show_top10()

elif page == "📋 Complete Dataset":
    show_dataset()

elif page == "🏥 COVID Patient Module":
    show_patient_module()


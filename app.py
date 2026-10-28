
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st


# --------------------------------------------------
# Page setup
# --------------------------------------------------
st.set_page_config(
    page_title="World Literacy Explorer",
    page_icon="🌍",
    layout="wide",
)

st.title("🌍 World Literacy Explorer")
st.write(
    "Explore global literacy patterns, compare countries, "
    "and see how rates have changed over time."
)


# --------------------------------------------------
# Load data
# --------------------------------------------------
CSV_PATH = (
    Path(__file__).parent
    / "literate-and-illiterate-world-population"
    / "literate-and-illiterate-world-population.csv"
)


@st.cache_data
def load_data():
    if not CSV_PATH.exists():
        st.error(f"Could not find the data file: {CSV_PATH}")
        st.stop()

    data = pd.read_csv(CSV_PATH)

    required = {"Entity", "Year", "Code"}
    missing = required - set(data.columns)

    if missing:
        st.error(
            f"Missing columns: {', '.join(sorted(missing))}. "
            f"Found: {list(data.columns)}"
        )
        st.stop()

    literacy_col = next(
        (
            col for col in data.columns
            if "literate" in col.lower()
            and "illiterate" not in col.lower()
        ),
        None,
    )

    illiteracy_col = next(
        (
            col for col in data.columns
            if "illiterate" in col.lower()
        ),
        None,
    )

    if literacy_col is None and illiteracy_col is None:
        st.error("Could not identify the literacy data columns.")
        st.stop()

    data["Year"] = pd.to_numeric(data["Year"], errors="coerce")

    if literacy_col is not None:
        data["Literacy rate"] = pd.to_numeric(
            data[literacy_col], errors="coerce"
        )

    if illiteracy_col is not None:
        data["Illiteracy rate"] = pd.to_numeric(
            data[illiteracy_col], errors="coerce"
        )

    if "Literacy rate" not in data.columns:
        data["Literacy rate"] = 100 - data["Illiteracy rate"]

    if "Illiteracy rate" not in data.columns:
        data["Illiteracy rate"] = 100 - data["Literacy rate"]

    data = data.dropna(subset=["Entity", "Year"]).copy()
    data["Year"] = data["Year"].astype(int)
    data["Entity"] = data["Entity"].astype(str).str.strip()
    data["Code"] = data["Code"].astype("string").str.strip().str.upper()

    for col in ["Literacy rate", "Illiteracy rate"]:
        data.loc[~data[col].between(0, 100), col] = float("nan")

    return data


df = load_data()


# --------------------------------------------------
# Prepare country data
# --------------------------------------------------
country_df = df[
    df["Code"].notna()
    & df["Code"].str.fullmatch(r"[A-Z]{3}", na=False)
].copy()

if country_df.empty:
    st.error(
        "No valid three-letter country codes were found. "
        "The world map requires ISO alpha-3 country codes."
    )
    st.stop()

countries = sorted(country_df["Entity"].dropna().unique().tolist())
years = sorted(country_df["Year"].unique().tolist())
latest_year = years[-1]

china_name = next(
    (name for name in countries if name.casefold() == "china"),
    None,
)


# --------------------------------------------------
# Shared settings
# --------------------------------------------------
if "map_year" not in st.session_state:
    st.session_state.map_year = latest_year

if "compare_countries" not in st.session_state:
    st.session_state.compare_countries = countries[:2]

if "show_comparison" not in st.session_state:
    st.session_state.show_comparison = False

if "compare_year" not in st.session_state:
    st.session_state.compare_year = latest_year


# --------------------------------------------------
# Measure selection and contextual wording
# --------------------------------------------------
st.sidebar.header("World map settings")

measure = st.sidebar.radio(
    "Choose a measure",
    ["Literacy rate", "Illiteracy rate"],
)

is_literacy = measure == "Literacy rate"

if is_literacy:
    color_scale = [
        [0.00, "#542788"],
        [0.125, "#8073AC"],
        [0.25, "#B2ABD2"],
        [0.375, "#D8D3E5"],
        [0.50, "#F0F0F0"],
        [0.625, "#D9EFD8"],
        [0.75, "#91CF91"],
        [0.875, "#35964F"],
        [1.00, "#07552D"],
    ]

    map_title = "Global literacy rates"
    map_description = (
        "Purple indicates literacy below 50%; green indicates literacy "
        "above 50%. Darker shades represent values farther from 50%."
    )
    measure_description = (
        "the share of adults who can read and write a simple everyday sentence"
    )
    china_higher = "Higher literacy than China"
    china_lower = "Lower literacy than China"
    china_positive_explanation = (
        "A positive difference means a larger share of adults can read "
        "and write than in China."
    )
    china_negative_explanation = (
        "A negative difference means a smaller share of adults can read "
        "and write than in China."
    )
else:
    color_scale = [
        [0.00, "#084081"],
        [0.125, "#0868AC"],
        [0.25, "#2B8CBE"],
        [0.375, "#A6BDDB"],
        [0.50, "#F0F0F0"],
        [0.625, "#FEE0D2"],
        [0.75, "#FC9272"],
        [0.875, "#DE2D26"],
        [1.00, "#99000D"],
    ]

    map_title = "Global illiteracy rates"
    map_description = (
        "Blue indicates illiteracy below 50%; red indicates illiteracy "
        "above 50%. Darker shades represent values farther from 50%."
    )
    measure_description = (
        "the share of adults who cannot read and write a simple everyday sentence"
    )
    china_higher = "Higher illiteracy than China"
    china_lower = "Lower illiteracy than China"
    china_positive_explanation = (
        "A positive difference means a larger share of adults cannot "
        "read and write than in China."
    )
    china_negative_explanation = (
        "A negative difference means a smaller share of adults cannot "
        "read and write than in China."
    )


# --------------------------------------------------
# World map
# --------------------------------------------------
st.header(map_title)
st.caption(map_description)

map_data = country_df[
    (country_df["Year"] <= st.session_state.map_year)
    & country_df[measure].notna()
].copy()

# Use the latest observation available on or before the selected year.
map_data = (
    map_data.sort_values("Year")
    .drop_duplicates(subset=["Code"], keep="last")
)

if map_data.empty:
    st.warning("No observations are available for this year.")
else:
    fig_map = px.choropleth(
        map_data,
        locations="Code",
        locationmode="ISO-3",
        color=measure,
        hover_name="Entity",
        hover_data={
            "Code": False,
            "Year": True,
            measure: ":.0f",
        },
        color_continuous_scale=color_scale,
        range_color=(0, 100),
        labels={
            measure: f"{measure} (%)",
            "Year": "Observation year",
        },
    )

    fig_map.update_layout(
        height=560,
        margin=dict(l=0, r=0, t=10, b=0),
        geo=dict(
            showframe=False,
            showcoastlines=True,
            showland=True,
            landcolor="#D9D9D9",
            projection_type="natural earth",
        ),
        coloraxis_colorbar=dict(
            title=f"{measure} (%)",
            ticksuffix="%",
        ),
    )

    st.plotly_chart(fig_map, use_container_width=True)

st.slider(
    "Explore the world through time",
    min_value=years[0],
    max_value=latest_year,
    step=1,
    key="map_year",
)

st.caption(
    f"Map year: {st.session_state.map_year}. "
    "Grey indicates no available observation by that year. "
    "Hover over a country to see its actual observation year."
)


# --------------------------------------------------
# Country selection
# --------------------------------------------------
st.divider()
st.header("Compare countries")

st.multiselect(
    "1. Select two or more countries",
    options=countries,
    key="compare_countries",
    placeholder="Choose countries...",
)

include_china = st.checkbox(
    "Include China as a reference",
    value=True,
    help=(
        "Adds China to the chart and shows the percentage-point "
        "difference from China in the comparison table."
    ),
)

selected_countries = st.session_state.compare_countries

if include_china and china_name is None:
    st.warning(
        "China is not available among the countries with valid map codes."
    )

# --------------------------------------------------
# Context-aware comparison year
# --------------------------------------------------
# Keep the complete timeline, but do not offer years before
# any selected country has its first observation.
if selected_countries:
    first_years = (
        country_df[country_df["Entity"].isin(selected_countries)]
        .groupby("Entity")["Year"]
        .min()
    )

    comparison_min_year = (
        int(first_years.min()) if not first_years.empty else years[0]
    )
else:
    comparison_min_year = years[0]

comparison_min_year = max(comparison_min_year, years[0])

# If the selected countries change, keep the year within the valid range.
if (
    st.session_state.compare_year < comparison_min_year
    or st.session_state.compare_year > latest_year
):
    st.session_state.compare_year = latest_year

st.slider(
    "2. Choose the comparison year",
    min_value=comparison_min_year,
    max_value=latest_year,
    step=1,
    key="compare_year",
)

comparison_year = st.session_state.compare_year

if selected_countries:
    st.caption(
        f"Comparing rates for {comparison_year}. "
        "Countries use their latest available observation on or before "
        "this year; the table shows when each value was recorded."
    )
else:
    st.caption("Select countries to begin your comparison.")

if st.button("Show comparison", type="primary"):
    if len(selected_countries) < 2:
        st.warning("Please select at least two countries.")
        st.session_state.show_comparison = False
    else:
        st.session_state.show_comparison = True


# --------------------------------------------------
# Comparison results: point in time first
# --------------------------------------------------
if st.session_state.show_comparison:
    selected_countries = st.session_state.compare_countries

    if len(selected_countries) < 2:
        st.info("Select at least two countries to show a comparison.")
    else:
        table_countries = list(selected_countries)

        if (
            include_china
            and china_name is not None
            and china_name not in table_countries
        ):
            table_countries.append(china_name)

        eligible = country_df[
            country_df["Entity"].isin(table_countries)
            & (country_df["Year"] <= comparison_year)
            & country_df[measure].notna()
        ].copy()

        latest_values = (
            eligible.sort_values("Year")
            .drop_duplicates(subset=["Entity"], keep="last")
        )

        # Build a lookup for each country's latest value.
        value_lookup = {
            row["Entity"]: {
                "value": float(row[measure]),
                "year": int(row["Year"]),
            }
            for _, row in latest_values.iterrows()
        }

        china_record = (
            value_lookup.get(china_name)
            if include_china and china_name is not None
            else None
        )

        china_value = (
            china_record["value"] if china_record is not None else None
        )

        st.subheader(f"Rates in {comparison_year}")

        st.caption(
            f"The table compares {measure.lower()} "
            f"({measure_description})."
        )

        result_rows = []

        for country in table_countries:
            record = value_lookup.get(country)

            if record is None:
                display_rate = "No data"
                observation_year = "—"
                numeric_rate = None
                rate_is_older = False
            else:
                numeric_rate = record["value"]
                observation_year = record["year"]
                rate_is_older = record["year"] != comparison_year

                display_rate = f"{numeric_rate:.0f}%"
                if rate_is_older:
                    display_rate += "*"

            row = {
                "Country": country,
                measure: display_rate,
                "Observation year": observation_year,
                "_numeric_rate": numeric_rate,
                "_older": rate_is_older,
            }

            if include_china and china_name is not None:
                if country == china_name:
                    difference_display = "Reference"
                elif (
                    record is not None
                    and china_value is not None
                ):
                    difference = numeric_rate - china_value
                    difference_display = f"{difference:+.0f} pp"

                    china_is_older = (
                        china_record["year"] != comparison_year
                    )

                    if rate_is_older or china_is_older:
                        difference_display += "*"
                else:
                    difference_display = "—"

                row["Difference vs. China (percentage points)"] = (
                    difference_display
                )

            result_rows.append(row)

        result = pd.DataFrame(result_rows)

        # Sort numerically while retaining whole-number display values.
        result = result.sort_values(
            "_numeric_rate",
            ascending=False,
            na_position="last",
        )

        visible_columns = ["Country", measure, "Observation year"]

        if include_china and china_name is not None:
            visible_columns.append(
                "Difference vs. China (percentage points)"
            )

        st.dataframe(
            result[visible_columns],
            use_container_width=True,
            hide_index=True,
        )

        st.caption(
            f"* The value uses the latest available observation on or "
            f"before {comparison_year}, rather than an observation "
            f"recorded in {comparison_year}. A difference vs. China is "
            f"also marked when either country's observation is from an "
            f"earlier year. 'pp' means percentage points."
        )

        if include_china and china_name is not None:
            st.caption(
                china_positive_explanation + " "
                + china_negative_explanation
            )

        # --------------------------------------------------
        # Historical trends second
        # --------------------------------------------------
        st.divider()
        st.subheader("Explore trends over time")

        chart_countries = list(selected_countries)

        if (
            include_china
            and china_name is not None
            and china_name not in chart_countries
        ):
            chart_countries.append(china_name)

        trend_data = country_df[
            country_df["Entity"].isin(chart_countries)
        ][["Entity", "Year", measure]].dropna()

        if trend_data.empty:
            st.info("No historical observations are available.")
        else:
            fig_comparison = px.line(
                trend_data,
                x="Year",
                y=measure,
                color="Entity",
                markers=True,
                labels={
                    "Year": "Year",
                    measure: f"{measure} (%)",
                    "Entity": "Country",
                },
                title=f"{measure} over time",
            )

            for trace in fig_comparison.data:
                trace.update(
                    hovertemplate=(
                        "%{x}<br>"
                        + trace.name
                        + ": %{y:.0f}%<extra></extra>"
                    )
                )

                if (
                    include_china
                    and china_name is not None
                    and trace.name == china_name
                ):
                    trace.update(line=dict(dash="dash"))

            fig_comparison.update_layout(
                yaxis=dict(
                    title=f"{measure} (%)",
                    range=[0, 100],
                    ticksuffix="%",
                ),
                xaxis_title="Year",
                legend_title="Country",
                hovermode="x unified",
            )

            st.plotly_chart(
                fig_comparison,
                use_container_width=True,
            )


# --------------------------------------------------
# Dataset notes
# --------------------------------------------------
with st.expander("About the data"):
    st.write(
        f"""
        The selected measure is {measure.lower()}: {measure_description}.

        Historical observations may use different definitions and
        estimation methods. Some early estimates are indirect, while
        more recent data generally comes from surveys or censuses.

        Missing observations are not treated as zero. The map and
        comparison table use the latest available observation on or
        before the selected year. Countries may therefore have
        observations from different years.

        China is an optional reference for the country comparison.
        It does not determine the map's colors or country selections.
        """
    )

st.caption(
    "Source: UNESCO and other historical and contemporary sources, "
    "compiled by Our World in Data."
)

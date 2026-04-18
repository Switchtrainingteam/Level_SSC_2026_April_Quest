import streamlit as st
import pandas as pd
import plotly.express as px

# -----------------------------------------------------------------------------
# 1. PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(page_title="SSC 2026 Explorer", layout="wide")

# Custom CSS for metric cards
st.markdown("""
<style>
    div[data-testid="metric-container"] {
        background-color: #f0f2f6;
        border: 1px solid #d6d6d6;
        padding: 10px;
        border-radius: 5px;
    }
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# 2. DATA LOADING (Dynamic from CSV files)
# -----------------------------------------------------------------------------
@st.cache_data
def load_data():
    # --- A. REGIONAL PERFORMANCE ---
    df_regional = pd.read_csv("Explorer Quest April 2026.xlsx - Region Performance Comparison .csv")
    # Clean Data
    df_regional = df_regional[df_regional['Region'] != 'Grand Total'] # Drop Grand Total
    df_regional['Region'] = df_regional['Region'].str.strip() # Fix trailing spaces (e.g., "Sarawak ")
    df_regional = df_regional.rename(columns={
        'Sum of Pass': 'Pass',
        'Sum of Fail': 'Fail',
        'Sum of Total Headcount': 'Total Headcount'
    })

    # --- B. OUTLET PERFORMANCE ---
    regions = ['Central', 'East Coast', 'Northern', 'Southern', 'Sabah', 'Sarawak']
    outlet_dfs = []
    
    for region in regions:
        filename = f"Explorer Quest April 2026.xlsx - {region}.csv"
        df_temp = pd.read_csv(filename)
        
        # Handle variations in column names ('Outlet' vs 'Outlets')
        outlet_col = 'Outlets' if 'Outlets' in df_temp.columns else 'Outlet'
        
        # Clean and rename
        df_temp = df_temp.rename(columns={
            outlet_col: 'Outlet',
            'Sum of Pass': 'Pass',
            'Sum of Fail': 'Fail',
            'Sum of Total Crew': 'Total'
        })
        df_temp['Region'] = region
        
        # Drop "Total" and "Grand Total" rows (e.g., Sarawak has both)
        df_temp = df_temp[~df_temp['Outlet'].isin(['Total', 'Grand Total'])]
        outlet_dfs.append(df_temp)
        
    # Combine all regions into one DataFrame
    df_outlets = pd.concat(outlet_dfs, ignore_index=True)

    # --- C. LOB COMPARISON ---
    df_lob = pd.read_csv("Explorer Quest April 2026.xlsx - LOB COMPARISON.csv")
    df_lob = df_lob[df_lob['LOB'] != 'Grand Total'] # Drop Grand total
    
    # Rename columns to remove "Sum of " and change "LOB" to "Result"
    rename_dict = {col: col.replace('Sum of ', '') for col in df_lob.columns}
    rename_dict['LOB'] = 'Result'
    df_lob = df_lob.rename(columns=rename_dict)
    df_lob.columns = df_lob.columns.str.strip() # Ensure no trailing spaces in region names

    return df_regional, df_outlets, df_lob

# Load the data
try:
    df_regional, df_outlets, df_lob = load_data()
except FileNotFoundError as e:
    st.error(f"Error loading data: {e}. Please ensure the CSV files are in the same folder as this script.")
    st.stop()

# Function to clean and structure LOB data
def process_lob_data(df):
    # Melt to long format
    df_long = df.melt(id_vars=['Result'], var_name='Region', value_name='Count')
    
    # Extract Status (Pass/Fail) and Product
    df_long['Status'] = df_long['Result'].apply(lambda x: 'Pass' if '(Pass)' in x else 'Fail')
    df_long['Product'] = df_long['Result'].apply(lambda x: x.split(' (')[0])
    
    # Convert Count to numeric just in case, and filter out 0 counts
    df_long['Count'] = pd.to_numeric(df_long['Count'], errors='coerce').fillna(0)
    df_long = df_long[df_long['Count'] > 0]
    
    return df_long

# -----------------------------------------------------------------------------
# 3. SIDEBAR NAVIGATION
# -----------------------------------------------------------------------------
with st.sidebar:
    # Use a try-except block just in case the image is missing
    try:
        st.image("Main Banner.png")
    except:
        pass # Skips image if not found
    
    st.header("SSC 2026 : Explorer iPhone & Apple Watch")
    view_selection = st.selectbox(
        "Select Dataset:",
        ["Regional Performance", "Outlet Performance", "LOB Comparison"]
    )
    st.markdown("---")
    st.caption("© 2026 SSC 2026 | Insight Team")

# -----------------------------------------------------------------------------
# 4. MAIN LOGIC
# -----------------------------------------------------------------------------

st.title(f"📊 {view_selection}")

# Initialize variables
fig = None
display_df = None
total_vol = 0
total_pass = 0
total_fail = 0

# --- LOGIC: REGIONAL VIEW ---
if view_selection == "Regional Performance":
    display_df = df_regional
    
    total_pass = display_df['Pass'].sum()
    total_fail = display_df['Fail'].sum()
    total_vol = display_df['Total Headcount'].sum()
    
    # Chart
    chart_df = display_df.melt(id_vars=['Region'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
    fig = px.bar(chart_df, x='Region', y='Count', color='Status', barmode='group',
                 text_auto=True,
                 color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'},
                 title="Pass vs Fail by Region")

# --- LOGIC: OUTLET VIEW ---
elif view_selection == "Outlet Performance":
    
    selected_region_filter = st.selectbox("Filter by Region:", ["All"] + list(df_outlets['Region'].unique()))
    
    if selected_region_filter != "All":
        display_df = df_outlets[df_outlets['Region'] == selected_region_filter]
    else:
        display_df = df_outlets

    total_pass = display_df['Pass'].sum()
    total_fail = display_df['Fail'].sum()
    total_vol = display_df['Total'].sum()
    
    # Chart
    chart_df = display_df.melt(id_vars=['Outlet'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
    
    # Sort by Volume so biggest outlets are first
    chart_df = chart_df.sort_values(by='Count', ascending=False)
    
    fig = px.bar(chart_df, x='Outlet', y='Count', color='Status', barmode='group',
                 text_auto=True,
                 color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'},
                 title=f"Outlet Performance ({selected_region_filter})")

# --- LOGIC: LOB VIEW ---
elif view_selection == "LOB Comparison":
    processed_lob = process_lob_data(df_lob)
    display_df = processed_lob[['Region', 'Product', 'Status', 'Count']]
    
    total_pass = processed_lob[processed_lob['Status'] == 'Pass']['Count'].sum()
    total_fail = processed_lob[processed_lob['Status'] == 'Fail']['Count'].sum()
    total_vol = total_pass + total_fail
    
    # Chart
    fig = px.bar(processed_lob, x='Product', y='Count', color='Status', 
                 color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'},
                 text_auto=True,
                 facet_col='Region', title="Product Performance by Region")
    fig.update_xaxes(matches=None) 

# -----------------------------------------------------------------------------
# 5. DASHBOARD LAYOUT (KPIs -> Chart -> Table)
# -----------------------------------------------------------------------------

pass_rate = (total_pass / total_vol) * 100 if total_vol > 0 else 0

# Row 1: KPI Cards
st.subheader("1. Key Performance Indicators")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Volume", f"{int(total_vol):,}")
col2.metric("Total Pass", f"{int(total_pass):,}")
col3.metric("Total Fail", f"{int(total_fail):,}")
col4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.markdown("---")

# Row 2: Charts
st.subheader("2. Graphical Analysis")
if fig:
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")

# Row 3: Data Table
st.subheader("3. Source Data")
with st.expander("View Data Table", expanded=True):
    st.dataframe(display_df, use_container_width=True)# --- REGION PERFORMANCE ---
csv_regional = """Region,Sum of Pass,Sum of Fail,Sum of Total Headcount
Central,35,97,132
East Coast,26,19,45
Northern,62,65,127
Sabah,21,45,66
Sarawak ,48,12,60
Southern,59,44,103
Grand Total,251,282,533""".strip()

# --- CENTRAL OUTLETS ---
csv_central = """Outlets,Sum of Pass,Sum of Fail,Sum of Total Crew
AP,4,1,5
BG,0,4,4
BK,4,0,4
BV,0,5,5
EK,0,5,5
EV,3,2,5
LY,0,5,5
MF,3,3,6
MT,3,3,6
PR,0,5,5
PS,1,4,5
PU,0,5,5
PY,2,14,16
QS,3,2,5
SA,1,6,7
SL,1,4,5
SWKLAA,1,2,3
SWKLGC,0,4,4
SWSGKG,3,0,3
SWSGKW,1,4,5
SWSGSY,3,2,5
TG,2,5,7
UK,0,1,1
UP,0,5,5
WW,0,6,6
Grand Total,35,97,132""".strip()

# --- NORTHERN OUTLETS ---
csv_northern = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
AC,5,2,7
AJ,5,2,7
AL,6,2,8
AR,2,6,8
AS,1,4,5
BM,3,2,5
GT,8,7,15
KI,3,2,5
LW,4,0,4
PG,0,7,7
QB,10,5,15
SQ,3,2,5
SU,4,9,13
SWKDSW,1,3,4
TM,0,6,6
TS,1,6,7
VM,6,0,6
Grand Total,62,65,127""".strip()

# --- SOUTHERN OUTLETS ---
csv_southern = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
BP,3,4,7
JB,6,5,11
KJ,2,5,7
KP,3,1,4
MP,3,1,4
NL,7,1,8
PD,5,7,12
SC,4,2,6
SG,2,4,6
SR,5,2,7
SWJHBX,2,2,4
SWJHDS,4,1,5
SWJHEL,2,3,5
SWJHGP,3,2,5
SWNSLJ,4,0,4
SWNSLT,1,2,3
WE,3,2,5
Grand Total,59,44,103""".strip()

# --- EAST COAST OUTLETS ---
csv_east = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
EC,3,4,7
KA,1,6,7
KM,4,2,6
KT,4,0,4
MM,3,0,3
SWPHCH,4,0,4
SWPHLK,2,2,4
SWTRGD,3,2,5
SWTRMY,2,3,5
Grand Total,26,19,45""".strip()

# --- SABAH OUTLETS ---
csv_sabah = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
HS,5,1,6
IG,4,14,18
PQ,6,1,7
SS,0,11,11
SWLBFP,0,5,5
SWSBCC,0,3,3
SWSBCM,2,3,5
SWSBKK,1,3,4
TW,4,3,7
Grand Total,22,44,66""".strip()

# --- SARAWAK OUTLETS ---
csv_sarawak = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
CK,5,2,7
MB,4,1,5
MR,2,3,5
SB,3,2,5
SP,11,1,12
SWSWDM,5,0,5
SWSWER,5,0,5
SY,4,2,6
Total,48,12,60
VC,9,1,10
Grand Total,96,24,120""".strip()

# -----------------------------------------------------------------------------
# 3. DATA PROCESSING FUNCTIONS
# -----------------------------------------------------------------------------

def clean_excel_pivot_csv(df):
    """
    Cleans CSVs that come from Excel Pivot Tables:
    1. Removes 'Grand Total' and 'Total' rows.
    2. Removes 'Sum of ' prefix from value columns.
    """
    # Remove Grand Total and subtotals (like the "Total" row in Sarawak)
    df = df[~df.iloc[:, 0].isin(['Grand Total', 'Total'])].copy()
    
    # Rename columns: Remove "Sum of "
    df.columns = df.columns.str.replace('Sum of ', '')
    
    return df

@st.cache_data
def load_and_clean_data():
    # --- 1. Regional Data ---
    df_reg = pd.read_csv(io.StringIO(csv_regional), skipinitialspace=True)
    df_reg = clean_excel_pivot_csv(df_reg)
    if 'Row Labels' in df_reg.columns:
        df_reg = df_reg.rename(columns={'Row Labels': 'Region'})
    df_reg['Region'] = df_reg['Region'].str.strip()
    
    # --- 2. LOB Data ---
    df_lob = pd.read_csv(io.StringIO(csv_lob), skipinitialspace=True)
    df_lob = clean_excel_pivot_csv(df_lob)
    
    if 'LOB' in df_lob.columns:
        df_lob = df_lob.rename(columns={'LOB': 'Result'})
    elif 'Row Labels' in df_lob.columns:
        df_lob = df_lob.rename(columns={'Row Labels': 'Result'})
    
    # --- 3. Outlet Data ---
    # Helper to process outlet files
    def process_outlet_file(csv_data, region_name):
        df = pd.read_csv(io.StringIO(csv_data), skipinitialspace=True)
        df = clean_excel_pivot_csv(df)
        
        # Rename first column to 'Outlet'
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'Outlet'})
        
        df['Region'] = region_name
        return df

    # Process all outlet files
    outlets = [
        process_outlet_file(csv_central, 'Central'),
        process_outlet_file(csv_northern, 'Northern'),
        process_outlet_file(csv_southern, 'Southern'),
        process_outlet_file(csv_east, 'East Coast'),
        process_outlet_file(csv_sabah, 'Sabah'),
        process_outlet_file(csv_sarawak, 'Sarawak')
    ]
    
    df_outlet_all = pd.concat(outlets, ignore_index=True)
    
    # Ensure numeric columns (Handle blank values natively)
    cols_to_numeric = ['Pass', 'Fail', 'Total Crew', 'Total Headcount']
    
    # Clean Outlet Data Types
    for c in cols_to_numeric:
        if c in df_outlet_all.columns:
            df_outlet_all[c] = pd.to_numeric(df_outlet_all[c], errors='coerce').fillna(0)

    # Clean Regional Data Types
    for c in cols_to_numeric:
        if c in df_reg.columns:
            df_reg[c] = pd.to_numeric(df_reg[c], errors='coerce').fillna(0)

    return df_reg, df_lob, df_outlet_all

def process_lob_data(df):
    # Melt from wide (Regions in columns) to long
    region_cols = [c for c in df.columns if c != 'Result']
    
    df_long = df.melt(id_vars=['Result'], value_vars=region_cols, var_name='Region', value_name='Count')
    
    # Ensure Count is numeric
    df_long['Count'] = pd.to_numeric(df_long['Count'], errors='coerce').fillna(0)
    
    # Extract Status and Product
    df_long['Status'] = df_long['Result'].apply(lambda x: 'Pass' if '(Pass)' in str(x) else 'Fail')
    df_long['Product'] = df_long['Result'].apply(lambda x: str(x).split(' (')[0])
    
    return df_long

# Load Data
try:
    df_regional, df_lob, df_outlet = load_and_clean_data()
except Exception as e:
    st.error(f"Error processing data: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("SSC 2026 Dashboard")
    st.write("Explorer Quest - April 2026") # Updated to April
    
    view_selection = st.selectbox(
        "Select Dataset:",
        ["Regional Performance", "Outlet Performance", "LOB Comparison"]
    )
    
    st.markdown("---")
    st.caption("© 2026 Insight Team")

# -----------------------------------------------------------------------------
# 5. MAIN LOGIC
# -----------------------------------------------------------------------------

st.title(f"📊 {view_selection}")

active_df = pd.DataFrame()
chart_fig = None
total_pass = 0
total_fail = 0
total_vol = 0

if view_selection == "Regional Performance":
    active_df = df_regional
    
    vol_col = 'Total Headcount' if 'Total Headcount' in active_df.columns else active_df.columns[-1]
    total_pass = active_df['Pass'].sum()
    total_fail = active_df['Fail'].sum()
    total_vol = active_df[vol_col].sum()
    
    # Chart
    chart_df = active_df.melt(id_vars=['Region'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
    chart_fig = px.bar(chart_df, x='Region', y='Count', color='Status', barmode='group',
                       color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}, 
                       title="Pass vs Fail by Region")

elif view_selection == "Outlet Performance":
    active_df = df_outlet
    
    # Filter
    regions_list = sorted(active_df['Region'].unique().tolist())
    selected_region = st.sidebar.multiselect("Filter by Region:", regions_list, default=regions_list[0] if regions_list else None)
    
    if selected_region:
        filtered_df = active_df[active_df['Region'].isin(selected_region)]
        title_text = f"Outlet Performance ({', '.join(selected_region)})"
    else:
        filtered_df = active_df
        title_text = "Outlet Performance (All)"
    
    # Metrics
    if not filtered_df.empty:
        total_pass = filtered_df['Pass'].sum()
        total_fail = filtered_df['Fail'].sum()
        if 'Total Crew' in filtered_df.columns:
            total_vol = filtered_df['Total Crew'].sum()
        else:
            total_vol = total_pass + total_fail
        
        # Enhanced Chart layout & Sort Data so highest values are prominent
        chart_df = filtered_df.melt(id_vars=['Outlet'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
        chart_df = chart_df.sort_values(by=['Count', 'Status'], ascending=[False, True])
        
        chart_fig = px.bar(chart_df, x='Outlet', y='Count', color='Status', barmode='group',
                           color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}, 
                           title=title_text)

elif view_selection == "LOB Comparison":
    active_df = df_lob
    processed_lob = process_lob_data(df_lob)
    
    total_pass = processed_lob[processed_lob['Status'] == 'Pass']['Count'].sum()
    total_fail = processed_lob[processed_lob['Status'] == 'Fail']['Count'].sum()
    total_vol = total_pass + total_fail
    
    # Chart - Use consistent coloring
    chart_fig = px.bar(processed_lob, x='Product', y='Count', color='Region',
                       facet_row='Status',
                       title="Product Performance: Regional Breakdown")
    chart_fig.update_layout(height=600)

# Calculate Pass Rate safely
pass_rate = (total_pass / total_vol) * 100 if total_vol > 0 else 0

# -----------------------------------------------------------------------------
# 6. LAYOUT
# -----------------------------------------------------------------------------

# ROW 1: KPIs
st.subheader("1. Key Performance Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Volume", f"{int(total_vol)}")
c2.metric("Total Pass", f"{int(total_pass)}")
c3.metric("Total Fail", f"{int(total_fail)}")
c4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.markdown("---")

# ROW 2: CHART
st.subheader("2. Graphical Analysis")
if chart_fig:
    st.plotly_chart(chart_fig, use_container_width=True)
else:
    st.info("Select a region to view outlet performance.")

st.markdown("---")

# ROW 3: ENHANCED TABLE WITH DOWNLOAD BUTTON
st.subheader("3. Data Table")

display_df = active_df.copy()

# Limit to filtered data for outlets view
if view_selection == "Outlet Performance" and 'filtered_df' in locals():
    display_df = filtered_df.copy()

if not display_df.empty and 'Pass' in display_df.columns and 'Fail' in display_df.columns:
    
    # Calculate Total correctly and assign Pass Rate
    display_df['Total'] = display_df['Pass'] + display_df['Fail']
    display_df['Pass Rate (%)'] = (display_df['Pass'] / display_df['Total'] * 100).fillna(0).round(1)
    
    # Sort by performance (ascending=False puts best performance on top)
    display_df = display_df.sort_values("Pass Rate (%)", ascending=False)
    
    st.dataframe(
        display_df.style.format({'Pass Rate (%)': '{:.1f}%'})
        .background_gradient(cmap='RdYlGn', subset=['Pass Rate (%)'])
        .highlight_max(subset=['Pass'], color='#d4edda')
        .highlight_max(subset=['Fail'], color='#f8d7da'),
        use_container_width=True
    )
    
    # Add Download Button for the processed subset!
    csv_export = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download This Table as CSV",
        data=csv_export,
        file_name='ssc_April_2026_data.csv',
        mime='text/csv',
    )
else:
    st.dataframe(display_df, use_container_width=True)
    
    # Fallback download button for raw table
    csv_export = display_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Download This Table as CSV",
        data=csv_export,
        file_name='ssc_April_2026_data.csv',
        mime='text/csv',
    )# --- REGION PERFORMANCE ---
csv_regional = """Region,Sum of Pass,Sum of Fail,Sum of Total Headcount
Central,35,97,132
East Coast,26,19,45
Northern,62,65,127
Sabah,21,45,66
Sarawak ,48,12,60
Southern,59,44,103
Grand Total,251,282,533""".strip()

# --- CENTRAL OUTLETS ---
csv_central = """Outlets,Sum of Pass,Sum of Fail,Sum of Total Crew
AP,4,1,5
BG,0,4,4
BK,4,0,4
BV,0,5,5
EK,0,5,5
EV,3,2,5
LY,0,5,5
MF,3,3,6
MT,3,3,6
PR,0,5,5
PS,1,4,5
PU,0,5,5
PY,2,14,16
QS,3,2,5
SA,1,6,7
SL,1,4,5
SWKLAA,1,2,3
SWKLGC,0,4,4
SWSGKG,3,0,3
SWSGKW,1,4,5
SWSGSY,3,2,5
TG,2,5,7
UK,0,1,1
UP,0,5,5
WW,0,6,6
Grand Total,35,97,132""".strip()

# --- NORTHERN OUTLETS ---
csv_northern = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
AC,5,2,7
AJ,5,2,7
AL,6,2,8
AR,2,6,8
AS,1,4,5
BM,3,2,5
GT,8,7,15
KI,3,2,5
LW,4,0,4
PG,0,7,7
QB,10,5,15
SQ,3,2,5
SU,4,9,13
SWKDSW,1,3,4
TM,,6,6
TS,1,6,7
VM,6,0,6
Grand Total,62,65,127""".strip()

# --- SOUTHERN OUTLETS ---
csv_southern = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
BP,3,4,7
JB,6,5,11
KJ,2,5,7
KP,3,1,4
MP,3,1,4
NL,7,1,8
PD,5,7,12
SC,4,2,6
SG,2,4,6
SR,5,2,7
SWJHBX,2,2,4
SWJHDS,4,1,5
SWJHEL,2,3,5
SWJHGP,3,2,5
SWNSLJ,4,0,4
SWNSLT,1,2,3
WE,3,2,5
Grand Total,59,44,103""".strip()

# --- EAST COAST OUTLETS ---
csv_east = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
EC,3,4,7
KA,1,6,7
KM,4,2,6
KT,4,0,4
MM,3,0,3
SWPHCH,4,0,4
SWPHLK,2,2,4
SWTRGD,3,2,5
SWTRMY,2,3,5
Grand Total,26,19,45""".strip()

# --- SABAH OUTLETS ---
csv_sabah = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
HS,5,1,6
IG,4,14,18
PQ,6,1,7
SS,0,11,11
SWLBFP,0,5,5
SWSBCC,0,3,3
SWSBCM,2,3,5
SWSBKK,1,3,4
TW,4,3,7
Grand Total,22,44,66""".strip()

# --- SARAWAK OUTLETS ---
csv_sarawak = """Outlet,Sum of Pass,Sum of Fail,Sum of Total Crew
CK,5,2,7
MB,4,1,5
MR,2,3,5
SB,3,2,5
SP,11,1,12
SWSWDM,5,0,5
SWSWER,5,0,5
SY,4,2,6
Total,48,12,60
VC,9,1,10
Grand Total,96,24,120""".strip()

# -----------------------------------------------------------------------------
# 3. DATA PROCESSING FUNCTIONS
# -----------------------------------------------------------------------------

def clean_excel_pivot_csv(df):
    """
    Cleans CSVs that come from Excel Pivot Tables:
    1. Removes 'Grand Total' and 'Total' rows safely.
    2. Removes 'Sum of ' prefix from value columns.
    """
    # Remove Grand Total and Total rows (usually at the bottom, or inline)
    df = df[~df.iloc[:, 0].isin(['Grand Total', 'Total'])].copy()
    
    # Rename columns: Remove "Sum of "
    df.columns = df.columns.str.replace('Sum of ', '')
    
    return df

@st.cache_data
def load_and_clean_data():
    # --- 1. Regional Data ---
    df_reg = pd.read_csv(io.StringIO(csv_regional), skipinitialspace=True)
    df_reg = clean_excel_pivot_csv(df_reg)
    if 'Row Labels' in df_reg.columns:
        df_reg = df_reg.rename(columns={'Row Labels': 'Region'})
    df_reg['Region'] = df_reg['Region'].str.strip()
    
    # --- 2. LOB Data ---
    df_lob = pd.read_csv(io.StringIO(csv_lob), skipinitialspace=True)
    df_lob = clean_excel_pivot_csv(df_lob)
    
    if 'LOB' in df_lob.columns:
        df_lob = df_lob.rename(columns={'LOB': 'Result'})
    elif 'Row Labels' in df_lob.columns:
        df_lob = df_lob.rename(columns={'Row Labels': 'Result'})
    
    # --- 3. Outlet Data ---
    # Helper to process outlet files
    def process_outlet_file(csv_data, region_name):
        df = pd.read_csv(io.StringIO(csv_data), skipinitialspace=True)
        df = clean_excel_pivot_csv(df)
        
        # Rename first column to 'Outlet' (handles 'Row Labels', 'Outlets', etc.)
        first_col = df.columns[0]
        df = df.rename(columns={first_col: 'Outlet'})
        
        df['Region'] = region_name
        return df

    # Process all outlet files
    outlets = [
        process_outlet_file(csv_central, 'Central'),
        process_outlet_file(csv_northern, 'Northern'),
        process_outlet_file(csv_southern, 'Southern'),
        process_outlet_file(csv_east, 'East Coast'),
        process_outlet_file(csv_sabah, 'Sabah'),
        process_outlet_file(csv_sarawak, 'Sarawak')
    ]
    
    df_outlet_all = pd.concat(outlets, ignore_index=True)
    
    # Ensure numeric columns (Pivot exports sometimes have missing values, handled by coerce and fillna)
    cols_to_numeric = ['Pass', 'Fail', 'Total Crew', 'Total Headcount']
    
    # Clean Outlet Data Types
    for c in cols_to_numeric:
        if c in df_outlet_all.columns:
            df_outlet_all[c] = pd.to_numeric(df_outlet_all[c], errors='coerce').fillna(0)

    # Clean Regional Data Types
    for c in cols_to_numeric:
        if c in df_reg.columns:
            df_reg[c] = pd.to_numeric(df_reg[c], errors='coerce').fillna(0)

    return df_reg, df_lob, df_outlet_all

def process_lob_data(df):
    # Melt from wide (Regions in columns) to long
    # Identify region columns (all columns except 'Result')
    region_cols = [c for c in df.columns if c != 'Result']
    
    df_long = df.melt(id_vars=['Result'], value_vars=region_cols, var_name='Region', value_name='Count')
    
    # Ensure Count is numeric
    df_long['Count'] = pd.to_numeric(df_long['Count'], errors='coerce').fillna(0)
    
    # Extract Status and Product
    df_long['Status'] = df_long['Result'].apply(lambda x: 'Pass' if '(Pass)' in str(x) else 'Fail')
    df_long['Product'] = df_long['Result'].apply(lambda x: str(x).split(' (')[0])
    
    return df_long

# Load Data
try:
    df_regional, df_lob, df_outlet = load_and_clean_data()
except Exception as e:
    st.error(f"Error processing data: {e}")
    st.stop()

# -----------------------------------------------------------------------------
# 4. SIDEBAR
# -----------------------------------------------------------------------------
with st.sidebar:
    st.header("SSC 2026 Dashboard")
    st.write("Explorer Quest - Apr 2026") # Updated to April
    
    view_selection = st.selectbox(
        "Select Dataset:",
        ["Regional Performance", "Outlet Performance", "LOB Comparison"]
    )
    
    st.markdown("---")
    st.caption("© 2026 Insight Team")

# -----------------------------------------------------------------------------
# 5. MAIN LOGIC
# -----------------------------------------------------------------------------

st.title(f"📊 {view_selection}")

active_df = pd.DataFrame()
chart_fig = None
total_pass = 0
total_fail = 0
total_vol = 0

if view_selection == "Regional Performance":
    active_df = df_regional
    
    # Use "Total Headcount" as volume for Regional
    vol_col = 'Total Headcount' if 'Total Headcount' in active_df.columns else active_df.columns[-1]
    
    total_pass = active_df['Pass'].sum()
    total_fail = active_df['Fail'].sum()
    total_vol = active_df[vol_col].sum()
    
    # Chart
    chart_df = active_df.melt(id_vars=['Region'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
    chart_fig = px.bar(chart_df, x='Region', y='Count', color='Status', barmode='group',
                       color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}, 
                       title="Pass vs Fail by Region")

elif view_selection == "Outlet Performance":
    active_df = df_outlet
    
    # Filter
    regions_list = sorted(active_df['Region'].unique().tolist())
    selected_region = st.sidebar.multiselect("Filter by Region:", regions_list, default=regions_list[0] if regions_list else None)
    
    if selected_region:
        filtered_df = active_df[active_df['Region'].isin(selected_region)]
        title_text = f"Outlet Performance ({', '.join(selected_region)})"
    else:
        filtered_df = active_df
        title_text = "Outlet Performance (All)"
    
    # Metrics
    if not filtered_df.empty:
        total_pass = filtered_df['Pass'].sum()
        total_fail = filtered_df['Fail'].sum()
        # For outlets, use Pass + Fail or Total Crew if available
        if 'Total Crew' in filtered_df.columns:
            total_vol = filtered_df['Total Crew'].sum()
        else:
            total_vol = total_pass + total_fail
        
        # Chart
        chart_df = filtered_df.melt(id_vars=['Outlet'], value_vars=['Pass', 'Fail'], var_name='Status', value_name='Count')
        chart_df = chart_df.sort_values(by='Count', ascending=False)
        
        chart_fig = px.bar(chart_df, x='Outlet', y='Count', color='Status', barmode='group',
                           color_discrete_map={'Pass': '#00CC96', 'Fail': '#EF553B'}, 
                           title=title_text)

elif view_selection == "LOB Comparison":
    active_df = df_lob
    processed_lob = process_lob_data(df_lob)
    
    total_pass = processed_lob[processed_lob['Status'] == 'Pass']['Count'].sum()
    total_fail = processed_lob[processed_lob['Status'] == 'Fail']['Count'].sum()
    total_vol = total_pass + total_fail
    
    # Chart
    chart_fig = px.bar(processed_lob, x='Product', y='Count', color='Region',
                       facet_row='Status',
                       title="Product Performance: Regional Breakdown")
    chart_fig.update_layout(height=600)

# Calculate Pass Rate safely
pass_rate = (total_pass / total_vol) * 100 if total_vol > 0 else 0

# -----------------------------------------------------------------------------
# 6. LAYOUT
# -----------------------------------------------------------------------------

# ROW 1: KPIs
st.subheader("1. Key Performance Indicators")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Total Volume", f"{int(total_vol)}")
c2.metric("Total Pass", f"{int(total_pass)}")
c3.metric("Total Fail", f"{int(total_fail)}")
c4.metric("Pass Rate", f"{pass_rate:.1f}%")

st.markdown("---")

# ROW 2: CHART
st.subheader("2. Graphical Analysis")
if chart_fig:
    st.plotly_chart(chart_fig, use_container_width=True)
else:
    st.info("Select a region to view outlet performance.")

st.markdown("---")

# ROW 3: TABLE
st.subheader("3. Data Table")

display_df = active_df.copy()

# Show filtered data for outlets
if view_selection == "Outlet Performance" and 'filtered_df' in locals():
    display_df = filtered_df.copy()

if not display_df.empty and 'Pass' in display_df.columns and 'Fail' in display_df.columns:
    # Calculate Total for rate calc (Ensure we don't divide by zero)
    display_df['Calculated Total'] = display_df['Pass'] + display_df['Fail']
    
    display_df['Pass Rate (%)'] = display_df.apply(
        lambda x: (x['Pass'] / x['Calculated Total'] * 100) if x['Calculated Total'] > 0 else 0, 
        axis=1
    ).round(1)
    
    # Drop intermediate calc column before showing
    display_df = display_df.drop(columns=['Calculated Total'])
    
    st.dataframe(
        display_df.style.background_gradient(cmap='RdYlGn', subset=['Pass Rate (%)'], vmin=0, vmax=100),
        use_container_width=True
    )
else:
    st.dataframe(display_df, use_container_width=True)

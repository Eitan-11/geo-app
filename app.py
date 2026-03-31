import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import numpy as np

# 1. הגדרות דף ועיצוב כללי
st.set_page_config(
    page_title="מחשבון פיזור גיאוגרפי",
    page_icon="🗺️",
    layout="wide" # פריסה רחבה יותר
)

# הוספת CSS מותאם אישית לעיצוב כפתורים וטקסט
st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .stButton>button {
        width: 100%;
        border-radius: 20px;
        height: 3em;
        background-color: #007bff;
        color: white;
    }
    .metric-container {
        background-color: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    </style>
    """, unsafe_allow_html=True)

# 2. כותרת מעוצבת
st.title("🗺️ מחשבון פיזור ונקודת מפגש")
st.info("כלי חכם לניתוח גיאוגרפי של קבוצת יישובים ומציאת מרכז המסה התיאורטי.")

# 3. סרגל צד (Sidebar) להזנת נתונים
with st.sidebar:
    st.header("⚙️ הגדרות קלט")
    input_cities = st.text_area(
        "הזינו יישובים (מופרדים בפסיק):", 
        "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל",
        height=200
    )
    calculate = st.button("🚀 הרץ ניתוח גיאוגרפי")
    st.divider()
    st.markdown("### אודות")
    st.write("החישוב מתבצע באמצעות מנוע ArcGIS ומרחק אווירי מדויק.")

# 4. לוגיקה ותצוגה מרכזית
if calculate:
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    
    locations = []
    with st.spinner('מנתח נתונים גיאוגרפיים...'):
        for name in city_list:
            try:
                search_query = name if "ישראל" in name or "Israel" in name else f"{name}, Israel"
                loc = geolocator.geocode(search_query)
                if loc:
                    locations.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
            except: continue

    if len(locations) < 2:
        st.error("יש להזין לפחות שני יישובים תקינים.")
    else:
        # חישובים (פיזור ומרכז)
        results = []
        all_avg_dist = []
        for i, c1 in enumerate(locations):
            dists = [geodesic((c1["lat"], c1["lon"]), (c2["lat"], c2["lon"])).km for j, c2 in enumerate(locations) if i != j]
            avg = sum(dists) / len(dists)
            all_avg_dist.append(avg)
            results.append({"יישוב": c1["name"], "ריחוק ממוצע (ק\"מ)": round(avg, 2)})
        
        center_lat = np.mean([l["lat"] for l in locations])
        center_lon = np.mean([l["lon"] for l in locations])
        final_score = sum(all_avg_dist) / len(all_avg_dist)

        # תצוגת מדדים בכרטיסים (Metrics)
        m1, m2, m3 = st.columns(3)
        with m1:
            st.metric("📊 רמת פיזור כללית", f"{final_score:.2f} ק\"מ")
        with m2:
            distances_to_center = [geodesic((center_lat, center_lon), (l["lat"], l["lon"])).km for l in locations]
            closest_city = locations[np.argmin(distances_to_center)]["name"]
            st.metric("📍 יישוב מרכזי", closest_city)
        with m3:
            st.metric("🏘️ סה\"כ יישובים", len(locations))

        # תצוגת מפה וטבלה בשתי עמודות
        st.divider()
        col_map, col_table = st.columns([2, 1])
        
        with col_map:
            st.subheader("📍 פריסה על המפה")
            df_map = pd.DataFrame(locations)
            st.map(df_map, color='#007bff', size=20)
        
        with col_table:
            st.subheader("📝 פירוט מרחקים")
            st.dataframe(pd.DataFrame(results), use_container_width=True, hide_index=True)

        # הצעת מפגש
        st.success(f"💡 **הצעה:** המקום הנוח ביותר למפגש הוא באזור **{closest_city}**.")
else:
    st.write("👈 התחל על ידי הזנת רשימת יישובים בסרגל הצד ולחיצה על הכפתור.")

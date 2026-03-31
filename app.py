import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import numpy as np

# הגדרות דף
st.set_page_config(page_title="מחשבון נגישות ופיזור", page_icon="🚗", layout="wide")

st.title("🚗 מחשבון הנגישות ונקודת המפגש")
st.info("הכלי מוצא כעת גם את המרכז הגיאוגרפי וגם את היישוב שהכי נגיש תחבורתית לקבוצה.")

# סרגל צד
with st.sidebar:
    st.header("⚙️ הזנת נתונים")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 נתח נגישות ומפגש")

if calculate:
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    locations = []
    
    with st.spinner('מנתח מסלולי נסיעה ומיקומים...'):
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
        # --- חישוב 1: מרכז גאוגרפי (קו אווירי) ---
        center_lat = np.mean([l["lat"] for l in locations])
        center_lon = np.mean([l["lon"] for l in locations])
        
        # --- חישוב 2: מדד נגישות (מי הכי קרוב לכבישים הראשיים של שאר הקבוצה) ---
        # אנחנו בונים מטריצת מרחקים בין כל היישובים
        accessibility_results = []
        for i, target in enumerate(locations):
            total_travel_effort = 0
            for j, origin in enumerate(locations):
                if i == j: continue
                # אנחנו מוסיפים "מקדם כבישים" של 1.3 למרחק האווירי כדי להעריך מרחק נסיעה
                dist_road_est = geodesic((target["lat"], target["lon"]), (origin["lat"], origin["lon"])).km * 1.3
                total_travel_effort += dist_road_est
            
            accessibility_results.append({
                "name": target["name"],
                "total_effort": total_travel_effort,
                "avg_effort": total_travel_effort / (len(locations)-1)
            })

        # מציאת היישוב עם המאמץ הנמוך ביותר (הכי נגיש)
        best_city = min(accessibility_results, key=lambda x: x['total_effort'])
        
        # --- תצוגת תוצאות ---
        c1, c2 = st.columns(2)
        with c1:
            st.metric("📍 המרכז הגאוגרפי", locations[np.argmin([geodesic((center_lat, center_lon), (l["lat"], l["lon"])).km for l in locations])]["name"])
            st.caption("הנקודה שנמצאת באמצע המפה.")
        with c2:
            st.metric("🏠 היישוב הכי נגיש", best_city['name'])
            st.caption("היישוב שדורש הכי מעט נסיעה מצטברת משאר חברי הקבוצה.")

        st.divider()
        
        # מפה
        st.subheader("🗺️ מפת פריסה")
        st.map(pd.DataFrame(locations), color='#ff4b4b')

        # טבלת נגישות
        st.subheader("📊 מדד הנגישות (מאמץ נסיעה מצטבר)")
        df_acc = pd.DataFrame(accessibility_results).sort_values("avg_effort")
        df_acc.columns = ["שם היישוב", "סך קילומטראז' נסיעה אליו", "מרחק נסיעה ממוצע (ק\"מ)"]
        st.dataframe(df_acc, use_container_width=True, hide_index=True)
        
        st.success(f"💡 **המלצה:** אם אתם מחפשים להיפגש בבית של מישהו, הכי כדאי להיפגש ב**{best_city['name']}** - זה יחסוך לקבוצה הכי הרבה דלק וזמן.")

import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np
import time

st.set_page_config(page_title="מחשבון נגישות מתקדם", page_icon="🛣️", layout="wide")

def get_road_dist(origin, target):
    """שאילתת מרחק כבישים מהירה (ללא גיאומטריה)"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview=false"
        r = requests.get(url, timeout=1)
        if r.status_code == 200:
            return r.json()['routes'][0]['distance'] / 1000
    except: return None
    return None

st.title("🗺️ ניתוח נגישות ופיזור (טעינה חכמה)")

with st.sidebar:
    st.header("⚙️ הזנת נתונים")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל, ירושלים, באר שבע")
    calculate = st.button("🚀 הרץ ניתוח")

if calculate or 'locs' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        names = [c.strip() for c in input_cities.split(",") if c.strip()]
        locs = []
        with st.spinner('מאתר מיקומים...'):
            for name in names:
                loc = geolocator.geocode(f"{name}, Israel")
                if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
        st.session_state.locs = locs
        # איפוס נתונים קודמים
        st.session_state.road_results = None 

    locs = st.session_state.locs
    
    # שלב 1: חישוב אווירי (מיידי)
    air_results = []
    for i, t in enumerate(locs):
        dists = [geodesic((t['lat'], t['lon']), (o['lat'], o['lon'])).km for j, o in enumerate(locs) if i != j]
        air_results.append({"יישוב": t['name'], "מרחק אווירי ממוצע": round(np.mean(dists), 1), "lat": t['lat'], "lon": t['lon']})
    
    df_air = pd.DataFrame(air_results).sort_values("מרחק אווירי ממוצע")
    
    # הצגת נתונים ראשוניים (אוויריים)
    c1, c2, c3 = st.columns(3)
    c1.metric("📊 מדד פיזור כללי", f"{df_air['מרחק אווירי ממוצע'].mean():.1f} ק\"מ")
    c2.metric("📍 המרכז הגיאוגרפי", df_air.iloc[0]["יישוב"])
    
    # שלב 2: חישוב כבישים (רק אם עדיין לא חושב)
    if 'road_results' not in st.session_state or st.session_state.road_results is None:
        if len(locs) > 15:
            st.warning(f"מנתח {len(locs)} יישובים. חישוב נתיבי נסיעה עשוי לקחת כדקה...")
        
        road_data = []
        progress_bar = st.progress(0)
        total_pairs = len(locs) * (len(locs) - 1)
        count = 0
        
        for i, target in enumerate(locs):
            total_r_dist = 0
            for j, origin in enumerate(locs):
                if i == j: continue
                d = get_road_dist((origin['lat'], origin['lon']), (target['lat'], target['lon']))
                if d is None: d = geodesic((origin['lat'], origin['lon']), (target['lat'], target['lon'])).km * 1.25
                total_r_dist += d
                count += 1
                progress_bar.progress(min(count / total_pairs, 1.0))
            
            road_data.append({"יישוב": target['name'], "מרחק נסיעה ממוצע": round(total_r_dist/(len(locs)-1), 1)})
        
        st.session_state.road_results = pd.DataFrame(road_data)
        st.rerun() # טעינה מחדש להצגת התוצאות הסופיות

    # שלב 3: תצוגת התוצאות הסופיות (כבישים + אווירי)
    df_final = pd.merge(df_air, st.session_state.road_results, on="יישוב")
    best_road_city = df_final.loc[df_final["מרחק נסיעה ממוצע"].idxmin()]
    c3.metric("🏠 היישוב הכי נגיש", best_road_city["יישוב"])

    st.divider()
    
    col_tab, col_map = st.columns([1, 2])
    with col_tab:
        st.subheader("📊 השוואת נגישות")
        st.dataframe(df_final[["יישוב", "מרחק אווירי ממוצע", "מרחק נסיעה ממוצע"]].sort_values("מרחק נסיעה ממוצע"), 
                     use_container_width=True, hide_index=True)
        selected_city = st.selectbox("בחר יעד לצפייה בנתיבים:", df_final["יישוב"].tolist())

    with col_map:
        # יצירת מפה (בדומה לקוד הקודם עם Folium)
        target_node = df_final[df_final["יישוב"] == selected_city].iloc[0]
        m = folium.Map(location=[target_node['lat'], target_node['lon']], zoom_start=8)
        # ... (כאן מופיע קוד ה-Folium לציור הקווים כפי שהיה קודם)
        folium.Marker([target_node['lat'], target_node['lon']], icon=folium.Icon(color='red')).add_to(m)
        folium_static(m, width=750)

import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np

# 1. הגדרות דף
st.set_page_config(page_title="מחשבון פיזור ונגישות מלא", page_icon="🗺️", layout="wide")

def get_road_dist(origin, target):
    """פונקציית עזר למרחק כבישים מהיר (ללא מסלול מלא)"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview=false"
        r = requests.get(url, timeout=2)
        if r.status_code == 200:
            return r.json()['routes'][0]['distance'] / 1000
    except: return geodesic(origin, target).km * 1.25

def get_full_route(origin, target):
    """פונקציה למסלול מלא (לציור על המפה)"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview=full&geometries=geojson"
        r = requests.get(url, timeout=3)
        data = r.json()
        if data.get('code') == 'Ok':
            line = data['routes'][0]['geometry']['coordinates']
            return [[p[1], p[0]] for p in line]
    except: return None

st.title("🗺️ ניתוח גיאוגרפי ותחבורתי מלא")

# 2. קלט בסרגל צד
with st.sidebar:
    st.header("⚙️ הזנת נתונים")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 הרץ ניתוח מלא")

if calculate or 'results_df' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
        
        locs = []
        with st.spinner('מאתר מיקומים...'):
            for name in city_list:
                loc = geolocator.geocode(f"{name}, Israel")
                if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
        
        if len(locs) >= 2:
            st.session_state.locations = locs
            
            # חישוב כל המטריצה (אווירי + כבישים)
            all_results = []
            with st.spinner('מחשב מדדי פיזור ונגישות...'):
                for i, target in enumerate(locs):
                    air_dists = []
                    road_dists = []
                    for j, origin in enumerate(locs):
                        if i == j: continue
                        air_dists.append(geodesic((origin['lat'], origin['lon']), (target['lat'], target['lon'])).km)
                        road_dists.append(get_road_dist((origin['lat'], origin['lon']), (target['lat'], target['lon'])))
                    
                    all_results.append({
                        "יישוב": target['name'],
                        "מרחק אווירי ממוצע": round(np.mean(air_dists), 1),
                        "מרחק נסיעה ממוצע": round(np.mean(road_dists), 1),
                        "סך קילומטראז' (כבישים)": round(sum(road_dists), 1),
                        "lat": target['lat'], "lon": target['lon']
                    })
            
            st.session_state.results_df = pd.DataFrame(all_results)
            st.session_state.dispersion = st.session_state.results_df["מרחק אווירי ממוצע"].mean()

    # --- תצוגת התוצאות (אם קיימות בזיכרון) ---
    if 'results_df' in st.session_state:
        df = st.session_state.results_df
        
        # א. כרטיסי מדדים (Metrics)
        m1, m2, m3 = st.columns(3)
        m1.metric("📊 מדד פיזור כללי", f"{st.session_state.dispersion:.1f} ק\"מ")
        
        best_air = df.loc[df["מרחק אווירי ממוצע"].idxmin(),

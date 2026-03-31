import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np

# הגדרות דף
st.set_page_config(page_title="מחשבון נגישות ופיזור", page_icon="📍", layout="wide")

def get_osrm_data(origin, target, full_route=False):
    """שליפת מרחק ונתיב משרת OSRM"""
    geom = "full" if full_route else "simplified"
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview={geom}&geometries=geojson"
        r = requests.get(url, timeout=2)
        data = r.json()
        if data.get('code') == 'Ok':
            dist = data['routes'][0]['distance'] / 1000
            coords = [[p[1], p[0]] for p in data['routes'][0]['geometry']['coordinates']] if full_route else None
            return dist, coords
    except: return None, None
    return None, None

st.title("📍 ניתוח פיזור ונגישות תחבורתית")

with st.sidebar:
    st.header("⚙️ הגדרות")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל, ירושלים")
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
        st.session_state.road_done = False # סימון שחישוב הכבישים טרם הסתיים

    locs = st.session_state.locs
    
    # --- שלב א': הצגת נתונים אוויריים מיידיים ---
    air_results = []
    for i, t in enumerate(locs):
        dists = [geodesic((t['lat'], t['lon']), (o['lat'], o['lon'])).km for j, o in enumerate(locs) if i != j]
        air_results.append({
            "יישוב": t['name'],
            "מרחק אווירי ממוצע": np.mean(dists),
            "lat": t['lat'], "lon": t['lon']
        })
    df_air = pd.DataFrame(air_results).sort_values("מרחק אווירי ממוצע")
    
    c1, c2, c3 = st.columns(3)
    c1.metric("📊 מדד פיזור כללי", f"{df_air['מרחק אווירי ממוצע'].mean():.1f} ק\"מ")
    c2.metric("📍 המרכז הגיאוגרפי", df_air.iloc[0]['יישוב'])
    
    # מציין מקום (Placeholder) ליישוב הנגיש שיופיע אחר כך
    road_metric_spot = c3.empty() 
    
    st.divider()
    
    col_tab, col_map = st.columns([1, 2])
    with col_tab:
        st.subheader("📝 נתונים גיאוגרפיים")
        st.dataframe(df_air[["יישוב", "מרחק אווירי ממוצע"]], use_container_width=True, hide_index=True)

    # --- שלב ב': חישוב כבישים בזמן שהמשתמש צופה בנתונים ---
    if not st.session_state.get('road_done', False):
        road_means = {}
        st.info("🔄 מחשב נתוני נסיעה וכבישים... נא להמתין לסיום הפס")
        progress = st.progress(0)
        
        for i, t in enumerate(locs):
            road_dists = []
            for j, o in enumerate(locs):
                if i == j: continue
                d, _ = get_osrm_data((o['lat'], o['lon']), (t['lat'], t['lon']))
                road_dists.append(d if d else geodesic((o['lat'], o['lon']), (t['lat'], t['lon'])).km * 1.25)
            road_means[t['name']] = np.mean(road_dists)
            progress.progress((i + 1) / len(locs))
        
        # עדכון הנתונים ב-Session State
        df_air['מרחק נסיעה ממוצע'] = df_air['יישוב'].map(road_means)
        st.session_state.final_df = df_air
        st.session_state.road_done = True
        st.rerun()

    # --- שלב ג': הצגת נתוני הכבישים והמפה לאחר הסיום ---
    if st.session_state.get('road_done', False):
        df = st.session_state.final_df
        
        # עדכון המדד החסר בראש הדף
        best_road = df.loc[df['מרחק נסיעה ממוצע'].idxmin()]
        road_metric_spot.metric("🏠 היישוב הכי נגיש", best_road['יישוב'])
        
        with col_tab:
            st.subheader("🚗 דירוג נגישות סופי")
            selected_target = st.selectbox("בחר יעד לצפייה בכבישים:", df['יישוב'].tolist(), 
                                           index=int(df['מרחק נסיעה ממוצע'].idxmin()))
            st.dataframe(df[["יישוב", "מרחק נסיעה ממוצע"]].sort_values("מרחק נסיעה ממוצע"), 
                         use_container_width=True, hide_index=True)

        with col_map:
            target_data = df[df['יישוב'] == selected_target].iloc[0]
            m = folium.Map(location=[target_data['lat'], target_data['lon']], zoom_start=8, tiles='CartoDB positron')
            
            for _, origin in df.iterrows():
                if origin['יישוב'] == selected_target:
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב'], 
                                  icon=folium.Icon(color='red', icon='star')).add_to(m)
                else:
                    _, route = get_osrm_data((origin['lat'], origin['lon']), (target_data['lat'], target_data['lon']), full_route=True)
                    if route:
                        folium.PolyLine(route, color='#2E86C1', weight=4, opacity=0.6).add_to(m)
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב']).add_to(m)
            
            folium_static(m, width=800, height=550)

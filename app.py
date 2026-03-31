import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np

# 1. הגדרות דף
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

# 2. סרגל צד
with st.sidebar:
    st.header("⚙️ הגדרות")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל, ירושלים")
    calculate = st.button("🚀 הרץ ניתוח")

if calculate or 'results' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        names = [c.strip() for c in input_cities.split(",") if c.strip()]
        locs = []
        with st.spinner('מאתר מיקומים...'):
            for name in names:
                loc = geolocator.geocode(f"{name}, Israel")
                if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
        
        if len(locs) >= 2:
            # חישוב מטריצת נגישות (כבישים + אווירי)
            results = []
            progress = st.progress(0)
            for i, t in enumerate(locs):
                air_dists = []
                road_dists = []
                for j, o in enumerate(locs):
                    if i == j: continue
                    air_dists.append(geodesic((t['lat'], t['lon']), (o['lat'], o['lon'])).km)
                    # חישוב מרחק כביש מהיר לצורך מציאת היישוב הנגיש
                    d, _ = get_osrm_data((o['lat'], o['lon']), (t['lat'], t['lon']))
                    road_dists.append(d if d else air_dists[-1] * 1.25)
                
                results.append({
                    "יישוב": t['name'],
                    "מרחק אווירי ממוצע": np.mean(air_dists),
                    "מרחק נסיעה ממוצע": np.mean(road_dists),
                    "lat": t['lat'], "lon": t['lon']
                })
                progress.progress((i + 1) / len(locs))
            
            st.session_state.results = pd.DataFrame(results)

    # הצגת תוצאות
    if 'results' in st.session_state:
        df = st.session_state.results
        
        # א. כרטיסי מדדים
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 מדד פיזור כללי", f"{df['מרחק אווירי ממוצע'].mean():.1f} ק\"מ")
        
        best_air = df.loc[df['מרחק אווירי ממוצע'].idxmin(), 'יישוב']
        c2.metric("📍 המרכז הגיאוגרפי", best_air)
        
        best_road = df.loc[df['מרחק נסיעה ממוצע'].idxmin()]
        c3.metric("🏠 היישוב הכי נגיש", best_road['יישוב'])

        st.divider()

        # ב. מפה וטבלה
        col_tab, col_map = st.columns([1, 2])
        
        with col_tab:
            st.subheader("📝 השוואת נגישות")
            selected_target = st.selectbox("בחר יעד לצפייה בכבישים:", df['יישוב'].tolist(), 
                                           index=int(df['מרחק נסיעה ממוצע'].idxmin()))
            
            st.dataframe(df[["יישוב", "מרחק אווירי ממוצע", "מרחק נסיעה ממוצע"]].sort_values("מרחק נסיעה ממוצע"), 
                         use_container_width=True, hide_index=True)

        with col_map:
            target_data = df[df['יישוב'] == selected_target].iloc[0]
            m = folium.Map(location=[target_data['lat'], target_data['lon']], zoom_start=8, tiles='CartoDB positron')
            
            with st.spinner(f'משרטט כבישים אל {selected_target}...'):
                for _, origin in df.iterrows():
                    if origin['יישוב'] == selected_target:
                        folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב'], 
                                      icon=folium.Icon(color='red', icon='star')).add_to(m)
                    else:
                        _, route = get_osrm_data((origin['lat'], origin['lon']), (target_data['lat'], target_data['lon']), full_route=True)
                        if route:
                            folium.PolyLine(route, color='#2E86C1', weight=4, opacity=0.6).add_to(m)
                        folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב']).add_to(m)
            
            folium_static(m, width=800, height=500)

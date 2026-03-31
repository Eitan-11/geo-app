import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np

# 1. הגדרות דף
st.set_page_config(page_title="מחשבון נגישות וכבישים", page_icon="🛣️", layout="wide")

def get_osrm_route(origin, target):
    """שליפת נתיב נסיעה אמיתי משרת OSRM"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview=full&geometries=geojson"
        r = requests.get(url, timeout=3)
        data = r.json()
        if data.get('code') == 'Ok':
            line = data['routes'][0]['geometry']['coordinates']
            # OSRM מחזיר [lon, lat], פוליום צריך [lat, lon]
            return [[p[1], p[0]] for p in line], data['routes'][0]['distance'] / 1000
    except: return None, None

st.title("🛣️ ניתוח נגישות ותשתית כבישים")

# 2. קלט
with st.sidebar:
    st.header("⚙️ הגדרות קלט")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 נתח נתונים והצג כבישים")

if calculate or 'locs' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        names = [c.strip() for c in input_cities.split(",") if c.strip()]
        locs = []
        with st.spinner('מאתר מיקומים מדויקים...'):
            for name in names:
                loc = geolocator.geocode(f"{name}, Israel")
                if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
        st.session_state.locs = locs

    if len(st.session_state.locs) < 2:
        st.error("יש להזין לפחות שני יישובים.")
    else:
        locs = st.session_state.locs
        
        # חישובים גיאוגרפיים מורחבים
        air_results = []
        for i, t in enumerate(locs):
            dists = [geodesic((t['lat'], t['lon']), (o['lat'], o['lon'])).km for j, o in enumerate(locs) if i != j]
            air_results.append({
                "יישוב": t['name'], 
                "מרחק אווירי ממוצע": np.mean(dists),
                "הכי רחוק מ": locs[np.argmax(dists)]['name'],
                "מרחק מקסימלי": np.max(dists),
                "lat": t['lat'], "lon": t['lon']
            })
        
        df_air = pd.DataFrame(air_results)
        
        # הצגת נתונים בראש הדף
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("📊 פיזור ממוצע", f"{df_air['מרחק אווירי ממוצע'].mean():.1f} ק\"מ")
        c2.metric("📍 מרכז גיאוגרפי", df_air.loc[df_air['מרחק אווירי ממוצע'].idxmin(), 'יישוב'])
        c3.metric("🌵 היישוב המבודד", df_air.loc[df_air['מרחק אווירי ממוצע'].idxmax(), 'יישוב'])
        c4.metric("📏 רדיוס פריסה", f"{df_air['מרחק מקסימלי'].max():.1f} ק\"מ")

        st.divider()

        # בחירת יעד להצגת כבישים
        selected_target = st.selectbox("בחר יישוב יעד כדי לראות את הכבישים המובילים אליו:", df_air['יישוב'].tolist(), 
                                       index=int(df_air['מרחק אווירי ממוצע'].idxmin()))
        
        target_node = df_air[df_air['יישוב'] == selected_target].iloc[0]
        
        # יצירת המפה עם Folium
        m = folium.Map(location=[target_node['lat'], target_node['lon']], zoom_start=8, tiles='CartoDB positron')
        
        road_stats = []
        with st.spinner(f'משרטט נתיבי נסיעה אל {selected_target}...'):
            for _, origin in df_air.iterrows():
                if origin['יישוב'] == selected_target:
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב'], 
                                  icon=folium.Icon(color='red', icon='star')).add_to(m)
                    continue
                
                # שליפת הכבישים
                route, dist = get_osrm_route((origin['lat'], origin['lon']), (target_node['lat'], target_node['lon']))
                
                if route:
                    folium.PolyLine(route, color='#2E86C1', weight=4, opacity=0.7, tooltip=f"{origin['יישוב']} -> {selected_target}").add_to(m)
                    road_stats.append({"מ": origin['יישוב'], "מרחק נסיעה (ק\"מ)": round(dist, 1)})
                
                folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב']).add_to(m)

        # תצוגת מפה וטבלה
        col_map, col_details = st.columns([2, 1])
        with col_map:
            folium_static(m, width=850, height=550)
        
        with col_details:
            st.subheader("🚗 זמני נסיעה ליעד")
            if road_stats:
                st.table(pd.DataFrame(road_stats))
                avg_road = np.mean([r['מרחק נסיעה (ק\"מ)'] for r in road_stats])
                st.success(f"**ממוצע נסיעה ליעד:** {avg_road:.1f} ק\"מ")
            
            st.info("💡 המפה מציגה נתיבי נסיעה אמיתיים בכבישים (בכחול).")

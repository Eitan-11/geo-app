import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static
import numpy as np
import time

st.set_page_config(page_title="מחשבון נגישות מהיר", page_icon="⚡", layout="wide")

# פונקציות עזר מהירות
def get_route_data(origin, target, full_geometry=False):
    geom = "full" if full_geometry else "simplified"
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview={geom}&geometries=geojson"
        r = requests.get(url, timeout=2)
        data = r.json()
        if data.get('code') == 'Ok':
            dist = data['routes'][0]['distance'] / 1000
            coords = [[p[1], p[0]] for p in data['routes'][0]['geometry']['coordinates']] if full_geometry else None
            return dist, coords
    except: return None, None
    return None, None

st.title("⚡ מחשבון נגישות ופיזור - גרסה מהירה (30+ יישובים)")

with st.sidebar:
    st.header("⚙️ הזנת נתונים")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל, ירושלים, תל אביב, חיפה, באר שבע")
    calculate = st.button("🚀 נתח במהירות")

if calculate or 'locs' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        names = [c.strip() for c in input_cities.split(",") if c.strip()]
        locs = []
        progress_bar = st.progress(0)
        
        # שלב 1: איתור מיקומים (מהיר)
        for i, name in enumerate(names):
            loc = geolocator.geocode(f"{name}, Israel")
            if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
            progress_bar.progress((i + 1) / len(names))
        
        st.session_state.locs = locs
        
        # שלב 2: חישוב אווירי לכולם (מיידי)
        air_results = []
        for i, target in enumerate(locs):
            dists = [geodesic((target['lat'], target['lon']), (o['lat'], o['lon'])).km for j, o in enumerate(locs) if i != j]
            air_results.append({"יישוב": target['name'], "מרחק אווירי ממוצע": round(np.mean(dists), 1), "lat": target['lat'], "lon": target['lon']})
        
        st.session_state.air_df = pd.DataFrame(air_results).sort_values("מרחק אווירי ממוצע")
        st.session_state.total_disp = st.session_state.air_df["מרחק אווירי ממוצע"].mean()

    # תצוגה
    if 'air_df' in st.session_state:
        df = st.session_state.air_df
        
        c1, c2, c3 = st.columns(3)
        c1.metric("📊 מדד פיזור כללי", f"{st.session_state.total_disp:.1f} ק\"מ")
        c2.metric("📍 המרכז הגיאוגרפי", df.iloc[0]["יישוב"])
        c3.metric("🏘️ סה\"כ יישובים", len(df))

        st.divider()

        col_ui, col_map = st.columns([1, 2])

        with col_ui:
            st.subheader("🎯 בחירת יעד למפגש")
            selected_city = st.selectbox("בחר יישוב כדי לחשב מסלולי נסיעה אמיתיים אליו:", df["יישוב"].tolist())
            
            target_node = df[df["יישוב"] == selected_city].iloc[0]
            
            # חישוב כבישים רק עבור היעד הנבחר (חוסך המון זמן!)
            road_details = []
            total_road_km = 0
            
            with st.spinner(f'מחשב מסלולי כבישים אל {selected_city}...'):
                for _, origin in df.iterrows():
                    if origin['יישוב'] == selected_city: continue
                    dist, _ = get_route_data((origin['lat'], origin['lon']), (target_node['lat'], target_node['lon']))
                    if dist is None: dist = origin['מרחק אווירי ממוצע'] * 1.25 # Fallback
                    road_details.append({"מ": origin['יישוב'], "ק\"מ": round(dist, 1)})
                    total_road_km += dist
            
            avg_road = total_road_km / (len(df)-1)
            st.info(f"🛣️ מרחק נסיעה ממוצע ל{selected_city}: **{avg_road:.1f} ק\"מ**")
            st.dataframe(df[["יישוב", "מרחק אווירי ממוצע"]], use_container_width=True, hide_index=True)

        with col_map:
            m = folium.Map(location=[target_node['lat'], target_node['lon']], zoom_start=8)
            
            # ציור מסלולים בזמן אמת רק ליעד הנבחר
            for _, origin in df.iterrows():
                if origin['יישוב'] == selected_city:
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב'], icon=folium.Icon(color='red', icon='star')).add_to(m)
                else:
                    _, route_coords = get_route_data((origin['lat'], origin['lon']), (target_node['lat'], target_node['lon']), full_geometry=True)
                    if route_coords:
                        folium.PolyLine(route_coords, color="blue", weight=3, opacity=0.5).add_to(m)
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['יישוב']).add_to(m)
            
            folium_static(m, width=800, height=550)

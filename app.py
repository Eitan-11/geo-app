import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import folium
from streamlit_folium import folium_static

# הגדרות דף
st.set_page_config(page_title="מחשבון נגישות ויזואלי", page_icon="🛣️", layout="wide")

def get_osrm_route(origin, target):
    """מביא את הקואורדינטות של המסלול המלא לצורך ציור על המפה"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{origin[1]},{origin[0]};{target[1]},{target[0]}?overview=full&geometries=geojson"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 'Ok':
                line = data['routes'][0]['geometry']['coordinates']
                # OSRM מחזיר [lon, lat], פוליום צריך [lat, lon]
                return [[p[1], p[0]] for p in line], data['routes'][0]['distance'] / 1000
    except: pass
    return None, None

st.title("🛣️ מפת נגישות וכבישים אינטראקטיבית")

with st.sidebar:
    st.header("⚙️ הזנת נתונים")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 נתח נתונים")

if calculate or 'locations' in st.session_state:
    if calculate:
        geolocator = ArcGIS(timeout=10)
        city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
        locs = []
        for name in city_list:
            loc = geolocator.geocode(f"{name}, Israel")
            if loc: locs.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
        st.session_state.locations = locs

    if len(st.session_state.locations) < 2:
        st.error("הזינו לפחות שני יישובים.")
    else:
        locs = st.session_state.locations
        
        # חישוב מהיר של מרחקים אוויריים להצגת טבלה ראשונית
        air_results = []
        for l in locs:
            dists = [geodesic((l['lat'], l['lon']), (other['lat'], other['lon'])).km for other in locs if l != other]
            air_results.append({"יישוב": l['name'], "מרחק אווירי ממוצע": round(sum(dists)/len(dists), 1)})
        
        st.subheader("📍 בחר יישוב יעד להצגת כבישים:")
        selected_target_name = st.selectbox("בחר יישוב מהרשימה כדי לראות את דרכי ההגעה אליו:", [l['name'] for l in locs])
        
        target_loc = next(l for l in locs if l['name'] == selected_target_name)
        
        # יצירת המפה
        m = folium.Map(location=[target_loc['lat'], target_loc['lon']], zoom_start=8, control_scale=True)
        
        total_road_dist = 0
        road_details = []

        with st.spinner(f'מחשב מסלולים אל {selected_target_name}...'):
            for origin in locs:
                if origin['name'] == selected_target_name:
                    folium.Marker([origin['lat'], origin['lon']], popup=origin['name'], icon=folium.Icon(color='red', icon='star')).add_to(m)
                    continue
                
                # הבאת המסלול מהשרת
                route_coords, dist = get_osrm_route((origin['lat'], origin['lon']), (target_loc['lat'], target_loc['lon']))
                
                if route_coords:
                    folium.PolyLine(route_coords, weight=4, color='blue', opacity=0.6).add_to(m)
                    total_road_dist += dist
                    road_details.append({"ממוצא": origin['name'], "מרחק נסיעה (ק\"מ)": round(dist, 1)})
                
                folium.Marker([origin['lat'], origin['lon']], popup=origin['name']).add_to(m)

        # תצוגה
        col_map, col_info = st.columns([2, 1])
        with col_map:
            folium_static(m, width=800)
        
        with col_info:
            st.metric("סה\"כ קילומטראז' לקבוצה", f"{total_road_dist:.1f} ק\"מ")
            st.write(f"מרחק נסיעה ממוצע ליעד: **{total_road_dist/(len(locs)-1):.1f} ק\"מ**")
            st.table(pd.DataFrame(road_details))

        st.divider()
        st.subheader("📊 השוואת פיזור גיאוגרפי (מרחק אווירי)")
        st.dataframe(pd.DataFrame(air_results).sort_values("מרחק אווירי ממוצע"), use_container_width=True, hide_index=True)

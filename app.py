import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import time
import numpy as np

# הגדרות דף
st.set_page_config(page_title="מחשבון פיזור ונגישות", page_icon="🚗", layout="wide")

def get_road_distance(lat1, lon1, lat2, lon2):
    """חישוב מרחק כבישים אמיתי דרך OSRM"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        r = requests.get(url, timeout=3)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 'Ok':
                return data['routes'][0]['distance'] / 1000
    except:
        pass
    return None

st.title("🗺️ ניתוח פיזור גיאוגרפי ונגישות תחבורתית")

with st.sidebar:
    st.header("⚙️ הגדרות")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 נתח נתונים")

if calculate:
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    locations = []
    
    with st.spinner('מאתר מיקומים...'):
        for name in city_list:
            loc = geolocator.geocode(f"{name}, Israel")
            if loc:
                locations.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
            time.sleep(0.1)

    if len(locations) < 2:
        st.error("חובה להזין לפחות שני יישובים תקינים.")
    else:
        results = []
        all_air_dists = []
        
        with st.spinner('מחשב מרחקים אוויריים ומסלולי נסיעה...'):
            for i, target in enumerate(locations):
                total_road_dist = 0
                total_air_dist = 0
                
                for j, origin in enumerate(locations):
                    if i == j: continue
                    
                    # מרחק אווירי (Geodesic)
                    air_d = geodesic((origin['lat'], origin['lon']), (target['lat'], target['lon'])).km
                    total_air_dist += air_d
                    
                    # מרחק כבישים (OSRM)
                    road_d = get_road_distance(origin['lat'], origin['lon'], target['lat'], target['lon'])
                    if road_d is not None:
                        total_road_dist += road_d
                    else:
                        total_road_dist += air_d * 1.25 # גיבוי אם השרת עמוס
                
                avg_air = total_air_dist / (len(locations)-1)
                avg_road = total_road_dist / (len(locations)-1)
                all_air_dists.append(avg_air)
                
                results.append({
                    "יישוב": target['name'],
                    "מרחק אווירי ממוצע (ק\"מ)": round(avg_air, 1),
                    "מרחק נסיעה ממוצע (ק\"מ)": round(avg_road, 1),
                    "סך נסיעה לקבוצה (כבישים)": round(total_road_dist, 1)
                })

        # חישוב מדד פיזור כללי (ממוצע האווירי של כולם)
        total_dispersion = sum(all_air_dists) / len(all_air_dists)
        best_city = min(results, key=lambda x: x['סך נסיעה לקבוצה (כבישים)'])
        
        # תצוגת מדדים
        m1, m2, m3 = st.columns(3)
        m1.metric("📊 מדד פיזור כללי", f"{total_dispersion:.1f} ק\"מ")
        m2.metric("🏠 היישוב הכי נגיש", best_city['יישוב'])
        m3.metric("🛣️ ממוצע נסיעה אליו", f"{best_city['מרחק נסיעה ממוצע (ק\"מ)']} ק\"מ")

        st.divider()
        
        # מפה
        st.subheader("📍 פריסה על המפה")
        st.map(pd.DataFrame(locations))
        
        # טבלה משולבת
        st.divider()
        st.subheader("📝 ניתוח השוואתי: גיאוגרפיה מול תחבורה")
        df_final = pd.DataFrame(results).sort_values("מרחק נסיעה ממוצע (ק\"מ)")
        
        # עיצוב הטבלה
        st.dataframe(df_final, use_container_width=True, hide_index=True)
        
        st.info(f"💡 **הסבר:** 'מרחק אווירי' מראה כמה היישוב מרכזי גיאוגרפית. 'מרחק נסיעה' מראה כמה באמת יצטרכו לנסוע אליו בכבישים.")

import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests
import time

# הגדרות דף
st.set_page_config(page_title="מחשבון נגישות", page_icon="🚗", layout="wide")

def get_road_distance(lat1, lon1, lat2, lon2):
    """פונקציה לשאילת שרת הניווט עם מנגנון הגנה"""
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        r = requests.get(url, timeout=5)
        if r.status_code == 200:
            data = r.json()
            if data.get('code') == 'Ok':
                return data['routes'][0]['distance'] / 1000
    except:
        pass
    return None # מחזיר None אם השרת נכשל

st.title("🚗 מחשבון הנגישות והפיזור")

with st.sidebar:
    st.header("⚙️ הגדרות")
    input_cities = st.text_area("הזינו יישובים (מופרדים בפסיק):", 
                                "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 חשב נגישות")

if calculate:
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    locations = []
    
    with st.spinner('מאתר מיקומים...'):
        for name in city_list:
            loc = geolocator.geocode(f"{name}, Israel")
            if loc:
                locations.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
            time.sleep(0.2) # מניעת חסימות

    if len(locations) < 2:
        st.error("לא נמצאו מספיק יישובים תקינים. נסו שמות אחרים.")
    else:
        results = []
        used_road_data = True
        
        with st.spinner('מחשב מסלולי נסיעה אופטימליים...'):
            for i, target in enumerate(locations):
                total_dist = 0
                for j, origin in enumerate(locations):
                    if i == j: continue
                    
                    # ניסיון לקבל מרחק כבישים
                    d = get_road_distance(origin['lat'], origin['lon'], target['lat'], target['lon'])
                    
                    if d is not None:
                        total_dist += d
                    else:
                        # גיבוי: מרחק אווירי כפול מקדם הגיוני (1.25)
                        total_dist += geodesic((origin['lat'], origin['lon']), (target['lat'], target['lon'])).km * 1.25
                        used_road_data = False
                    
                results.append({
                    "יישוב": target['name'],
                    "מרחק נסיעה ממוצע (ק\"מ)": round(total_dist / (len(locations)-1), 1),
                    "סך נסיעה לקבוצה (ק\"מ)": round(total_dist, 1)
                })

        # תצוגה
        if not used_road_data:
            st.warning("⚠️ שרת הניווט עמוס. התוצאות מבוססות על הערכת מרחק כבישים (מרחק אווירי משוקלל).")
        
        best_city = min(results, key=lambda x: x['סך נסיעה לקבוצה (ק\"מ)'])
        
        c1, c2 = st.columns(2)
        c1.metric("🏠 היישוב הכי נגיש", best_city['יישוב'])
        c2.metric("🛣️ ממוצע נסיעה אליו", f"{best_city['מרחק נסיעה ממוצע (ק\"מ)']} ק\"מ")

        st.divider()
        st.map(pd.DataFrame(locations))
        
        st.subheader("📊 פירוט נגישות")
        st.dataframe(pd.DataFrame(results).sort_values("מרחק נסיעה ממוצע (ק\"מ)"), use_container_width=True, hide_index=True)

import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import requests # בשביל לשאול את שרת הניווט

# 1. פונקציה שמחשבת מרחק כבישים אמיתי דרך OSRM
def get_road_distance(lat1, lon1, lat2, lon2):
    try:
        url = f"http://router.project-osrm.org/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
        r = requests.get(url)
        data = r.json()
        if data['code'] == 'Ok':
            # המרחק חוזר במטרים, אנחנו נהפוך לקילומטרים
            return data['routes'][0]['distance'] / 1000
    except:
        pass
    # אם השרת לא זמין, נחזור לברירת מחדל של מרחק אווירי כפול 1.2
    return geodesic((lat1, lon1), (lat2, lon2)).km * 1.2

# 2. הגדרות דף
st.set_page_config(page_title="מחשבון נגישות מדויק", page_icon="🚗", layout="wide")
st.title("🚗 מחשבון נגישות מבוסס מרחקי כבישים (OSRM)")

with st.sidebar:
    st.header("⚙️ הגדרות")
    input_cities = st.text_area("הזינו יישובים:", "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")
    calculate = st.button("🚀 חשב מרחקי כבישים אמיתיים")

if calculate:
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    locations = []
    
    with st.spinner('מאתר מיקומים ומחשב מסלולי נסיעה...'):
        for name in city_list:
            loc = geolocator.geocode(f"{name}, Israel")
            if loc:
                locations.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})

    if len(locations) < 2:
        st.error("יש להזין לפחות שני יישובים.")
    else:
        # --- חישוב מטריצת מרחקים אמיתית ---
        final_data = []
        for i, target in enumerate(locations):
            total_road_dist = 0
            for j, origin in enumerate(locations):
                if i == j: continue
                # כאן קורה הקסם - בדיקת מרחק כבישים אמיתי
                dist = get_road_distance(origin['lat'], origin['lon'], target['lat'], target['lon'])
                total_road_dist += dist
            
            avg_road_dist = total_road_dist / (len(locations) - 1)
            final_data.append({
                "יישוב": target['name'],
                "מרחק נסיעה ממוצע (ק\"מ)": round(avg_road_dist, 1),
                "סה\"כ קילומטראז' לקבוצה": round(total_road_dist, 1)
            })

        # תצוגה
        best_city = min(final_data, key=lambda x: x['סה\"כ קילומטראז\' לקבוצה'])
        
        c1, c2 = st.columns(2)
        c1.metric("היישוב הכי נגיש (כבישים)", best_city['יישוב'])
        c2.metric("מינימום נסיעה ממוצעת", f"{best_city['מרחק נסיעה ממוצע (ק\"מ)']} ק\"מ")

        st.divider()
        st.subheader("📍 מפת פריסה")
        st.map(pd.DataFrame(locations))

        st.subheader("📊 טבלת נגישות מבוססת כבישים")
        st.dataframe(pd.DataFrame(final_data).sort_values("מרחק נסיעה ממוצע (ק\"מ)"), use_container_width=True)

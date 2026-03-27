import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import numpy as np

# הגדרות דף
st.set_page_config(page_title="מחשבון פיזור ומפגש", page_icon="📍")

st.title("📍 מדד הפיזור ונקודת מפגש")
st.markdown("מחשב את רמת הפיזור ומוצא את הנקודה הגיאוגרפית המרכזית למפגש.")

# תיבת קלט
input_cities = st.text_area("הזינו שמות יישובים (מופרדים בפסיק):", 
                            "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")

if st.button("חשב פיזור ונקודת מפגש"):
    geolocator = ArcGIS(timeout=10)
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    
    locations = []
    
    with st.spinner('מנתח מיקומים...'):
        for name in city_list:
            try:
                search_query = name if "ישראל" in name or "Israel" in name else f"{name}, Israel"
                loc = geolocator.geocode(search_query)
                if loc:
                    locations.append({"name": name, "lat": loc.latitude, "lon": loc.longitude})
            except:
                continue

    if len(locations) < 2:
        st.error("חובה להזין לפחות שני יישובים תקינים.")
    else:
        # 1. חישוב פיזור (כפי שהיה)
        results = []
        all_avg_dist = []
        coords_list = [(l["lat"], l["lon"]) for l in locations]
        
        for i, c1 in enumerate(locations):
            dists = [geodesic((c1["lat"], c1["lon"]), (c2["lat"], c2["lon"])).km for j, c2 in enumerate(locations) if i != j]
            avg = sum(dists) / len(dists)
            all_avg_dist.append(avg)
            results.append({"יישוב": c1["name"], "ריחוק ממוצע (ק\"מ)": round(avg, 2)})
        
        # 2. חישוב נקודת המפגש האופטימלית (ממוצע הקואורדינטות)
        center_lat = np.mean([l["lat"] for l in locations])
        center_lon = np.mean([l["lon"] for l in locations])
        
        # 3. תצוגת תוצאות
        st.divider()
        col1, col2 = st.columns(2)
        col1.metric("רמת פיזור כללית", f"{sum(all_avg_dist)/len(all_avg_dist):.2f} ק\"מ")
        
        # מציאת היישוב הקרוב ביותר לנקודת המרכז התיאורטית
        meeting_point = (center_lat, center_lon)
        distances_to_center = [geodesic(meeting_point, (l["lat"], l["lon"])).km for l in locations]
        closest_city_index = np.argmin(distances_to_center)
        closest_city = locations[closest_city_index]["name"]
        
        col2.metric("היישוב המרכזי ביותר", closest_city)

        # 4. מפה עם כל הנקודות
        st.subheader("מפת פריסה ונקודת מרכז")
        df_map = pd.DataFrame(locations)
        # הוספת נקודת המפגש למפה
        meeting_df = pd.DataFrame([{"name": "נקודת מפגש אופטימלית", "lat": center_lat, "lon": center_lon}])
        st.map(df_map)
        
        st.write(f"💡 **טיפ:** נקודת המפגש האידיאלית נמצאת באזור **{closest_city}**.")
        
        st.divider()
        st.subheader("פירוט רמות ריחוק")
        st.table(pd.DataFrame(results))

        # אפשרות להורדת הנתונים
        csv = pd.DataFrame(results).to_csv(index=False).encode('utf-8-sig')
        st.download_button("הורד נתונים כ-CSV", csv, "dispersion_data.csv", "text/csv")

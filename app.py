import streamlit as st
from geopy.geocoders import ArcGIS
from geopy.distance import geodesic
import pandas as pd
import time

# הגדרות דף
st.set_page_config(page_title="מחשבון פיזור יישובים", page_icon="📍")

st.title("📍 מדד הפיזור הגיאוגרפי")
st.markdown("גרסה יציבה - שימוש במנוע ArcGIS לאיתור מיקומים.")

# תיבת קלט
input_cities = st.text_area("הזינו שמות יישובים (מופרדים בפסיק):", 
                            "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")

if st.button("חשב רמת פיזור והצג מפה"):
    # מעבר למנוע ArcGIS - הרבה יותר יציב ולא דורש User Agent מורכב
    geolocator = ArcGIS(timeout=10)
    
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    
    locations = []
    map_data = []
    
    with st.spinner('מאתר מיקומים ומחשב מרחקים...'):
        for name in city_list:
            try:
                # ArcGIS מצוין בזיהוי שמות בעברית גם בלי "ישראל", 
                # אבל נשאיר את זה לביטחון
                search_query = name if "ישראל" in name or "Israel" in name else f"{name}, Israel"
                
                loc = geolocator.geocode(search_query)
                
                if loc:
                    locations.append({"name": name, "coord": (loc.latitude, loc.longitude)})
                    map_data.append({"lat": loc.latitude, "lon": loc.longitude})
                else:
                    st.warning(f"⚠️ לא מצאתי את: {name}")
                
                # עם ArcGIS אפשר להוריד את ה-sleep או לקצר אותו מאוד
                time.sleep(0.2) 
                
            except Exception as e:
                st.error(f"שגיאה טכנית באיתור {name}. נסה שוב בעוד רגע.")
                continue

    if len(locations) < 2:
        st.error("חובה להזין לפחות שני יישובים תקינים שנמצאו.")
    else:
        # 1. חישובים
        results = []
        all_avg_dist = []
        for i, c1 in enumerate(locations):
            dists = [geodesic(c1["coord"], c2["coord"]).km for j, c2 in enumerate(locations) if i != j]
            avg = sum(dists) / len(dists)
            all_avg_dist.append(avg)
            results.append({"יישוב": c1["name"], "רמת ריחוק (ק\"מ)": round(avg, 2)})
        
        final_score = sum(all_avg_dist) / len(all_avg_dist)

        # 2. תצוגת תוצאות
        st.divider()
        st.metric("רמת פיזור כללית של הקבוצה", f"{final_score:.2f} ק\"מ")
        
        st.subheader("מפת פריסת היישובים")
        df_map = pd.DataFrame(map_data)
        st.map(df_map)
        
        st.divider()
        st.subheader("פירוט רמות ריחוק לפי יישוב")
        df_results = pd.DataFrame(results)
        st.table(df_results)
        
        st.success("החישוב הושלם בהצלחה!")

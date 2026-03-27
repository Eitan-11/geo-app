import streamlit as st
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pandas as pd
import time

# הגדרות דף
st.set_page_config(page_title="מחשבון פיזור יישובים", page_icon="📍")

st.title("📍 מדד הפיזור הגיאוגרפי")
st.markdown("חישוב רמת הריחוק הממוצעת והצגת המיקומים על מפה אינטראקטיבית.")

# תיבת קלט
input_cities = st.text_area("הזינו שמות יישובים (מופרדים בפסיק):", 
                            "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")

if st.button("חשב רמת פיזור והצג מפה"):
    # שינוי חשוב: שם ייחודי מאוד והגדלת זמן ההמתנה (timeout)
    # תשנה את 'my_unique_geo_app_2026_user123' למשהו אישי שלך
    geolocator = Nominatim(user_agent="my_unique_geo_app_2026_user123", timeout=10)
    
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    
    locations = []
    map_data = []
    
    with st.spinner('מאתר מיקומים ומחשב מרחקים...'):
        for name in city_list:
            try:
                search_query = name if "ישראל" in name or "Israel" in name else f"{name}, Israel"
                # הוספת timeout גם כאן
                loc = geolocator.geocode(search_query)
                
                if loc:
                    locations.append({"name": name, "coord": (loc.latitude, loc.longitude)})
                    map_data.append({"lat": loc.latitude, "lon": loc.longitude})
                
                # הוספת השהיה קצרה בין בקשה לבקשה כדי לא להעמיס על השרת
                time.sleep(1) 
                
            except Exception as e:
                st.error(f"שגיאה באיתור היישוב {name}: שרת המפות לא זמין כרגע. נסה שוב בעוד דקה.")
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

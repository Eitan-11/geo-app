import streamlit as st
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import pandas as pd

# הגדרות דף
st.set_page_config(page_title="מחשבון פיזור יישובים", page_icon="📍")

st.title("📍 מדד הפיזור הגיאוגרפי")
st.markdown("כלי לחישוב רמת הריחוק הממוצעת של קבוצת יישובים.")

# תיבת קלט
input_cities = st.text_area("הזינו שמות יישובים (מופרדים בפסיק):", 
                            "נופית, צור הדסה, רחובות, זכרון יעקב, גבעת שמואל")

if st.button("חשב רמת פיזור"):
    # שימוש ב-user_agent ייחודי כדי למנוע חסימות
    geolocator = Nominatim(user_agent="geo_dispersion_tool_v1")
    city_list = [c.strip() for c in input_cities.split(",") if c.strip()]
    
    locations = []
    with st.spinner('מאתר מיקומים על המפה...'):
        for name in city_list:
            # מחפש בישראל כברירת מחדל
            search_query = name if "ישראל" in name or "Israel" in name else f"{name}, Israel"
            loc = geolocator.geocode(search_query)
            if loc:
                locations.append({"name": name, "coord": (loc.latitude, loc.longitude)})
            else:
                st.warning(f"⚠️ לא מצאתי את: {name}")

    if len(locations) < 2:
        st.error("חובה להזין לפחות שני יישובים תקינים.")
    else:
        results = []
        all_avg_dist = []
        
        for i, c1 in enumerate(locations):
            dists = [geodesic(c1["coord"], c2["coord"]).km for j, c2 in enumerate(locations) if i != j]
            avg = sum(dists) / len(dists)
            all_avg_dist.append(avg)
            results.append({"יישוב": c1["name"], "רמת ריחוק (ק\"מ)": round(avg, 2)})
        
        st.divider()
        st.subheader("תוצאות")
        
        # הצגת המדד הסופי בגדול
        final_score = sum(all_avg_dist) / len(all_avg_dist)
        st.metric("רמת פיזור כללית של הקבוצה", f"{final_score:.2f} ק\"מ")
        
        # טבלה מפורטת
        st.write("פירוט לפי יישוב (ממוצע המרחקים שלו משאר הקבוצה):")
        st.table(pd.DataFrame(results))

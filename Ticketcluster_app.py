import streamlit as st
import requests
import pandas as pd

# -----------------------------
# CONFIG: INSERT YOUR API KEYS
# -----------------------------
TICKETMASTER_API_KEY = "YOUR_TICKETMASTER_API_KEY"
GOOGLE_PLACES_API_KEY = "YOUR_GOOGLE_PLACES_API_KEY"

# -----------------------------
# FUNCTIONS
# -----------------------------

def fetch_ticketmaster_events(lat, lon, radius_km=10, size=20):
    """Fetch events from Ticketmaster API."""
    url = "https://app.ticketmaster.com/discovery/v2/events.json"
    params = {
        "apikey": TICKETMASTER_API_KEY,
        "latlong": f"{lat},{lon}",
        "radius": radius_km,
        "unit": "km",
        "size": size,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        events = []
        if "_embedded" in data and "events" in data["_embedded"]:
            for event in data["_embedded"]["events"]:
                name = event.get("name", "Unknown Event")
                venue_data = event["_embedded"]["venues"][0]
                venue_name = venue_data.get("name", "Unknown Venue")
                venue_lat = float(venue_data["location"]["latitude"])
                venue_lon = float(venue_data["location"]["longitude"])
                start_date = event["dates"]["start"].get("localDate", "TBA")
                # FOMO score: can improve later with popularity/distance
                fomo_score = min(100, 10 + len(events) * 5)
                events.append({
                    "name": name,
                    "venue": venue_name,
                    "lat": venue_lat,
                    "lon": venue_lon,
                    "start_date": start_date,
                    "fomo_score": fomo_score
                })
        return events
    except Exception as e:
        st.warning(f"Ticketmaster API unavailable: {e}")
        return []

def fetch_google_places(lat, lon, radius_m=1000, place_type="bar"):
    """Fallback: fetch nearby venues from Google Places API."""
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": GOOGLE_PLACES_API_KEY,
        "location": f"{lat},{lon}",
        "radius": radius_m,
        "type": place_type,
        "opennow": True
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        data = response.json()
        events = []
        for idx, place in enumerate(data.get("results", [])):
            name = place.get("name", "Unknown Venue")
            loc = place["geometry"]["location"]
            fomo_score = min(100, 10 + idx * 5)
            events.append({
                "name": name,
                "venue": name,
                "lat": loc["lat"],
                "lon": loc["lng"],
                "start_date": "Now",
                "fomo_score": fomo_score
            })
        return events
    except Exception as e:
        st.warning(f"Google Places API unavailable: {e}")
        return []

def get_events(lat, lon):
    """Try Ticketmaster first, fallback to Google Places."""
    events = fetch_ticketmaster_events(lat, lon)
    if not events:
        events = fetch_google_places(lat, lon)
    return events

def generate_gpt_summary(events, top_n=5):
    """Generate simple GPT-style summary of top events."""
    events_sorted = sorted(events, key=lambda x: x["fomo_score"], reverse=True)[:top_n]
    summary_lines = [
        f"{idx+1}. {e['name']} at {e['venue']} (FOMO Score: {e['fomo_score']})"
        for idx, e in enumerate(events_sorted)
    ]
    return "\n".join(summary_lines)

# -----------------------------
# STREAMLIT UI
# -----------------------------
st.set_page_config(page_title="FOMO App", layout="wide")
st.title("FOMO - Find Hotspots and Events Around You")

with st.sidebar:
    st.header("Search Location")
    lat = st.number_input("Latitude", value=-33.8688, format="%.6f")
    lon = st.number_input("Longitude", value=151.2093, format="%.6f")
    radius = st.slider("Search Radius (km)", 1, 50, 10)
    search_button = st.button("Find Hotspots")

if search_button:
    events = get_events(lat, lon)
    if not events:
        st.info("No events found in this area.")
    else:
        df = pd.DataFrame(events)
        st.subheader("Top Events / Venues")
        st.dataframe(df[["name", "venue", "start_date", "fomo_score"]])

        st.subheader("Event Map")
        st.map(df.rename(columns={"lat": "latitude", "lon": "longitude"}))

        st.subheader("FOMO Summary")
        summary_text = generate_gpt_summary(events)
        st.text(summary_text)
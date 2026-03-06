from fastapi import APIRouter, HTTPException, Query, Response
from datetime import datetime
from app.services.alert_state import global_alert_state
from app.db.database import get_recent_alerts, get_alert_statistics
import logging

from app.api.models import AlertsResponse, HistoryResponse, StatisticsResponse

router = APIRouter()
logger = logging.getLogger("pikudhaoref_app.routes")

@router.get(
    "/api/alerts", 
    summary="Get Active Alerts", 
    description="Fetches the current active alerts from the Rockets & Missles alerts API. Responses are cached.",
    tags=["Alerts"],
    response_model=AlertsResponse
)
async def get_alerts(mock: bool = False):
    """
    Retrieves active alerts instantaneously from global memory state.
    If 'mock=true' is passed, simulates a massive attack for UI testing.
    """
    if mock:
        # Extensive mock list from user request
        mock_cities = list(set([
            "פלמחים", "בית אלעזרי", "בית חלקיה", "בני ראם", "גדרה", "גני טל", "חפץ חיים", "יבנה", "יד בנימין", 
            "כפר הנגיד", "קדרון", "רבדים", "אזור תעשייה רבדים", "בית גמליאל", "בן זכאי", "בניה", "גבעת ברנר", 
            "גבעת וושינגטון", "כפר אביב", "כפר מרדכי", "כרם ביבנה", "מישר", "משגב דב", "מתחם בני דרום", "עשרת", 
            "קבוצת יבנה", "שדמה", "אזור תעשייה גדרה", "מעון צופיה", "אזור תעשייה עד הלום", "אשדוד - א,ב,ד,ה", 
            "אשדוד - איזור תעשייה צפוני", "אשדוד - ג,ו,ז", "אשדוד - ח,ט,י,יג,יד,טז", "אשדוד -יא,יב,טו,יז,מרינה,סיטי", 
            "בני דרום", "ניר גלים", "אביגדור", "אבן שמואל", "אורות", "אזור תעשייה באר טוביה", "אזור תעשייה קריית גת", 
            "אחווה", "אחוזם", "איתן", "אל עזי", "באר טוביה", "גת", "ינון", "כפר אחים", "כפר הרי''ף וצומת ראם", 
            "כפר ורבורג", "נועם", "עוזה", "ערוגות", "קריית גת", "כרמי גת", "קריית מלאכי", "שדה משה", "שלווה", 
            "תימורים", "תלמי יחיאל", "אזור תעשייה כנות", "ביצרון", "בני עי''ש", "גן הדרום", "גן יבנה", "חצב", 
            "חצור", "כנות", "נווה מבטח", "תחנת רכבת קריית מלאכי - יואב", "אלומה", "אמונים", "בית עזרא", "ברכיה", 
            "גבעתי", "הודיה", "ורדון", "זבדיאל", "זוהר", "זרחיה", "יד נתן", "כוכב מיכאל", "כפר סילבר", "לכיש", 
            "מנוחה", "מרכז שפירא", "משואות יצחק", "משען", "נגבה", "נהורה", "נוגה", "נחלה", "ניצן", "ניצנים", 
            "ניר בנים", "ניר ח''ן", "ניר ישראל", "סגולה", "עוצם", "עזר", "עזריקם", "עין צורים", "קדמה", "קוממיות", 
            "רווחה", "שדה יואב", "שדה עוזיהו", "שחר", "שפיר", "שתולים", "אזור תעשייה תימורים", "פארק תעשייה ראם", 
            "אזור תעשייה צפוני אשקלון", "אשקלון - דרום", "אשקלון - צפון", "באר גנים", "אזור תעשייה הדרומי אשקלון", 
            "בית שקמה", "בת הדר", "גיאה", "חלץ", "מבקיעים", "שדה דוד", "תלמי יפה", "תלמים", "אביעזר", "אדרת", 
            "אזור תעשייה הר טוב - צרעה", "אשתאול", "בית שמש", "בקוע", "גבעות עדן", "גיזו", "הראל", "זנוח", 
            "טל שחר", "ישעי", "כפר אוריה", "לטרון", "מחסיה", "מיני ישראל - נחשון", "מסילת ציון", "נווה מיכאל - רוגלית", 
            "נווה שלום", "נחם", "נחשון", "נתיב הל''ה", "צלפון", "צרעה", "רטורנו - גבעת שמש", "תעוז", "תרום", 
            "אבו גוש", "בית מאיר", "בר גיורא", "גבעת יערים", "יד השמונה", "כסלון", "כפר הנוער קריית יערים", "מטע", 
            "נווה אילן", "נטף", "נס הרים", "עין נקובא", "עין ראפה", "קריית יערים", "רמת רזיאל", "שואבה", "שורש", 
            "אזור תעשייה ברוש", "בית נקופה", "הר אדר", "מעלה החמישה", "צובה", "קריית ענבים", "מבוא ביתר", "צור הדסה", 
            "כפר מנחם", "בית גוברין", "בית ניר", "גלאון", "גפן", "זכריה", "כפר זוהרים", "לוזית", "נחושה", "עגור", 
            "צפרירים", "שדות מיכה", "שריגים - לי-און", "תירוש", "גבעת ישעיהו", "אלון שבות", "אלעזר", "אפרת", 
            "ביתר עילית", "בת עין", "הר גילה", "כפר אלדד", "כפר עציון", "כרמי צור", "מגדל עוז", "מיצד", "מעלה עמוס", 
            "מעלה רחבעם", "נווה דניאל", "נוקדים", "פארק תעשיות מגדל עוז", "פני קדם", "ראש צורים", "שדה בר", "תלם", 
            "תקוע", "אדורה", "אדורים", "בית חג\"י", "הגבעה הצהובה", "מעלה חבר", "נגוהות", "עתניאל", "צומת הגוש", 
            "קרית ארבע", "איבי הנחל", "אפקה", "בית הברכה", "בר כוכבא", "גבעות", "היישוב היהודי חברון", "חוות ארץ האיילים", 
            "חוות מדבר חבר", "חוות מלאכי אברהם", "חוות נחלת אבות", "חוות עדן", "חוות קשואלה", "חוות תלם צפון", 
            "מצפה זי\"ו", "עוז וגאון", "שדה בועז", "תקוע ד' וה'", "אזור תעשייה מישור אדומים", "מעלה אדומים", "קדר", 
            "חוות הרועה העברי", "חוות צאן קדר", "קדר דרום", "אלון", "כפר אדומים", "מצפה יריחו", "עלמון", "מצפה חגית", 
            "נופי פרת", "בני דקלים", "כרמי קטיף ואמציה", "נטע", "שומריה", "שקף", "אליאב", "חוות אשכולות", "גבעת השלושה", 
            "גת רימון", "כפר סירקין", "מעש", "פתח תקווה", "אלעד", "בארות יצחק", "בני עטרות", "גבעת כ''ח", "מגשימים", 
            "מזור", "נופך", "נחלים", "נחשונים", "עינת", "ראש העין", "רינתיה", "אזור תעשייה חבל מודיעין שוהם", "בית נחמיה", 
            "בית עריף", "ברקת", "חדיד", "טירת יהודה", "כפר טרומן", "שוהם", "אזור תעשייה אפק ולב הארץ", "איירפורט סיטי", 
            "תל אביב - דרום העיר ויפו", "תל אביב - מזרח", "תל אביב - מרכז העיר", "תל אביב - עבר הירקון", "אור יהודה", 
            "אזור", "בני ברק", "בת ים", "גבעת שמואל", "גבעתיים", "הרצליה - מערב", "הרצליה - מרכז וגליל ים", "חולון", 
            "יהוד מונוסון", "כפר שמריהו", "מקווה ישראל", "סביון", "פארק אריאל שרון", "קריית אונו", "רמת גן - מזרח", 
            "רמת גן - מערב", "רמת השרון", "גני תקווה", "בית עלמין מורשה", "מתחם גלילות", "מתחם פי גלילות", "גיבתון", 
            "גמזו", "גן שלמה", "חשמונאים", "כפר דניאל", "כפר רות", "לפיד", "מבוא חורון", "מבוא מודיעים", "מודיעין - ליגד סנטר", 
            "מודיעין מכבים רעות", "מודיעין עילית", "מתתיהו", "נוף איילון", "שעלבים", "נצר סרני", "פארק תעשיות פלמחים", 
            "ראשון לציון - מזרח", "ראשון לציון - מערב", "רחובות", "שילת", "אזור תעשייה נשר - רמלה", "אחיסמך", "אירוס", 
            "באר יעקב", "בית חנן", "בית עובד", "בן שמן", "גאליה", "גינתון", "גן שורק", "ישרש", "כפר נוער בן שמן", 
            "לוד", "מצליח", "נטעים", "ניר צבי", "נס ציונה", "עיינות", "רמלה", "תעשיון צריפין", "אחיעזר", "בית דגן", 
            "בית חשמונאי", "בית עוזיאל", "גזר", "גני הדר", "גני יוחנן", "זיתן", "חולדה", "חמד", "יגל", "יד רמב''ם", 
            "יסודות", "יציץ", "כפר ביל''ו", "כפר בן נון", "כפר חב''ד", "כפר שמואל", "כרמי יוסף", "מזכרת בתיה", 
            "משמר איילון", "משמר דוד", "משמר השבעה", "נאות קדומים", "נען", "נצר חזני", "סתריה", "עזריה", "פדיה", 
            "פתחיה", "צפריה", "קריית עקרון", "רמות מאיר", "גנות", "כפר האורנים", "מודיעין - ישפרו סנטר", "אלפי מנשה", 
            "אלקנה", "עץ אפרים", "צופים", "שערי תקווה", "סלעית", "אביחיל", "גבעת חן", "נתניה - מזרח", "נתניה - מערב", 
            "רעננה", "שושנת העמקים", "אורנית", "אייל", "אלישמע", "בית ברל", "בני דרור", "ג'לג'וליה", "גאולים", 
            "גן חיים", "גני עם", "הוד השרון", "חגור", "חורשים", "חרות", "טייבה", "טירה", "יעבץ", "יעף", "ירחיב", 
            "ירקונה", "כוכב יאיר - צור יגאל", "כפר ברא", "כפר הס", "כפר מל''ל", "כפר סבא", "כפר עבודה", "כפר קאסם", 
            "משמרת", "מתן", "נווה ימין", "נווה ירק", "ניר אליהו", "נירית", "עדנים", "עזריאל", "עין ורד", "עין שריד", 
            "פורת", "פרדסיה", "צופית", "צור יצחק", "צור משה", "צור נתן", "קדימה צורן", "קלנסווה", "רמות השבים", 
            "רמת הכובש", "שדה ורבורג", "שדי חמד", "שער אפרים", "תחנת רכבת ראש העין", "תל מונד", "אבן יהודה", 
            "אודים", "ארסוף", "בית יהושע", "בני ציון", "בצרה", "געש", "חרוצים", "יקום", "כפר נטר", "מכון וינגייט", 
            "רשפון", "שפיים", "תל יצחק", "אזור תעשייה כפר יונה", "אזור תעשייה עמק חפר", "אחיטוב", "אליכין", 
            "אלישיב", "אמץ", "בארותיים", "בורגתה", "בחן", "בית הלוי", "בית חרות", "בית ינאי", "בית יצחק - שער חפר", 
            "ביתן אהרן", "בת חן", "בת חפר", "גאולי תימן", "גבעת חיים איחוד", "גבעת חיים מאוחד", "גבעת שפירא", 
            "גן יאשיה", "גנות הדר", "הדר עם", "המעפיל", "המרכז האקדמי רופין", "העוגן", "זמר", "חבצלת השרון וצוקי ים", 
            "חגלה", "חופית", "חיבת ציון", "חניאל", "חרב לאת", "יד חנה", "ינוב", "כפר הרא''ה", "כפר ויתקין", "כפר חיים", 
            "כפר ידידיה", "כפר יונה", "כפר מונש", "מכמורת", "מסוף אורנית", "מעברות", "משמר השרון", "נורדיה", 
            "ניצני עוז", "נעורים", "עולש", "עין החורש", "תנובות", "מרכז אזורי דרום השרון", "ברקן", "חוות יאיר", 
            "יקיר", "נופים", "עמנואל", "קריית נטפים", "קרני שומרון", "רבבה", "אבני חפץ", "אזור תעשייה אריאל", 
            "אזור תעשייה בראון", "אזור תעשייה ברקן", "אזור תעשייה שחק", "אזור תעשייה שער בנימין", "איתמר", 
            "אלון מורה", "בית אל", "בית אריה", "בית חורון", "ברוכין", "גבעת אסף", "גבעת הראל", "דולב", "הר ברכה", 
            "חוות אביחי", "חוות גלעד", "חיננית", "חרמש", "טלמון", "יצהר", "כוכב יעקב", "כפר תפוח", "מבוא דותן", 
            "מגדלים", "מעלה לבונה", "נווה צוף", "נחליאל", "נילי", "נעלה", "עטרת", "עלי זהב - לשם", "עלי", "עמיחי", 
            "ענב", "עפרה", "פדואל", "פסגות", "קדומים", "רחלים", "ריחן", "שבות רחל", "שבי שומרון", "שילה", "שקד", 
            "תל ציון", "אביתר", "אחיה", "אריאל", "אש קודש", "גבעת הרואה", "גבעת פורת יוסף", "גופנה", "דורות עילית", 
            "חוות אביה", "חוות אל נווה", "חוות אלחי", "חוות מגדלים", "חוות מגנזי", "חוות מרום שמואל", "חוות נווה צוף", 
            "חוות נוף אב\"י", "חוות נחל שילה", "חוות עולם חסד", "חוות צרידה", "חוות שדה", "חוות שוביאל", "חוות שחרית", 
            "חומש", "חרמש דרום", "חרשה", "טל מנשה", "יבוא דודי", "כרם רעים", "מגרון", "מכינת אלישע", "נופי נחמיה", 
            "נריה", "עופרים", "רמת מגרון", "שדה אפרים", "ארגמן", "בקעות", "גבע בנימין", "גיתית", "גלגל", "חמדת", 
            "חמרה", "ייט''ב", "יפית", "כוכב השחר", "מבואות יריחו", "מחולה", "מכורה", "מעלה אפרים", "מעלה מכמש", 
            "משואה", "משכיות", "נעמה", "נערן", "נתיב הגדוד", "עדי עד", "פצאל", "קידה", "רועי", "רותם", "רימונים", 
            "שדמות מחולה", "תומר", "שלומציון", "אעירה השחר", "בני אדם", "בתרונות", "החווה של אורי כהן", "החווה של זוהר", 
            "החווה של יאיא", "החווה של מנחם", "החווה של עשהאל", "חוות בניהו", "חוות גנות", "חוות הרשאש", "חוות חנינא", 
            "חוות יד השומר", "חוות ינון", "חוות מלכיאל", "חוות מעלה אהוביה", "חוות נחלת צבי", "חוות עמיאל", "חוות פריאל", 
            "חוות ראש תאנה", "מלאכי השלום", "מצפה דני", "מצפור פצאל", "נווה ארז", "עינות קדם"
        ]))

        return {
            "message": "MOCK MODE ACTIVE",
            "is_online": True,
            "data": {
                "id": "mock_barrage_2026",
                "cat": "1",
                "title": "ירי רקטות וטילים",
                "data": mock_cities,
                "desc": "היכנסו למרחב מוגן, שהו בו 10 דקות"
            }
        }

    alerts_data = global_alert_state.get()
    
    logger.info(f"API Request: /api/alerts (Online: {global_alert_state.is_online}, HasData: {alerts_data is not None})")
    
    return {
        "message": "Active alerts found." if alerts_data else "No active alerts at the moment.",
        "data": alerts_data,
        "is_online": global_alert_state.is_online
    }

@router.get(
    "/api/alerts/history", 
    summary="Get Alert History (Last 24 Hours)", 
    description="Fetches alerts that occurred in the last 24 hours from the local SQLite database.",
    tags=["Alerts"],
    response_model=HistoryResponse
)
async def get_alert_history(hours: int = 24):
    """
    Retrieves historical alerts. 
    By default fetches the last 24 hours.
    """
    try:
        history_data = get_recent_alerts(hours=hours)
        return {"message": "History retrieved successfully", "data": history_data}
    except Exception as e:
        logger.error(f"Failed to fetch history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching history.")

@router.get(
    "/api/alerts/statistics",
    summary="Get Alert Statistics By City",
    description="Fetches aggregated statistics of alerts per city based on a given timeframe.",
    tags=["Statistics"],
    response_model=StatisticsResponse
)
async def get_statistics(timeframe: str = Query("24h", description="Options: 24h, 1w, 1m, 6m, 1y, all")):
    """
    Returns an aggregated list of cities and their alert counts.
    """
    try:
        stats_data = get_alert_statistics(timeframe=timeframe)
        return {"message": f"Statistics for {timeframe} retrieved successfully", "data": stats_data}
    except Exception as e:
        logger.error(f"Failed to fetch statistics: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching statistics.")

@router.get(
    "/rss",
    summary="Get Alert RSS Feed",
    description="Returns an RSS XML feed of recent alerts.",
    tags=["RSS"]
)
async def get_rss_feed():
    try:
        # Get last 24h of alerts
        history_data = get_recent_alerts(hours=24)
        
        # Build XML
        current_time = datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0200")
        
        xml_content = f"""<?xml version="1.0" encoding="UTF-8" ?>
<rss version="2.0">
  <channel>
    <title>התראות ביטחוניות</title>
    <link>http://localhost:8000/</link>
    <description>התראות בזמן אמת</description>
    <lastBuildDate>{current_time}</lastBuildDate>
"""
        
        for alert in history_data:
            # Parse SQLite timestamp (which is ISO format) into RSS RFC 822 format
            try:
                alert_time = datetime.fromisoformat(alert['timestamp']).strftime("%a, %d %b %Y %H:%M:%S +0200")
            except:
                alert_time = current_time

            locations = ", ".join(alert['locations'])
            
            xml_content += f"""
    <item>
      <title>{alert['title']} - {locations}</title>
      <link>http://localhost:8000/archive</link>
      <description>{alert['description']} באזורים: {locations}</description>
      <pubDate>{alert_time}</pubDate>
      <guid>{alert['alert_id']}</guid>
    </item>"""
            
        xml_content += """
  </channel>
</rss>"""

        return Response(content=xml_content, media_type="application/xml")
    except Exception as e:
        logger.error(f"Failed to generate RSS: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while generating RSS feed.")

from app.api.models import GeocodeRequest, GeocodeResponse
from app.services.geocode_service import geocode_service

@router.post(
    "/api/geocode",
    summary="Resolve coordinates for a list of cities",
    description="Accepts a list of cities and returns a mapping from city name to its resolved GeoJSON shape. Used as a backend fallback to Nominatim avoiding local browser quota limits.",
    tags=["Geocoding"],
    response_model=GeocodeResponse
)
async def resolve_cities(request: GeocodeRequest):
    print("[ROUTE TRACE] Hit /api/geocode")
    try:
        print(f"[ROUTE TRACE] Parsed Request: {request.cities}")
        if not request.cities:
            print("[ROUTE TRACE] Empty cities list")
            return {"message": "No cities provided.", "data": {}}
            
        logger.info(f"API Request: /api/geocode for {len(request.cities)} cities.")
        
        print("[ROUTE TRACE] Calling geocode_service.get_coordinates...")
        resolved_data = await geocode_service.get_coordinates(request.cities)
        print("[ROUTE TRACE] Successfully returned from get_coordinates")
        
        return {
            "message": "Cities resolved successfully.",
            "data": resolved_data
        }
    except Exception as e:
        print(f"[ROUTE TRACE] Exception caught: {e}")
        logger.error(f"Failed to geocode cities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during geocoding.")

from app.api.models import GeolocationsResponse, GeolocationCity
from app.db.database import get_all_unique_cities, get_all_geolocations

@router.get(
    "/api/geolocations_list",
    summary="Get All Cities and Geolocation Status",
    description="Returns a list of all historically recorded cities and marks whether they have cached geographical coordinates.",
    tags=["Geocoding"],
    response_model=GeolocationsResponse
)
async def get_geolocations_list():
    try:
        all_cities = get_all_unique_cities()
        cached_dict = get_all_geolocations()
        
        response_data = []
        for city in all_cities:
            is_cached = city in cached_dict
            geo_data = cached_dict.get(city) if is_cached else None
            
            response_data.append(GeolocationCity(
                city_name=city,
                is_cached=is_cached,
                geo_data=geo_data if geo_data != "NOT_FOUND" else None
            ))
            
        # Sort so missing ones or alphabetically makes sense, but frontend can handle sorting
        response_data.sort(key=lambda x: (x.is_cached, x.city_name))

        return {
            "message": f"Successfully fetched {len(response_data)} cities.",
            "data": response_data
        }
    except Exception as e:
        logger.error(f"Failed to fetch geolocations list: {e}")
        raise HTTPException(status_code=500, detail="Internal server error fetching geolocations list.")

from pydantic import BaseModel

class SyncResponse(BaseModel):
    message: str

@router.post(
    "/api/geolocations/sync",
    summary="Trigger Manual Geolocation Sync",
    description="Forces the background worker to execute a batch of missing geolocations immediately.",
    tags=["Geocoding"],
    response_model=SyncResponse
)
async def trigger_geolocations_sync():
    try:
        from app.main import geocode_missing_cities_job
        import asyncio
        from functools import partial
        
        loop = asyncio.get_event_loop()
        
        # Pass limit_to_five=False to process the entire backlog instead of just 5
        job_func = partial(geocode_missing_cities_job, limit_to_five=False)
        await loop.run_in_executor(None, job_func)
        
        return {"message": "Manual sync batch triggered successfully. Wait a moment and refresh."}
    except Exception as e:
        logger.error(f"Manual sync failed: {e}")
        raise HTTPException(status_code=500, detail="Failed to trigger manual sync.")

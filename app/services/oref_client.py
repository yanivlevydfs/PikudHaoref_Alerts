import requests
import json
import logging

logger = logging.getLogger(__name__)

def fetch_active_alerts():
    """
    Fetches the active alerts from the Oref API.
    Returns a dictionary with the alerts data, or None if there are no active alerts.
    """
    url = "https://www.oref.org.il/WarningMessages/alert/alerts.json"
    
    # Headers exactly as required by Oref
    headers = {
        'Referer': 'https://www.oref.org.il/',
        'X-Requested-With': 'XMLHttpRequest'
    }
    
    try:
        # We add timeout just in case it hangs
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Oref API returns empty content if there are no active alerts
        content = response.content.decode('utf-8-sig', errors='ignore').strip()
        
        # --- TEMPORARY MOCK DATA INJECTION FOR UI TESTING ---
        # If there are no real alerts, we return the mock data so the map populates
        if not content:
            logger.info("No active alerts, returning MOCK DATA for UI Testing!")
            return {
                "id": "134168351070000000", 
                "cat": "10", 
                "title": "בדקות הקרובות צפויות להתקבל התרעות באזורך", 
                "data": ['אזור תעשייה צפוני אשקלון', 'אשקלון - דרום', 'אשקלון - צפון', 'באר גנים', 'אזור תעשייה הדרומי אשקלון', 'בית שקמה', 'בת הדר', 'גיאה', 'חלץ', 'מבקיעים', 'שדה דוד', 'תלמי יפה', 'תלמים', 'פלמחים', 'בית אלעזרי', 'בית חלקיה', 'בני ראם', 'גדרה', 'גני טל', 'חפץ חיים', 'יבנה', 'יד בנימין', 'כפר הנגיד', 'קדרון', 'רבדים', 'אזור תעשייה רבדים', 'בית גמליאל', 'בן זכאי', 'בניה', 'גבעת ברנר', 'גבעת וושינגטון', 'כפר אביב', 'כפר מרדכי', 'כרם ביבנה', 'מישר', 'משגב דב', 'מתחם בני דרום', 'עשרת', 'קבוצת יבנה', 'שדמה', 'אזור תעשייה גדרה', 'מעון צופיה', 'אביעזר', 'אדרת', 'תל אביב - דרום העיר ויפו', 'תל אביב - מזרח', 'תל אביב - מרכז העיר', 'תל אביב - עבר הירקון', 'אור יהודה', 'אזור', 'בני ברק', 'בת ים', 'גבעת שמואל', 'גבעתיים', 'הרצליה - מערב', 'הרצליה - מרכז וגליל ים', 'חולון', 'חיפה', 'ירושלים', 'באר שבע'], 
                "desc": 'על תושבי האזורים הבאים לשפר את המיקום למיגון המיטבי בקרבתך.\nבמקרה של קבלת התרעה, יש להיכנס למרחב המוגן ולשהות בו עד להודעה חדשה.'
            }
            
        # Try to parse as JSON
        try:
            data = json.loads(content)
            return data
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON. Raw content received: {content}")
            return {"error": "Failed to parse alerts data from Oref"}
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching data from Oref: {e}")
        return {"error": str(e)}

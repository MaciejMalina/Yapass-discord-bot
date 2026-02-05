import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from dotenv import load_dotenv

load_dotenv()
SCOPES = ['https://www.googleapis.com/auth/calendar']
CALENDAR_ID = os.getenv('CALENDAR_ID')

def get_calendar_service():
    creds = service_account.Credentials.from_service_account_file(
        'credentials.json', scopes=SCOPES)
    service = build('calendar', 'v3', credentials=creds)
    return service

def add_event(summary, start_iso, end_iso, description, location="Brak"):
    """
    Dodaje wydarzenie do kalendarza Google.
    Zwraca htmlLink do utworzonego wydarzenia.
    """
    service = get_calendar_service()
    
    event = {
        'summary': summary,
        'location': location,
        'description': description,
        'start': {
            'dateTime': start_iso,
            'timeZone': 'Europe/Warsaw',
        },
        'end': {
            'dateTime': end_iso,
            'timeZone': 'Europe/Warsaw',
        },
        'reminders': {
            'useDefault': True,
        },
    }

    try:
        created_event = service.events().insert(
            calendarId=os.getenv('CALENDAR_ID'), 
            body=event
        ).execute()
        
        return created_event.get('htmlLink')
    except Exception as e:
        print(f"Błąd podczas dodawania do Google Calendar: {e}")
        raise e
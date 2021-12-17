from __future__ import print_function

import datetime
import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bs4 import BeautifulSoup

import requests

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]
TIMEZONE = datetime.timezone(datetime.timedelta(hours=1))


def handle_auth():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())
    return creds


def create_event(service, calendar_id, contest_name, start_datetime, contest_length):
    start_dt = datetime.datetime.strptime(start_datetime, "%b/%d/%Y %H:%M").astimezone(
        TIMEZONE
    )
    hours, minutes = list(map(int, contest_length.split(":")))
    duration = datetime.timedelta(hours=hours, minutes=minutes)
    end_dt = start_dt + duration
    event = {
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "summary": contest_name,
    }
    service.events().insert(calendarId=calendar_id, body=event).execute()


def add_contests(service, calendar_id):
    html = requests.get("https://codeforces.com/contests").text
    soup = BeautifulSoup(html, "html.parser")
    for tr in soup.table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) > 2:
            create_event(
                service,
                calendar_id,
                tds[0].string,
                tds[2].a.span.string,
                tds[3].string,
            )

def delete_next_contests(service, calendar_id, num_contests):
    events_result = service.events().list(calendarId=calendar_id, timeMin=datetime.datetime.now(TIMEZONE).isoformat(),
                                              maxResults=num_contests, singleEvents=True,
                                              orderBy='startTime').execute()
    events = events_result.get('items', [])

    if not events:
        print('No upcoming events found.')
        return

    for event in events:
        service.events().delete(calendarId = calendar_id, eventId = event["id"]).execute()

def main():
    creds = handle_auth()

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = next(
            x
            for x in service.calendarList().list().execute()["items"]
            if x["summary"] == "Contests"
        )["id"]
        # add_contests(service, calendar_id)
        # delete_next_contests(service, calendar_id, 10)

    except HttpError as error:
        print("An HTTP error occurred: %s" % error)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main()

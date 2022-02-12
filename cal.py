from datetime import datetime, timedelta, timezone
import os
import sys, getopt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bs4 import BeautifulSoup

import requests

SCOPES = ["https://www.googleapis.com/auth/calendar"]
RUSSIA_TIMEZONE = timezone(timedelta(hours=3))
CALENDAR_NAME = "Contests"

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


def create_event(
    service, calendar_id, contest_name, start, contest_length, quiet
):
    start_dt = datetime.strptime(start, "%b/%d/%Y %H:%M").replace(
        tzinfo=RUSSIA_TIMEZONE
    )
    #TODO: Get duration with format constructor
    hours, minutes = list(map(int, contest_length.split(":")))[
        :2
    ]  # Time format can be hh:mm::ss (e.g. Kotlin Heroes)
    duration = timedelta(hours=hours, minutes=minutes)
    end_dt = start_dt + duration
    event = {
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "summary": contest_name,
    }
    service.events().insert(calendarId=calendar_id, body=event).execute()
    if not quiet:
        print("Inserted: {}".format(contest_name.strip()))


def add_contests(service, calendar_id, quiet):
    """Add all codeforces upcoming contests as event calendars"""
    html = requests.get("https://codeforces.com/contests").text
    soup = BeautifulSoup(html, "html.parser")
    if soup.table == None:
        raise Exception("Cannot add contests: Contests table not found")
    for tr in soup.table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) > 2:
            create_event(
                service,
                calendar_id,
                tds[0].string,
                tds[2].a.span.string,
                tds[3].string,
                quiet,
            )


def delete_next_contests(service, calendar_id, num_contests, quiet):
    """Delete next `num_contests` contests in calendar with id `calendar_id`"""
    now = datetime.utcnow().isoformat() + "Z"  # Z for UTC time
    events_result = (
        service.events()
        .list(
            calendarId=calendar_id,
            timeMin=now,
            maxResults=num_contests,
            singleEvents=True,
            orderBy="startTime",
        )
        .execute()
    )
    events = events_result.get("items", [])

    for event in events:
        service.events().delete(calendarId=calendar_id, eventId=event["id"]).execute()
        if not quiet:
            print("Deleted: {}".format(event["summary"].strip()))


def main(argv):
    try:
        creds = handle_auth()
    except Exception as e:
        print(f"Failed auth: ${e}")
        try: 
            os.remove("token.json")
            print("Deleted token.json")
            print("Token might have been expired. Rerun to get new token")
        except OSError:
            pass
        sys.exit(1)

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = next(
            x
            for x in service.calendarList().list().execute()["items"]
            if x["summary"] == CALENDAR_NAME
        )["id"]

        try:
            opts, _ = getopt.getopt(argv, "q")
        except getopt.GetoptError:
            print("Usage: python3 cal.py [-q]")
            sys.exit(2)
        quiet = ("-q", "") in opts
        if not quiet:
            print("Updating next 10 contests ...")
        delete_next_contests(service, calendar_id, 10, quiet)
        add_contests(service, calendar_id, quiet)

    except HttpError as error:
        print("An HTTP error occurred: %s" % error)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main(sys.argv[1:])

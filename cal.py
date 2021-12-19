from datetime import datetime, timedelta, timezone
import os.path
import sys, getopt

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from bs4 import BeautifulSoup

import requests

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]
RUSSIA_TIMEZONE = timezone(timedelta(hours=3))


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
    service, calendar_id, contest_name, start_datetime, contest_length, verbose
):
    start_dt = datetime.strptime(start_datetime, "%b/%d/%Y %H:%M").replace(tzinfo=RUSSIA_TIMEZONE)
    hours, minutes = map(int, contest_length.split(":"))
    duration = timedelta(hours=hours, minutes=minutes)
    end_dt = start_dt + duration
    event = {
        "start": {"dateTime": start_dt.isoformat()},
        "end": {"dateTime": end_dt.isoformat()},
        "summary": contest_name,
    }
    service.events().insert(calendarId=calendar_id, body=event).execute()
    if verbose:
        print("Inserted: {}".format(contest_name.strip()))


def add_contests(service, calendar_id, verbose):
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
                verbose,
            )


def delete_next_contests(service, calendar_id, num_contests, verbose):
    now = datetime.utcnow().isoformat() + 'Z' # Z indicates UTC time
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
        if verbose:
            print("Deleted: {}".format(event["summary"].strip()))


def main(argv):
    creds = handle_auth()

    try:
        service = build("calendar", "v3", credentials=creds)
        calendar_id = next(
            x
            for x in service.calendarList().list().execute()["items"]
            if x["summary"] == "Contests"
        )["id"]

        try:
            opts, _ = getopt.getopt(argv, "adv")
        except getopt.GetoptError:
            print("Usage: python3 cal.py [-a][-d][-v]")
            sys.exit(2)
        verbose = ("-v", "") in opts
        if opts and opts[0][0] == "-a":
            print("Adding contests ...")
            add_contests(service, calendar_id, verbose)
        elif opts and opts[0][0] == "-d":
            print("Deleting next 10 contests ...")
            delete_next_contests(service, calendar_id, 10, verbose)
        else:
            print("Updating next 10 contests ...")
            delete_next_contests(service, calendar_id, 10, verbose)
            add_contests(service, calendar_id, verbose)

    except HttpError as error:
        print("An HTTP error occurred: %s" % error)
    except Exception as e:
        print(e)


if __name__ == "__main__":
    main(sys.argv[1:])

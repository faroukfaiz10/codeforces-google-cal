# codeforces-google-cal
This is a script to add codeforces upcoming contests to your Google calendar. Useful for cross referencing with your own schedule to quickly check when you can participate in an event. 

## How to use
### 1. Credentials
The script needs Google credentials to update your Google calendar. [Here](https://developers.google.com/workspace/guides/create-credentials#desktop-app) is a documentation link on how to get them.
Once created, you can download your credentials as json and save them in the project root folder as `credentials.json`.
### 2. Calendar name
Change the variable `CALENDAR_NAME` with the name of your Google calendar.
### 3. Run
First install the required dependecies with `pip3 install -r requirements.txt`.
Then, the script can be ran with the `q` flag to disable logging (quiet mode).
```
Usage: python3 cal.py [-q]
```

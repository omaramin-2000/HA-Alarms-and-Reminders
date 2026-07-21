# custom_components/alarms_and_reminders/sentences/alarm.py
DEFAULT_SENTENCES = {
    "language": "de",
    "intents": {
        "SetAlarm_DE": {
            "data": [
                {
                    "sentences": [
                        "Stell[e] Wecker (auf|um|für) {datetime}",
                        "Weck[e] mich [auf] um {datetime}",
                        "Stelle (den|einen) Wecker (auf|für) {datetime}",
                        "wake me up at {datetime}",
                        "Wecker (auf|um|für) {datetime}"
                    ]
                }
            ]
        },
        "StopAlarm_DE": {
            "data": [
                {
                    "sentences": [
                        "stop[e] [den] Wecken",
                        "[den] Wecker (aus|ausschalten|beenden|deaktivieren|)",
                    ]
                }
            ]
        },
        "SnoozeAlarm_DE": {
            "data": [
                {
                    "sentences": [
                        "[den] Wecker schlummern",
                        "schlummern für {minutes} minuten"
                        "noch {minutes} minuten"
                        "(lass|gib) mir noch {minutes} minuten"
                    ]
                }
            ]
        }
    },
    "lists": {
        "datetime": {
            "type": "text",
            "values": [
                "in {time}",
                "um {time}",
                "{time} am {date}",
                "heute um {time}",
                "morgen um {time}",
                "übermorgen {time}",
                "am {date} um {time}"
            ]
        },
        "time": {
            "type": "text",
            "values": [
                "{hour}:{minute} (morgens|vormittags|am Vormittag)",
                "{hour}:{minute} (nachmittags|abends|am Nachmittag|am Abend)",
                "{hour} {minute} (morgens|vormittags|am Vormittag)",
                "{hour} {minute} (nachmittags|abends|am Nachmittag|am Abend)",
                "{hour} (morgens|vormittags|am Vormittag)",
                "{hour} (nachmittags|abends|am Nachmittag|am Abend)"
            ]
        },
        "hour": {
            "type": "number",
            "range": {
                "from": 1,
                "to": 12
            }
        },
        "minute": {
            "type": "number",
            "range": {
                "from": 0,
                "to": 59,
                "step": 1
            }
        },
        "date": {
            "type": "text",
            "values": [
                "Montag",
                "Dienstag",
                "Mittwoch",
                "Donnerstag",
                "Freitag",
                "Samstag",
                "Sonntag",
                "(nächsten|nächste Woche) Montag",
                "(nächsten|nächste Woche) Dienstag",
                "(nächsten|nächste Woche) Mittwoch",
                "(nächsten|nächste Woche) Donnerstag",
                "(nächsten|nächste Woche) Freitag",
                "(nächsten|nächste Woche) Samstag",
                "(nächsten|nächste Woche) Sonntag",
            ]
        },
        "minutes": {
            "type": "number",
            "range": {
                "from": 1,
                "to": 60
            }
        }
    }
}

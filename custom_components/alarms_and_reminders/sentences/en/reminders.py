DEFAULT_SENTENCES = {
    "language": "en",
    "intents": {
        "SetReminder": {
            "data": [
                {
                    "sentences": [
                        "remind me to {task} at {datetime}",
                        "set a reminder for {task} at {datetime}",
                        "remind me about {task} on {datetime}",
                        "create a reminder for {task} at {datetime}",
                        "set reminder to {task} for {datetime}"
                    ]
                }
            ]
        },
        "StopReminder": {
            "data": [
                {
                    "sentences": [
                        "stop [the] reminder",
                        "turn off [the] reminder",
                        "disable [the] reminder",
                        "cancel [the] reminder",
                        "dismiss [the] reminder"
                    ]
                }
            ]
        },
        "SnoozeReminder": {
            "data": [
                {
                    "sentences": [
                        "snooze [the] reminder",
                        "snooze reminder [for] {minutes} minutes",
                        "remind me again in {minutes} minutes",
                        "postpone [the] reminder [for] {minutes} minutes"
                    ]
                }
            ]
        }
    },
    "lists": {
        # ...existing code for task, datetime, time, etc...
        "minutes": {
            "type": "number",
            "range": [
                {"from": 1, "to": 60}
            ]
        }
    }
}

# custom_components/alarms_and_reminders/sentences/alarm.py
DEFAULT_SENTENCES = {
    "language": "en",
    "intents": {
        "SetAlarm": {
            "data": [
                {
                    "sentences": [
                        "set an alarm for {datetime}",
                        "wake me [up] at {datetime}",
                        "set (the|an) alarm (for|at) {datetime}",
                        "wake me up at {datetime}",
                        "set alarm at {datetime}"
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
                "at {time}",
                "{time} on {date}",
                "today at {time}",
                "tomorrow at {time}",
                "after tomorrow at {time}",
                "on {date} at {time}"
            ]
        },
        "time": {
            "type": "text",
            "values": [
                "{hour}:{minute} AM",
                "{hour}:{minute} PM",
                "{hour} {minute} AM",
                "{hour} {minute} PM",
                "{hour} AM",
                "{hour} PM"
            ]
        },
        "hour": {
            "type": "number",
            "range": [
                {"from": 1, "to": 12}
            ]
        },
        "minute": {
            "type": "number",
            "range": [
                {"from": 0, "to": 59, "step": 1}
            ]
        },
        "date": {
            "type": "text",
            "values": [
                "Monday",
                "Tuesday",
                "Wednesday",
                "Thursday",
                "Friday",
                "Saturday",
                "Sunday",
                "next Monday",
                "next Tuesday",
                "next Wednesday",
                "next Thursday",
                "next Friday",
                "next Saturday",
                "next Sunday"
            ]
        }
    }
}

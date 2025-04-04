# custom_components/alarms_and_reminders/sentences/reminders.py
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
        }
    },
    "lists": {
        "task": {
            "type": "text",
            "values": [
                "take medication",
                "check laundry", 
                "water plants",
                "feed pets",
                "check mail",
                "take out trash",
                "pay bills",
                "{custom_task}"
            ]
        },
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
        },
        "custom_task": {
            "type": "text"
        }
    }
}

# filepath: /ha-alarms-and-reminders/ha-alarms-and-reminders/custom_components/alarms_and_reminders/const.py

DOMAIN = "alarms_and_reminders"
SERVICE_SET_ALARM = "set_alarm"
SERVICE_SET_REMINDER = "set_reminder"

ATTR_DATETIME = "datetime"      # A string containing the reminder time
ATTR_SATELLITE = "satellite"    # The satellite ID to announce the reminder on
ATTR_MESSAGE = "message"        # The announcement message (optional)

DEFAULT_MESSAGE = "Reminder!"    # Default message for reminders
DEFAULT_SATELLITE = "default_satellite"  # Default satellite for announcements
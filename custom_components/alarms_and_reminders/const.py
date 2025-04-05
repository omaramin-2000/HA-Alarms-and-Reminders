# filepath: /ha-alarms-and-reminders/ha-alarms-and-reminders/custom_components/alarms_and_reminders/const.py

"""Constants for the Alarms and Reminders integration."""

DOMAIN = "alarms_and_reminders"

# Services
SERVICE_SET_ALARM = "set_alarm"
SERVICE_SET_REMINDER = "set_reminder"
SERVICE_STOP_ALARM = "stop_alarm"
SERVICE_SNOOZE_ALARM = "snooze_alarm"
SERVICE_STOP_REMINDER = "stop_reminder"
SERVICE_SNOOZE_REMINDER = "snooze_reminder"

# Attributes
ATTR_DATETIME = "datetime"      # A string containing the reminder time
ATTR_SATELLITE = "satellite"    # The satellite ID to announce the reminder on
ATTR_MESSAGE = "message"        # The announcement message (optional)
ATTR_ALARM_ID = "alarm_id"
ATTR_SNOOZE_MINUTES = "minutes"
ATTR_REMINDER_ID = "reminder_id"  # Add this line

# Configuration
CONF_ALARM_SOUND = "alarm_sound"
CONF_REMINDER_SOUND = "reminder_sound"
CONF_MEDIA_PLAYER = "media_player"  # New constant for media player selection

# Defaults
DEFAULT_MESSAGE = "Reminder!"
DEFAULT_SATELLITE = "default_satellite"
DEFAULT_ALARM_SOUND = "/custom_components/alarms_and_reminders/sounds/alarms/birds.mp3"
DEFAULT_REMINDER_SOUND = "/custom_components/alarms_and_reminders/sounds/reminders/ringtone.mp3"
DEFAULT_MEDIA_PLAYER = None  # Default to no media player selected
DEFAULT_SNOOZE_MINUTES = 5
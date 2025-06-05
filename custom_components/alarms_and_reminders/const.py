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
SERVICE_STOP_ALL_ALARMS = "stop_all_alarms"
SERVICE_STOP_ALL_REMINDERS = "stop_all_reminders"
SERVICE_STOP_ALL = "stop_all"
SERVICE_EDIT_ALARM = "edit_alarm"
SERVICE_EDIT_REMINDER = "edit_reminder"
SERVICE_DELETE_ALARM = "delete_alarm"
SERVICE_DELETE_REMINDER = "delete_reminder"
SERVICE_DELETE_ALL_ALARMS = "delete_all_alarms"
SERVICE_DELETE_ALL_REMINDERS = "delete_all_reminders"
SERVICE_DELETE_ALL = "delete_all"

# Attributes
ATTR_DATETIME = "datetime"      # A string containing the reminder time
ATTR_SATELLITE = "satellite"    # The satellite ID to announce the reminder on
ATTR_MESSAGE = "message"        # The announcement message (optional)
ATTR_ALARM_ID = "alarm_id"
ATTR_SNOOZE_MINUTES = "minutes"
ATTR_REMINDER_ID = "reminder_id"  
ATTR_MEDIA_PLAYER = "media_player"
ATTR_NAME = "name"             # Attribute name
ATTR_NOTIFY_DEVICE = "notify_device"
ATTR_NOTIFY_TITLE = "Alarm & Reminder"

# Configuration
CONF_ALARM_SOUND = "alarm_sound"
CONF_REMINDER_SOUND = "reminder_sound"
CONF_MEDIA_PLAYER = "media_player"

# Defaults
DEFAULT_NAME = "Alarms and Reminders"  # Config flow
DEFAULT_MESSAGE = "Reminder!"
DEFAULT_SATELLITE = "default_satellite"
DEFAULT_ALARM_SOUND = "/custom_components/alarms_and_reminders/sounds/alarms/birds.mp3"
DEFAULT_REMINDER_SOUND = "/custom_components/alarms_and_reminders/sounds/reminders/ringtone.mp3"
DEFAULT_MEDIA_PLAYER = None
DEFAULT_SNOOZE_MINUTES = 5 # Default snooze time in minutes
DEFAULT_NOTIFICATION_TITLE = "Alarm & Reminder"

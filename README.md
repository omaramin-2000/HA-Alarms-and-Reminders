# Home Assistant Alarms and Reminders (Beta)

[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://github.com/hacs/integration)
![beta_badge](https://img.shields.io/badge/Status-Beta-orange.svg)

A Home Assistant integration that allows you to set alarms and reminders that will ring on your Home Assistant voice satellites or media players.

> ⚠️ **Beta Status**: This integration is currently in beta and under active development. Features may change and bugs are expected. Please report any issues on the GitHub issue tracker.

## Features

- Set alarms and reminders using voice commands or the dashboard
- Custom sounds for alarms and reminders
- Support for Home Assistant voice satellites
- Optional media player support
- Snooze and stop functionality
- Dashboard controls

## Known Limitations
- Limited error handling
- Basic dashboard controls
- Repeat functionality in development
- Some edge cases not fully tested

## Development Status
This integration is actively being developed. Future updates will include:
- Enhanced repeat functionality
- More robust error handling
- Additional configuration options
- Improved dashboard controls
- Better state management

## Installation

1. Install via HACS:
   - Add this repository as a custom repository in HACS
   - Install the integration
2. Restart Home Assistant
3. Add the integration via the Integrations page

## Configuration

The integration can be configured through the UI:
- Custom sound files for alarms and reminders
- Optional media player selection for non-satellite playback

## Usage

### Voice Commands

Set alarms:
- "Set an alarm for 7 AM"
- "Wake me up at 8:30 tomorrow"

Set reminders:
- "Remind me to take medicine at 2 PM"
- "Set a reminder for meeting at 3:30"

Control:
- "Stop the alarm"
- "Snooze for 5 minutes"
- "Cancel the reminder"

### Services

The integration provides several services:
- `alarms_and_reminders.set_alarm`
- `alarms_and_reminders.set_reminder`
- `alarms_and_reminders.stop_alarm`
- `alarms_and_reminders.snooze_alarm`
- `alarms_and_reminders.stop_reminder`
- `alarms_and_reminders.snooze_reminder`

## Support

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/omaramin-2000/HA-Alarms-and-Reminders/issues).

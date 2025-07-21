# CloudBridge for OpenOffice - Architecture Overview

## Overview

CloudBridge is a client-side OpenOffice extension that integrates cloud storage and collaboration features directly into the OpenOffice desktop environment. The system is entirely local, requiring no server backend, and uses APIs from cloud providers and Slack to perform all remote functions.

## Architecture Diagram (Simplified)

```
         ┌─────────────────────┐
         │   OpenOffice (UNO)  │
         │ ─────────────────── │
         │  - CloudBridge Addon│
         │  - File Event Hooks │
         │  - OAuth Handler    │
         │  - Slack Notifier   │
         └──────┬──────────────┘
                │
     ┌──────────▼────────────┐
     │ Local Token Storage   │
     └──────────┬────────────┘
                │
      ┌─────────▼──────────┐
      │   Cloud API (e.g.  │
      │  Google Drive API) │
      └────────────────────┘
                │
      ┌─────────▼──────────┐
      │ Cloud Storage/File │
      │ (docs + lock files)│
      └────────────────────┘
                │
      ┌─────────▼──────────┐
      │ Slack Webhook URL  │
      └────────────────────┘
```

## Components

### 1. **OpenOffice Extension (Client)**

- Written in Python (via pyUNO)
- Hooks into OpenOffice events (`OnLoad`, `OnSave`, `OnUnload`)
- Manages user UI dialogs and preferences
- Calls remote APIs for cloud access and messaging

### 2. **OAuth 2.0 Flow**

- Opens local browser for user login
- Receives redirect at localhost with access/refresh tokens
- Tokens securely stored on user machine
- Automatically refreshes access token as needed

### 3. **Cloud Storage API Integration**

- Google Drive API / Dropbox API
- File operations: list, download, upload, metadata
- Creates and deletes `.lock` file on cloud

### 4. **Lock File Mechanism**

- JSON structure stored as sidecar file: `filename.odt.lock`

```json
{
  "user": "Alice",
  "timestamp": "2025-07-21T15:03:00Z",
  "machine": "alice-laptop"
}
```

- Checked on open, deleted on save/close
- Shown in warning dialog if present

### 5. **Slack Notification Integration**

- User provides Webhook URL
- Plugin POSTs messages on file events:
  - 🔒 Started editing
  - 💾 Saved changes
  - ✅ Finished editing

## File/Folder Structure

```
cloudbridge-extension/
├── META-INF/manifest.xml
├── python/CloudBridge.py
├── dialogs/PreferencesDialog.xdl
├── config/cloudbridge_config.json
├── Addons.xcu
├── description.xml
├── LICENSE.txt
└── README.md
```

## Local Storage Responsibilities

- OAuth tokens and Slack config saved in a local config file
- Logging (optional) to local log file for debugging and status

## External Services Used

- **Google Drive** or **Dropbox** (REST APIs)
- **Slack** (Incoming Webhook endpoint)

## Security Notes

- No backend server involved
- All credentials and tokens stored locally
- HTTPS used for all API calls

## Extensibility

- Can be extended to support OneDrive, Box
- Can integrate with Zapier, Trello, or Notion in future


# CloudBridge for OpenOffice - Refined Architectural Plan

## 1. Executive Summary

CloudBridge is a client-side OpenOffice extension that integrates cloud storage (Google Drive, Dropbox) and collaborative awareness features directly into the OpenOffice desktop suite. It is designed to prevent data loss from conflicting edits while improving team workflow.

This architecture is built on three core principles:
1.  **Security First**: User credentials and tokens are never stored in plaintext. All secrets are managed via the native operating system's credential manager.
2.  **Data Integrity**: A two-layered defense system using both advisory lock files and atomic `revisionId` checks provides a robust guarantee against accidental overwrites and data loss.
3.  **Native Integration**: The extension will feel like a native part of OpenOffice, using the UNO (Universal Network Objects) API for all core interactions, including menus, dialogs, and document event handling.

**Scope Note**: Due to its unique architecture of managing external database connections, OpenOffice Base (`.odb` files) is considered out of scope for the initial version of this extension. CloudBridge is designed for self-contained document types like Writer, Calc, Impress, Draw, and Math.

## 2. Core Components & Workflow

### 2.1. Two-Layered Defense System for Collaboration

To solve the challenge of concurrent editing, we will use two distinct mechanisms that work together.

#### Layer 1: The Advisory Lock File (The "Social" Warning)
- **Purpose**: To provide a real-time, friendly warning that a user is actively editing a file. It discourages users from starting work simultaneously.
- **Mechanism**:
    - On file open, the extension attempts to **atomically create** a sidecar lock file (e.g., `document.odt.lock`) on the cloud drive.
    - Cloud APIs (like Google Drive's) handle this atomically. If the file exists, the creation call fails with a `409 Conflict` error, preventing duplicate `(1)` files.
    - **Success (Lock Acquired)**: The user's session begins.
    - **Failure (Lock Exists)**: The user is immediately warned that another specific user is editing the file.
- **Answers the Question**: "Is anyone working on this *right now*?"

#### Layer 2: The `revisionId` Check (The "Technical" Guarantee)
- **Purpose**: To provide an unbreakable guarantee against the "lost update" problem, where one user's save accidentally overwrites another's.
- **Mechanism**:
    - On file download, the extension stores the file's unique `revisionId` (provided by the cloud API) in memory, associated with the open document.
    - Before uploading a saved version, the extension fetches the latest `revisionId` from the server.
    - **IDs Match**: The file has not been changed by anyone else. The upload proceeds safely.
    - **IDs Mismatch**: A conflict exists. The user is prompted with a clear dialog to:
        1.  **Overwrite** the server version.
        2.  **Save their changes as a new copy** (e.g., `document (conflict copy).odt`).
        3.  **Cancel** the save to manually review the changes.
- **Answers the Question**: "Has *anything* changed on the server since I opened this?"

### 2.2. Secure OAuth 2.0 Authentication Flow

- **Trigger**: Authentication is "on-demand." It is triggered the first time a user attempts a cloud action.
- **Process**:
    1.  The extension checks the OS keychain for a valid access token. If a refresh token exists, it is used silently to get a new access token.
    2.  If no valid tokens exist, the full OAuth flow begins.
    3.  A temporary local web server is started on `127.0.0.1`.
    4.  The user's default browser is opened to the official cloud provider's login and consent screen. The extension **never** sees the user's password.
    5.  Upon success, the provider redirects the browser to the local server's URL, passing an `authorization_code`.
    6.  The local server captures the code and immediately shuts down.
    7.  The extension exchanges the code for a long-lived `refresh_token` and a short-lived `access_token`.
    8.  Both tokens are stored securely in the **native OS credential manager** (e.g., macOS Keychain, Windows Credential Manager) using a cross-platform library like `keyring`. **No credentials will be stored in plaintext files.**

## 3. OpenOffice UNO API Integration Strategy

We will interact with the OpenOffice application exclusively through its Python-UNO bridge.

### 3.1. File Representation
- All documents, even local temporary ones, are handled via `file:///` URLs.
- The master `com.sun.star.frame.Desktop` service is our entry point for loading all documents via its `loadComponentFromURL()` method.

### 3.2. Document Lifecycle Management
The `document` component returned by the API is our handle. We interact with it through its specific interfaces:

- **`XModel`**: Used to attach our custom `XDocumentEventListener`. This allows our code to be notified of `OnSave` and `OnClose` events for cloud-managed documents specifically.
- **`XStorable`**: Used to control persistence. When our `OnSave` listener fires, we will use `storeToURL()` to save the document's current state to its local temporary file. Our code then reads this local file and handles the cloud upload. This decouples the OpenOffice save action from our network operations.
- **`XModifiable`**: Used to check the `isModified()` flag (the "dirty" state) to provide better UX, such as warning the user before closing a document with unsaved changes.

### 3.2.1. Handling the "Save As" Edge Case (State Desynchronization)
A critical edge case is when a user opens a document from the cloud and then uses `File > Save As...` to save it to a new, permanent location on their local disk. This action desynchronizes the plugin's state and must be handled gracefully to prevent accidental cloud overwrites.

- **Listen for Detachment**: Our `XDocumentEventListener` will be extended to listen for the `OnSaveAsDone` event, in addition to `OnSave` and `OnClose`.
- **Sever the Cloud Link**: When the `OnSaveAsDone` event fires, our handler will:
    1.  Check the document's new location via its `XStorable` interface.
    2.  If the new location is different from our temporary file path, we declare the document "detached" from its cloud session.
    3.  We immediately sever the link by removing the document from our internal tracking (deleting its `revisionId`) and programmatically detaching our event listener from its `XModel`.
    4.  A non-blocking notification will inform the user that the document is now a local copy and no longer connected to the cloud.
- **Preserve the Cloud Lock**: The original `.lock` file on the cloud server will **not** be deleted in this scenario. This correctly signals that the cloud document's editing session was abandoned, not properly completed, and prevents others from assuming the file is safe to edit.

### 3.3. UI and User Interaction
- **Menus**: A custom "CloudBridge" menu will be added to the OpenOffice UI via an `Addons.xcu` configuration file. Menu actions trigger specific command URLs.
- **Dispatch Provider**: Our code will implement a `XDispatchProvider` to listen for our custom command URLs and execute the corresponding Python functions (e.g., for `Open from Cloud...`).
- **Dialogs**: All custom UI (file browser, preferences, conflict warnings) will be designed in `.xdl` files and controlled via the `XDialog` service and its associated control listeners.

## 4. Modular Code Structure

To ensure maintainability, the project will follow a modular structure within the extension package. A monolithic `.py` file is explicitly forbidden.

```
python/
└── cloudbridge/
    ├── main.py             # Entry point, dispatch provider, and event listener setup
    ├── ui/                 # UI dialog management and handlers
    │   ├── preferences_dialog.py
    │   └── file_browser_dialog.py
    ├── auth/               # OAuth flow and secure token storage (using keyring)
    │   └── oauth_handler.py
    ├── cloud/
    │   ├── base_provider.py  # Abstract class for all cloud services
    │   ├── drive_provider.py # Google Drive implementation
    │   └── dropbox_provider.py # Dropbox implementation
    ├── collaboration/
    │   ├── locking.py        # Logic for creating and checking lock files
    │   └── versioning.py     # Logic for handling revisionId checks
    └── config.py           # Manages non-sensitive configuration
``` 
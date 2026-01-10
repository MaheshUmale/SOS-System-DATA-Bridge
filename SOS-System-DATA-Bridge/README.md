# SOS-System-DATA-Bridge

## Running Locally (as a Server)

To run the Data Bridge locally, follow these steps:

1.  **Set up a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```
2.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
3.  **Run the application:**
    ```bash
    python3 tv_data_bridge.py
    ```
    The Data Bridge will start a WebSocket server and listen for incoming connections on `ws://localhost:8765`.

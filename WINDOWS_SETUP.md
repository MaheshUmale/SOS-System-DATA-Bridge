# Running the SOS Integration Project on Windows

This guide provides step-by-step instructions for setting up and running the SOS (Scalping Orchestration System) integration project on a Windows laptop. You can run the project using Docker (recommended for a consistent environment) or locally on your machine.

## Running with Docker (Recommended)

... (existing Docker instructions) ...

## Running Locally (Without Docker)

This section provides instructions for running the Data Bridge and Core Engine directly on your Windows machine.

### Prerequisites

*   **Python 3.10:** You will need Python 3.10 installed. You can download it from the [official Python website](https://www.python.org/downloads/).
*   **Java 11:** You will need the Java Development Kit (JDK) version 11. You can download it from [Oracle](https://www.oracle.com/java/technologies/javase-jdk11-downloads.html) or use an open-source distribution like [Eclipse Temurin](https://adoptium.net/).
*   **Apache Maven:** You will need Apache Maven to build the Core Engine. You can download it from the [official Maven website](https://maven.apache.org/download.cgi).
*   **Git:** You will need Git to clone the project repositories. You can download it from the [official Git website](https://git-scm.com/downloads).
*   **A text editor or IDE:** You will need a text editor or an Integrated Development Environment (IDE) to edit configuration files. [Visual Studio Code](https://code.visualstudio.com/) is a good free option.

### Step 1: Clone the Repositories

First, you need to create a new directory for the project and then clone the `SOS-System-DATA-Bridge` and `Scalping-Orchestration-System-SOS-` repositories into it as sibling directories.

1.  Open a new terminal or PowerShell window.
2.  Create a new directory for the project and navigate into it:
    ```bash
    mkdir sos-integration
    cd sos-integration
    ```
3.  Clone the `SOS-System-DATA-Bridge` repository:
    ```bash
    git clone https://github.com/MaheshUmale/SOS-System-DATA-Bridge.git
    ```
4.  Clone the `Scalping-Orchestration-System-SOS-` repository:
    ```bash
    git clone https://github.com/MaheshUmale/Scalping-Orchestration-System-SOS-.git
    ```

### Step 2: Configure the Upstox API Key

The Data Bridge requires an Upstox API key to fetch market data.

1.  Navigate to the `SOS-System-DATA-Bridge` directory.
2.  Create a new file named `config.py`.
3.  Open the `config.py` file in your text editor and add the following line, replacing `"YOUR_ACCESS_TOKEN"` with your actual Upstox API access token:
    ```python
    ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
    ```

### Step 3: Run the Core Engine

1.  Open a new terminal or PowerShell window and navigate to the `Scalping-Orchestration-System-SOS-` directory.
2.  Build the project using Maven:
    ```bash
    mvn clean package
    ```
3.  Run the Core Engine application:
    ```bash
    java -jar sos-engine/target/sos-engine-1.0-SNAPSHOT.jar
    ```
    The Core Engine will start and begin listening for WebSocket connections on port 8765.

### Step 4: Run the Data Bridge

1.  Open a new terminal or PowerShell window and navigate to the `SOS-System-DATA-Bridge` directory.
2.  Install the required Python dependencies:
    ```bash
    pip install -r requirements.txt
    ```
3.  Run the Data Bridge script:
    ```bash
    python tv_data_bridge.py
    ```
    The Data Bridge will start, connect to the Core Engine, and begin sending data.

### Step 5: Verify the Integration

You can monitor the output of the two terminals to verify that the integration is working correctly.

*   The Core Engine terminal should show that it is receiving and processing messages from the Data Bridge.
*   The Data Bridge terminal should show that it is fetching data from the Upstox API and sending it to the Core Engine.

That's it! You should now have the SOS integration project up and running on your Windows laptop without Docker.

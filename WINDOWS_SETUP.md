# Running the SOS Integration Project on Windows

This guide provides step-by-step instructions for setting up and running the SOS (Scalping Orchestration System) integration project on a Windows laptop. The project is containerized using Docker, so you will need to have Docker Desktop installed.

## Prerequisites

*   **Windows 10 or 11:** This guide is written for modern versions of Windows.
*   **Docker Desktop:** You must have Docker Desktop for Windows installed and running. You can download it from the [official Docker website](https://www.docker.com/products/docker-desktop/).
*   **Git:** You will need Git to clone the project repositories. You can download it from the [official Git website](https://git-scm.com/downloads).
*   **A text editor or IDE:** You will need a text editor or an Integrated Development Environment (IDE) to edit configuration files. [Visual Studio Code](https://code.visualstudio.com/) is a good free option.

## Step 1: Clone the Repositories

First, you need to clone both the `SOS-System-DATA-Bridge` and `Scalping-Orchestration-System-SOS-` repositories from GitHub.

1.  Open a new terminal or PowerShell window.
2.  Navigate to the directory where you want to store the project.
3.  Clone the `SOS-System-DATA-Bridge` repository:
    ```bash
    git clone https://github.com/MaheshUmale/SOS-System-DATA-Bridge.git
    ```
4.  Clone the `Scalping-Orchestration-System-SOS-` repository:
    ```bash
    git clone https://github.com/MaheshUmale/Scalping-Orchestration-System-SOS-.git
    ```

## Step 2: Configure the Upstox API Key

The Data Bridge requires an Upstox API key to fetch market data.

1.  Navigate to the `SOS-System-DATA-Bridge` directory.
2.  Create a new file named `config.py`.
3.  Open the `config.py` file in your text editor and add the following line, replacing `"YOUR_ACCESS_TOKEN"` with your actual Upstox API access token:
    ```python
    ACCESS_TOKEN = "YOUR_ACCESS_TOKEN"
    ```

## Step 3: Build and Run the Containers

The project is orchestrated using `docker-compose`.

1.  Make sure Docker Desktop is running.
2.  Open a terminal or PowerShell window in the `SOS-System-DATA-Bridge` directory.
3.  Run the following command to build the Docker images and start the containers:
    ```bash
    docker compose up --build
    ```
    This command will:
    *   Build the Docker image for the `data-bridge` service.
    *   Build the Docker image for the `core-engine` service.
    *   Start both containers and connect them to a shared network.

## Step 4: Verify the Integration

You can monitor the logs of the two services to verify that the integration is working correctly.

1.  Open a new terminal or PowerShell window.
2.  To view the logs of the `data-bridge`, run:
    ```bash
    docker logs data-bridge
    ```
    You should see output indicating that the Data Bridge is fetching data from the Upstox API and sending it to the Core Engine.
3.  To view the logs of the `core-engine`, run:
    ```bash
    docker logs core-engine
    ```
    You should see output indicating that the Core Engine is receiving and processing messages from the Data Bridge.

## Troubleshooting

*   **`docker compose` command not found:** If you get an error that the `docker compose` command is not found, you may have an older version of Docker. Try using `docker-compose` (with a hyphen) instead.
*   **Permission errors:** If you encounter permission errors when running `docker` commands, you may need to run your terminal or PowerShell as an administrator.
*   **Build failures:** If the Docker images fail to build, check the output for any error messages. The most common issues are related to network connectivity or missing dependencies.

That's it! You should now have the SOS integration project up and running on your Windows laptop.

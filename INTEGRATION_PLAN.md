# Integration Plan: Data Bridge and Core Engine

## Introduction

This document outlines the step-by-step plan for integrating the Python-based **Data Bridge (Module A)** with the Java-based **Core Engine (Module B)**. The goal is to create a robust, end-to-end system where the Core Engine can successfully receive and process all specified data types from the Data Bridge via a WebSocket connection.

This is a forward-looking plan intended to guide a developer through the integration process.

---

## Phase 0: Project Kick-off & Alignment

**Goal:** Ensure all stakeholders are aligned and have a shared understanding of the project scope and technical requirements.

**A. Technical Checklist:**
*   [ ] **Review `Contract.md`:** The development team for the Core Engine must thoroughly review the [Data Bridge Contract](https://github.com/MaheshUmale/SOS-System-DATA-Bridge/blob/main/Contract.md) to understand the WebSocket interface, message types (`CANDLE_UPDATE`, `SENTIMENT_UPDATE`, etc.), and data structures.
*   [ ] **Dependency Review:**
    *   Confirm all Python dependencies listed in `requirements.txt` for the Data Bridge.
    *   Confirm all Java dependencies listed in the `pom.xml` for the Core Engine.

**B. Collaboration & Communication:**
*   **Communication Channel:** Establish a dedicated Slack/Teams channel (e.g., `#sos-integration`) for real-time communication.
*   **Point of Contact (PoC):**
    *   **Data Bridge (Module A):** @MaheshUmale
    *   **Core Engine (Module B):** @MaheshUmale
*   **Definition of Done:**
    *   **End-to-End Test Suite:** A comprehensive integration test suite is created and all tests are passing.
    *   **Successful Data Exchange:** The Core Engine can successfully receive and deserialize all message types (`CANDLE_UPDATE`, `SENTIMENT_UPDATE`, `MARKET_UPDATE`, `OPTION_CHAIN_UPDATE`) from the Data Bridge.
    *   **Documentation:** A `RUNBOOK.md` is created with clear instructions for setting up and running the integrated system.
    *   **Code Review:** The implementation has been peer-reviewed and approved.

---

## Phase 1: Environment Setup & Interface Definition Review

**Goal:** Prepare the local development environment and verify basic connectivity between the two modules.

**A. Technical Checklist:**
*   [ ] **Clone Repositories:** Set up a workspace with both repositories cloned as sibling directories.
    ```bash
    mkdir sos-workspace
    cd sos-workspace
    git clone https://github.com/MaheshUmale/SOS-System-DATA-Bridge.git
    git clone https://github.com/MaheshUmale/Scalping-Orchestration-System-SOS-.git
    ```
*   [ ] **Install Data Bridge Dependencies:**
    ```bash
    cd SOS-System-DATA-Bridge
    pip install -r requirements.txt
    ```
*   [ ] **Install Core Engine Dependencies:**
    ```bash
    cd ../Scalping-Orchestration-System-SOS-/sos-engine
    mvn clean install
    ```
*   [ ] **Create Unified Database:** The Data Bridge requires a SQLite database. Create it by running the following from the `SOS-System-DATA-Bridge` root:
    ```bash
    python3 create_unified_db.py
    ```
*   [ ] **Initial Connectivity Test:**
    1.  Start the Data Bridge server from the `SOS-System-DATA-Bridge` root: `python3 tv_data_bridge.py`.
    2.  Create a temporary Java test file in the Core Engine (`src/test/java/.../ConnectionTest.java`) to act as a simple WebSocket client.
    3.  Run this test to confirm a successful WebSocket connection to `ws://localhost:8765`. This verifies the environment is correctly configured.

---

## Phase 2: Development & Iterative Testing (Sandbox)

**Goal:** Implement the data handling logic in the Core Engine and create a robust integration test suite.

**A. Technical Checklist:**
*   [ ] **Create Java Data Models (POJOs):** In the Core Engine, create a new package `com.trading.hf.model`. Inside, define Java classes that map directly to the JSON structures in `Contract.md`:
    *   `BaseMessage.java` (with `type`, `timestamp`, and `data` fields)
    *   `Candle.java`
    *   `CandleUpdate.java`
    *   `SentimentUpdate.java`
    *   `MarketUpdate.java`
    *   `OptionChainUpdate.java`
*   [ ] **Implement Deserialization Logic:**
    *   Modify the `onMessage` method in `TVMarketDataStreamer.java`.
    *   Use the Jackson `ObjectMapper` to deserialize the incoming JSON string first into `BaseMessage.java`.
    *   Based on the `type` field, deserialize the `data` node into the corresponding specific class (e.g., `CandleUpdate`).
*   [ ] **Develop Integration Test Suite:**
    *   Create a permanent integration test file: `src/test/java/com/trading/hf/IntegrationTest.java`.
    *   This test should:
        1.  Programmatically start the Python Data Bridge as a background process.
        2.  Connect the Core Engine's WebSocket client.
        3.  Use `CountDownLatch` or a similar mechanism to wait for and verify that at least one of each message type (`CANDLE_UPDATE`, `SENTIMENT_UPDATE`, `MARKET_UPDATE`, `OPTION_CHAIN_UPDATE`) is received.
        4.  Ensure the Data Bridge process is terminated and the port is freed in a `tearDown` method.

---

## Phase 3: UAT (User Acceptance Testing) & Staging Deployment

**Goal:** Validate the integrated system in a production-like environment.

**A. Technical Checklist:**
*   [ ] **Prepare Runbook:** Create a `RUNBOOK.md` with clear, concise instructions on how to run the fully integrated system.
*   [ ] **Deploy to Staging:** Deploy both modules to a staging environment.
*   [ ] **Execute UAT Plan:** Run a predefined set of tests using anonymized production data to ensure the system behaves as expected under real-world conditions.
*   [ ] **Performance and Load Testing:**
    *   Develop a test script to simulate a high volume of WebSocket messages.
    *   Measure the end-to-end latency from the Data Bridge to the Core Engine.
    *   Monitor CPU and memory usage under load to identify any performance bottlenecks.
*   [ ] **Sign-off:** Obtain formal approval from all stakeholders before proceeding.

---

## Phase 4: Go-Live & Post-Deployment Monitoring

**Goal:** Deploy the system to production and monitor its performance.

**A. Technical Checklist:**
*   [ ] **Production Deployment:** Follow the deployment plan to release the integrated system.
*   [ ] **Monitoring:** Set up dashboards and alerts to monitor key metrics:
    *   WebSocket connection stability.
    *   Message latency.
    *   CPU and memory usage of both modules.

**B. Risk & Rollback Plan:**
*   **Identified Risks:**
    *   **Schema Drift:** The Python bridge might change its data format. Mitigation: Implement versioning in the API contract.
    *   **Latency:** Network issues could delay message delivery. Mitigation: Add timestamps to messages to monitor and alert on high latency.
*   **Rollback Procedure:** In case of critical failure, the previous standalone versions of the modules will be redeployed. A post-mortem will be conducted to analyze the root cause.

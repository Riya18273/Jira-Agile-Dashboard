# 🤖 Agile AI Agent: Technical Documentation

## 1. Project Overview
The **Agile AI Agent** is a high-fidelity data extraction, processing, and visualization engine designed to transform raw Jira ticket data into strategic business intelligence. It empowers CXOs, Product Owners, and Engineering Managers with actionable insights into team velocity, backlog health, and sprint efficiency.

Unlike standard Jira reports, this solution builds a **persistent data layer** in Excel, allowing for historical trend analysis, complex cross-project aggregation, and offline access.

## 2. High-Level Architecture
The system follows a modular "Extract-Load-Visualize" pipeline, augmented by an autonomous "Ritual Automation" layer.

```mermaid
graph TD
    %% Nodes
    subgraph Integrated_Sources
        Jira[(Jira Cloud / Server)]
        Outlook[Outlook Calendar/Email]
        Teams[Microsoft Teams]
    end

    subgraph Core_Agent [Agile AI Agent Core]
        Orchestrator[Agent Orchestrator<br/>(agent.py)]
        
        subgraph Extraction_Engine [Extraction Engine]
            Epics[Epic Extractor]
            Sprints[Sprint Extractor]
            Issues[Issue Extractor]
            Worklogs[Worklog Extractor]
            History[Transition History]
        end
        
        Discovery[Field Discovery<br/>(field_discovery.py)]
    end

    subgraph Data_Layer [Data Persistence]
        ExcelDB[(Master Data Model<br/>.xlsx)]
    end

    subgraph Presentation_Layer [Visualization & Interface]
        Dashboard[Streamlit Dashboard<br/>(dashboard_app.py)]
        PowerBI[Power BI Reports]
    end
    
    subgraph Automation_Layer [Ritual Automation]
        StandupBot[Standup Bot<br/>(Daily_standup.py)]
    end

    %% Edge Connections
    Jira -->|Rest API| Orchestrator
    Discovery -->|Field ID Mapping| Orchestrator
    Orchestrator --> Epics & Sprints & Issues & Worklogs & History
    
    Epics & Sprints & Issues & Worklogs & History -->|Pandas DataFrames| ExcelDB
    
    ExcelDB -->|Read Data| Dashboard
    ExcelDB -->|Import| PowerBI
    
    Outlook -->|Calendar Events| StandupBot
    StandupBot -->|Post Summary| Teams
    StandupBot -->|Read Blocker Status| ExcelDB

    %% Styles
    style Core_Agent fill:#f9f,stroke:#333,stroke-width:2px
    style Data_Layer fill:#ccf,stroke:#333,stroke-width:2px
    style Presentation_Layer fill:#cfc,stroke:#333,stroke-width:2px
```

## 3. Core Components

### 3.1. Extraction Engine (`agent.py`)
The heart of the system is the `JiraConnectorAgent` class. It orchestrates specialized extractor modules to pull specific data domains.
- **Incremental Extraction**: Tracks the `Updated` timestamp of issues to only fetch changed data since the last run, significantly reducing execution time.
- **Resilience**: Features automatic session management and error handling for API timeouts.

### 3.2. Intelligent Field Discovery (`field_discovery.py`)
Hardcoding field IDs (e.g., `customfield_10002` for Story Points) is ensuring failure in different Jira environments. The Agent solves this by:
1.  Scanning the Jira `/field` API endpoint.
2.  Fuzzy matching names like "Story Points", "Sprint", "Epic Link".
3.  Dynamically mapping these IDs at runtime.

### 3.3. Master Data Model (`ExcelManager`)
Data is normalized and stored in a multi-sheet Excel file (`*.xlsx`), acting as a lightweight data warehouse.
- **Sheets**: `Epic Summary`, `Sprint Summary`, `Issue Summary`, `Worklog Summary`, `Transition History`.
- **Normalization**: Flattens nested JSON structures (extracting sprint names from arrays, etc.).

### 3.4. Analytical Dashboard (`dashboard_app.py`)
A Streamlit-based web application providing real-time insights.
- **Executive Summary**: High-level KPIs like Resolution Rate, SLA Breaches, and Cost Analysis.
- **Agent Performance**: Drill-down into individual contributor metrics and worklog accuracy.
- **Trend Analysis**: Visualizing velocity and ticket volume over time.

### 3.5. Ritual Automation
- **Standup Bot**: Monitors Outlook for "Daily Standup" events. When the meeting starts, it triggers a workflow to collect updates and post a consolidated summary to Microsoft Teams.

## 4. Key Features

| Feature | Description | Business Value |
| :--- | :--- | :--- |
| **Cycle Time Engine** | Calculates the exact time an issue spent in every status (e.g., "In Progress", "Review"). | Identifies process bottlenecks (e.g., "Code Review is taking 3 days avg"). |
| **Backlog Health** | Scans for tickets untouched for >3 months or without Story Points. | Prevents backlog rot and ensures "Definition of Ready". |
| **Scope Creep Tracker** | Identifies issues added to a Sprint *after* the start date. | Protects team velocity commitments and highlights planning gaps. |
| **SLA Monitor** | Tracks "Time to First Response" and "Time to Resolution" against targets. | Critical for Service Desk teams to maintain contract compliance. |

## 5. Usage Guide

### 5.1. Setup
1.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```
2.  **Configuration**:
    Create a `.env` file with your credentials:
    ```env
    JIRA_URL=https://your-domain.atlassian.net
    JIRA_EMAIL=your-email@company.com
    JIRA_API_TOKEN=your-api-token
    ```

### 5.2. Running the Extraction
To run a full refresh of the data:
```bash
python agent.py --project M5R --force
```
*Use `--force` to rebuild the entire dataset, or omit it for an incremental update.*

### 5.3. Launching the Dashboard
```bash
streamlit run dashboard_app.py
```
Access the dashboard in your browser at `http://localhost:8501`.

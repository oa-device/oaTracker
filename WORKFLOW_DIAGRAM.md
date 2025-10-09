# oaTracker Workflow Diagram

## Overview

Real-time human detection and tracking service using YOLO models with multi-source input handling and comprehensive API endpoints for macOS and Ubuntu deployment.

## ML Pipeline Architecture

```mermaid
flowchart TD
    %% Input Sources
    USB[USB Camera\nDevice Index 0-9] --> InputMux
    RTSP[RTSP Stream\nrtsp://user:pass@ip:port] --> InputMux
    FILE[Video File\n/path/to/video.mp4] --> InputMux
    CAMBRIDGE[oaCamBridge\nMJPEG Stream / Frame Dir] --> InputMux

    %% Input Processing
    InputMux[Input Multiplexer\nSource Detection] --> FrameCapture
    FrameCapture[Frame Capture Thread\nAsync Processing] --> FrameBuffer

    %% ML Pipeline
    FrameBuffer[Frame Buffer\nCaching] --> Preprocessor
    Preprocessor[Image Preprocessing\nResize / Normalize] --> YOLOEngine
    YOLOEngine[YOLO Detection Engine\nMulti-Class Support] --> PersonFilter

    %% Object Filtering
    PersonFilter[Person Class Filter\nClass: 0] --> DetectionResults
    DetectionResults[Detection Results\nBounding Boxes + Confidence] --> Tracker

    %% Object Tracking
    Tracker[Object Tracker\nSORT/BOT-SORT] --> TrackManager
    TrackManager[Track Manager\nTrack ID Assignment] --> TemporalAnalysis

    %% Temporal Analysis
    TemporalAnalysis[Temporal Analysis\nTrack History] --> CountingLogic
    CountingLogic[Counting Logic\nUnique Person Count] --> StatisticsEngine

    %% Statistics
    StatisticsEngine[Statistics Engine\nFPS / Uptime / Counts] --> DataStore
    DataStore[In-Memory Data Store\nTrack History + Stats] --> API

    %% API Layer
    API[FastAPI Server\nPort 8080] --> Endpoints
    Endpoints[REST Endpoints\nJSON + MJPEG] --> Clients

    %% Styling
    classDef source fill:#1f2937,stroke:#f8fafc,stroke-width:2px,color:#f8fafc
    classDef processing fill:#1e293b,stroke:#f1f5f9,stroke-width:2px,color:#f1f5f9
    classDef ml fill:#f59e0b,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef tracking fill:#3b82f6,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef api fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#1f2937

    class USB,RTSP,FILE,CAMBRIDGE source
    class InputMux,FrameCapture,FrameBuffer,Preprocessor processing
    class YOLOEngine,PersonFilter,DetectionResults ml
    class Tracker,TrackManager,TemporalAnalysis,CountingLogic tracking
    class StatisticsEngine,DataStore,API,Endpoints api
```

## Object Tracking Workflow

```mermaid
stateDiagram-v2
    [*] --> Initialize
    Initialize --> LoadModel: Load YOLO Model
    LoadModel --> StartCamera: Initialize Camera
    StartCamera --> CaptureFrame: Capture Frame

    state ProcessingLoop {
        [*] --> FrameReady
        FrameReady --> DetectObjects: Run YOLO Detection
        DetectObjects --> FilterPersons: Filter Class 0
        FilterPersons --> UpdateTracks: Update Object Tracks
        UpdateTracks --> CalculateStats: Calculate Statistics
        CalculateStats --> StoreData: Store in Memory
        StoreData --> FrameReady: Next Frame
    }

    StartCamera --> ProcessingLoop

    state APIRequests {
        [*] --> HealthCheck
        HealthCheck --> GetStats: /api/stats
        GetStats --> GetDetections: /api/detections
        GetDetections --> GetObjects: /api/tracked_objects
        GetObjects --> VideoStream: /video_feed
        VideoStream --> [*]
    }

    ProcessingLoop --> APIRequests: Data Available
    APIRequests --> ProcessingLoop: Request Handled

    ProcessingLoop --> Shutdown: Service Stop
    Shutdown --> [*]
```

## Multi-Source Input Handling

```mermaid
flowchart LR
    subgraph InputSources [Input Sources]
        USB0[USB Camera 0\n/dev/video0]
        USB1[USB Camera 1\n/dev/video1]
        RTSP1[RTSP Stream 1\nrtsp://ip:8554/stream1]
        RTSP2[RTSP Stream 2\nrtsp://ip:8554/stream2]
        VIDEO[Video File\n/video.mp4]
        CAM_HTTP[oaCamBridge HTTP\nhttp://localhost:8086/stream]
        CAM_DIR[oaCamBridge Frames\n/tmp/webcam/*.jpg]
    end

    subgraph InputProcessingLayer [Input Processing Layer]
        Config[Config Parser\nconfig.yaml] --> SourceRouter
        SourceRouter[Source Router\nAuto-Detection] --> FormatAdapter
        FormatAdapter[Format Adapter\nCV2/URL/File] --> Validation
        Validation[Input Validation\nResolution/FPS] --> FrameCapture
    end

    subgraph FrameProcessingPipeline [Frame Processing Pipeline]
        FrameCapture[Frame Capture\nAsync Threading] --> Preprocess
        Preprocess[Preprocessing\nResize 640x640] --> Normalize
        Normalize[Normalization\n0-1 Range] --> BatchReady
        BatchReady[Batch Ready\nInference Queue] --> YOLO
    end

    InputSources --> InputProcessing
    InputProcessing --> FramePipeline

    classDef source fill:#1f2937,stroke:#f8fafc,stroke-width:2px,color:#f8fafc
    classDef processing fill:#1e293b,stroke:#f1f5f9,stroke-width:2px,color:#f1f5f9
    classDef pipeline fill:#f59e0b,stroke:#1f2937,stroke-width:2px,color:#1f2937

    class USB0,USB1,RTSP1,RTSP2,VIDEO,CAM_HTTP,CAM_DIR source
    class Config,SourceRouter,FormatAdapter,Validation processing
    class FrameCapture,Preprocess,Normalize,BatchReady,YOLO pipeline
```

## API Endpoint Architecture

```mermaid
flowchart TD
    subgraph FastAPIServerLayer [FastAPI Server Layer]
        Server[FastAPI Instance\nPort 8080] --> Middleware
        Middleware[CORS + Logging\nMiddleware] --> Router
        Router[API Router] --> Endpoints
    end

    subgraph APIEndpointsStructure [API Endpoints Structure]
        Health[GET /health\nService Status] --> HealthLogic
        Stats[GET /api/stats\nDetection Statistics] --> StatsLogic
        Detections[GET /api/detections\nCount by Time Window] --> DetectionLogic
        Objects[GET /api/tracked_objects\nAll Current Objects] --> ObjectsLogic
        Camera[GET /api/camera/status\nCamera Hardware Info] --> CameraLogic
        Video[GET /video_feed\nMJPEG Stream] --> VideoLogic
    end

    subgraph BusinessLogic [Business Logic Layer]
        HealthLogic[Health Checker\nCamera/Model Status] --> HealthResponse
        StatsLogic[Statistics Engine\nFPS/Uptime/Counts] --> StatsResponse
        DetectionLogic[Count Calculator\nTime Window Logic] --> DetectionResponse
        ObjectsLogic[Track Manager\nCurrent Track Data] --> ObjectsResponse
        CameraLogic[Hardware Monitor\nResolution/FPS] --> CameraResponse
        VideoLogic[Frame Streamer\nMJPEG Encoding] --> VideoResponse
    end

    subgraph DataLayer [Data Access Layer]
        DataStore[In-Memory Store\nTrack History] --> StatsLogic
        DataStore --> DetectionLogic
        DataStore --> ObjectsLogic
        Hardware[Hardware Interface\nCV2 Camera] --> CameraLogic
        Hardware --> VideoLogic
    end

    APILayer --> Endpoints
    Endpoints --> BusinessLogic
    BusinessLogic --> DataLayer

    classDef api fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef endpoint fill:#3b82f6,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef logic fill:#f59e0b,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef data fill:#1e293b,stroke:#f1f5f9,stroke-width:2px,color:#f1f5f9

    class Server,Middleware,Router api
    class Health,Stats,Detections,Objects,Camera,Video endpoint
    class HealthLogic,StatsLogic,DetectionLogic,ObjectsLogic,CameraLogic,VideoLogic logic
    class DataStore,Hardware data
```

## Real-Time Processing Flow

```mermaid
sequenceDiagram
    participant Camera as Camera Source
    participant Capture as Frame Capture
    participant YOLO as YOLO Engine
    participant Tracker as Object Tracker
    participant API as FastAPI
    participant Client as Client Request

    loop Every Frame
        Camera->>Capture: Raw Frame
        Capture->>Capture: Preprocess (640x640)
        Capture->>YOLO: Processed Frame

        YOLO->>YOLO: Inference (GPU/CPU/MPS)
        YOLO->>Tracker: Detections (bbox, conf, class)

        Tracker->>Tracker: Update Tracks (SORT)
        Tracker->>Tracker: Calculate Statistics
        Tracker->>API: Store Results
    end

    Client->>API: GET /api/stats
    API->>Tracker: Request Statistics
    Tracker->>API: Return Stats
    API->>Client: JSON Response

    Client->>API: GET /video_feed
    API->>Capture: Request Current Frame
    Capture->>API: Frame with Bboxes
    API->>Client: MJPEG Stream
```

## Performance Optimization Flow

```mermaid
flowchart TD
    Input[Camera Input] --> Threading
    Threading[Async Frame Capture\nSeparate Thread] --> Buffer
    Buffer[Frame Buffer\nCircular Queue] --> GPU
    GPU[GPU Acceleration\nCUDA/MPS/CPU] --> Batch
    Batch[Batch Processing\nEfficient Inference] --> Cache
    Cache[Result Caching\nAvoid Re-computation] --> API

    subgraph Optimizations [Performance Optimizations]
        ModelOpt[Model Optimization\nYOLOv8n - Fastest] --> GPU
        Resolution[Resolution Control\n640x640 Default] --> Buffer
        ConfThreshold[Confidence Threshold\nFilter Weak Detections] --> Batch
        FPSControl[FPS Limiting\nResource Management] --> Threading
    end

    ModelOpt --> GPU
    Resolution --> Buffer
    ConfThreshold --> Batch
    FPSControl --> Threading

    classDef flow fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef opt fill:#f59e0b,stroke:#1f2937,stroke-width:2px,color:#1f2937

    class Input,Threading,Buffer,GPU,Batch,Cache,API flow
    class ModelOpt,Resolution,ConfThreshold,FPSControl opt
```

## Service Deployment Architecture

```mermaid
flowchart TB
    subgraph Development [Development Environment]
        DevCode[Source Code] --> DevSetup
        DevSetup[./setup.sh] --> DevEnv
        DevEnv[uv Python Env] --> DevRun
        DevRun[uv run python -m src.main] --> DevAPI
        DevAPI[API :8080] --> DevTest
        DevTest[curl http://localhost:8080/health]
    end

    subgraph Production [Production Deployment]
        Ansible[oaAnsible Automation] --> Deploy
        Deploy[Service Deployment] --> Service
        Service[LaunchAgent/systemd] --> Monitor
        Monitor[Service Monitoring] --> Logs
        Logs[Log Management] --> Health
        Health[Health Checks] --> API
    end

    subgraph Integration [System Integration]
        API[oaTracker API :8080] --> CamBridge
        CamBridge[oaCamBridge :8086] --> Dashboard
        Dashboard[oaDashboard :9092] --> Users
        API --> Sentinel
        Sentinel[oaSentinel Models] --> CustomDetection
    end

    Production --> Integration

    classDef dev fill:#1e293b,stroke:#f1f5f9,stroke-width:2px,color:#f1f5f9
    classDef prod fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef integ fill:#3b82f6,stroke:#1f2937,stroke-width:2px,color:#1f2937

    class DevCode,DevSetup,DevEnv,DevRun,DevAPI,DevTest dev
    class Ansible,Deploy,Service,Monitor,Logs,Health,API prod
    class CamBridge,Dashboard,Users,Sentinel,CustomDetection integ
```

## Error Handling and Recovery

```mermaid
stateDiagram-v2
    [*] --> Starting
    Starting --> LoadModel: Initialize Service
    LoadModel --> InitCamera: Model Loaded
    InitCamera --> Running: Camera Ready

    Running --> CameraError: Camera Disconnect
    CameraError --> RetryCamera: Retry Connection
    RetryCamera --> Running: Camera Reconnected
    RetryCamera --> FatalError: Max Retries

    Running --> ModelError: Model Load Fail
    ModelError --> ReloadModel: Reload Model
    ReloadModel --> Running: Model OK
    ReloadModel --> FatalError: Model Failed

    Running --> APIError: API Exception
    APIError --> RestartAPI: Restart Service
    RestartAPI --> Running: API OK

    FatalError --> [*]: Service Shutdown

    Running --> Maintenance: Maintenance Mode
    Maintenance --> Running: Resume Normal
```

## Key Performance Indicators

```mermaid
flowchart LR
    subgraph Metrics [Performance Metrics]
        FPS[Frames Per Second\nTarget: 25-30 FPS]
        Latency[Detection Latency\nTarget: <100ms]
        Memory[Memory Usage\nTarget: <2GB]
        CPU[CPU Usage\nTarget: <50%]
        Accuracy[Detection Accuracy\nTarget: >95%]
        Uptime[Service Uptime\nTarget: 99.9%]
    end

    subgraph Monitoring [Monitoring & Alerting]
        HealthChecks[Health Endpoints] --> Alerts
        Alerts[Alert System] --> Dashboard
        Dashboard[Monitoring Dashboard] --> Logs
        Logs[Log Aggregation] --> Analysis
        Analysis[Performance Analysis] --> Optimization
        Optimization[Auto-Optimization] --> Metrics
    end

    Metrics --> Monitoring

    classDef metric fill:#f59e0b,stroke:#1f2937,stroke-width:2px,color:#1f2937
    classDef monitor fill:#10b981,stroke:#1f2937,stroke-width:2px,color:#1f2937

    class FPS,Latency,Memory,CPU,Accuracy,Uptime metric
    class HealthChecks,Alerts,Dashboard,Logs,Analysis,Optimization monitor
```
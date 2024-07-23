import SwiftUI
import AVFoundation
import CoreML
import Vapor

@main
struct CoreMLPlayerApp: App {
    @ObservedObject private var coreMLModel = CoreMLModel()
    @ObservedObject private var drawSettings = DrawSettings()
    @ObservedObject private var detectionStats = DetectionStats.shared // updated from other classes

    var body: some Scene {
        Window("CoreML Player", id: "main") {
            MainView()
                .environmentObject(coreMLModel)
                .environmentObject(drawSettings)
                .environmentObject(detectionStats)
                .onAppear {
                    coreMLModel.autoload()
                }
                .frame(minWidth: 900, maxWidth: .infinity, minHeight: 530, maxHeight: .infinity, alignment: .center)
        }
        .commands {
            CommandGroup(replacing: .appInfo) {
                Button("List Cameras and Exit") {
                    listCameras()
                    exit(EXIT_SUCCESS)
                }
            }
        }
    }
    
    init() {
        handleCommandLineArguments()
    }
    
    private func handleCommandLineArguments() {
        let arguments = CommandLine.arguments

        if arguments.contains("-listCameras") {
            listCameras()
            exit(EXIT_SUCCESS)
        } else if arguments.contains("-listScreens") {
            listScreens()
            exit(EXIT_SUCCESS)
        } else if let cameraIndex = arguments.firstIndex(of: "-camera") {
            if cameraIndex + 1 < arguments.count {
                let cameraID = arguments[cameraIndex + 1]
                coreMLModel.selectCamera(byID: cameraID)
            } else {
                print("Camera ID not specified")
                exit(EXIT_FAILURE)
            }
        } else if let modelIndex = arguments.firstIndex(of: "-model") {
            if modelIndex + 1 < arguments.count {
                let modelPath = arguments[modelIndex + 1]
                loadModel(at: modelPath)
            } else {
                print("Model path not specified")
                exit(EXIT_FAILURE)
            }
        } else if let labelsIndex = arguments.firstIndex(of: "-labels") {
            if labelsIndex + 1 < arguments.count {
                let labels = arguments[labelsIndex + 1].split(separator: ",").map { String($0) }
                coreMLModel.filterLabels(labels)
            } else {
                print("Labels not specified")
                exit(EXIT_FAILURE)
            }
        } else if let serverIndex = arguments.firstIndex(of: "-server") {
            if serverIndex + 1 < arguments.count {
                let port = arguments[serverIndex + 1]
                startHTTPServer(onPort: port)
            } else {
                print("Server port not specified")
                exit(EXIT_FAILURE)
            }
        } else if let rtspIndex = arguments.firstIndex(of: "-rtsp") {
            if rtspIndex + 1 < arguments.count {
                let rtspURL = arguments[rtspIndex + 1]
                coreMLModel.startRTSPStream(withURL: rtspURL)
            } else {
                print("RTSP URL not specified")
                exit(EXIT_FAILURE)
            }
        }
    }
    
    private func listCameras() {
        let devices = AVCaptureDevice.DiscoverySession(
            deviceTypes: [.builtInWideAngleCamera, .externalUnknown],
            mediaType: .video,
            position: .unspecified
        ).devices
        
        for device in devices {
            print("Camera: '\(device.localizedName)' - ID: '\(device.uniqueID)'")
        }
    }
    
    private func listScreens() {
        let screens = NSScreen.screens
        for (index, screen) in screens.enumerated() {
            print("Screen ID: \(index) - '\(screen.localizedName)'")
            print("  Frame: \(screen.frame)")
            print("  Backing Scale Factor: \(screen.backingScaleFactor)")
        }
    }
    
    private func loadModel(at path: String) {
        do {
            let modelURL = URL(fileURLWithPath: path)
            let model = try MLModel(contentsOf: modelURL)
            coreMLModel.loadModel(mlmodel: model)
            print("Loaded model from \(path)")
        } catch {
            print("Failed to load model from \(path): \(error.localizedDescription)")
            exit(EXIT_FAILURE)
        }
    }
    
    private func startHTTPServer(onPort port: String) {
        let app = Application(.development)
        defer { app.shutdown() }
        
        app.get("detections") { req -> String in
            let detections = coreMLModel.detections
            let jsonData = try JSONEncoder().encode(detections)
            return String(data: jsonData, encoding: .utf8) ?? "[]"
        }
        
        try? app.run()
    }
}

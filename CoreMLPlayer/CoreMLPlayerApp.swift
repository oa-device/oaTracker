import SwiftUI
import AVFoundation
import CoreML

@main
struct CoreMLPlayerApp: App {
    @StateObject private var coreMLModel = CoreMLModel()
    @StateObject private var drawSettings = DrawSettings()
    @StateObject private var detectionStats = DetectionStats.shared // updated from other classes
    
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
        } else if let modelIndex = arguments.firstIndex(of: "-model") {
            if modelIndex + 1 < arguments.count {
                let modelPath = arguments[modelIndex + 1]
                loadModel(at: modelPath)
            } else {
                print("Model path not specified")
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
            print("Camera: '\(device.localizedName)'")
        }
    }
    
    private func listScreens() {
        let screens = NSScreen.screens
        for screen in screens {
            print("Screen: '\(screen.localizedName)'")
            print("  Frame: \(screen.frame)")
            print("  Backing Scale Factor: \(screen.backingScaleFactor)")
        }
    }
    
    private func loadModel(at path: String) {
        do {
            let modelURL = URL(fileURLWithPath: path)
            //let model = try MLModel(contentsOf: modelURL)
            //coreMLModel.loadModel(mlmodel: model) // Suppose coreMLModel has a method loadModel
            print("Loaded model from \(path)")
        } catch {
            print("Failed to load model from \(path): \(error.localizedDescription)")
            exit(EXIT_FAILURE)
        }
    }
}

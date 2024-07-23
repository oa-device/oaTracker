//
//  DetectedObject.swift
//  CoreML Player
//
//  Created by NA on 1/26/23.
//

import Foundation
import CoreGraphics

struct DetectedObject: Identifiable, Codable {
    let id: UUID
    let label: String
    let confidence: String
    let otherLabels: [(label: String, confidence: String)]
    let width: CGFloat
    let height: CGFloat
    let x: CGFloat
    let y: CGFloat
    var isClassification: Bool = false

    init(id: UUID, label: String, confidence: String, otherLabels: [(label: String, confidence: String)], width: CGFloat, height: CGFloat, x: CGFloat, y: CGFloat, isClassification: Bool) {
            self.id = id
            self.label = label
            self.confidence = confidence
            self.otherLabels = otherLabels
            self.width = width
            self.height = height
            self.x = x
            self.y = y
            self.isClassification = isClassification
        }
    
    // Custom encoding to handle the tuple array `otherLabels`
    enum CodingKeys: String, CodingKey {
        case id
        case label
        case confidence
        case otherLabels
        case width
        case height
        case x
        case y
        case isClassification
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(label, forKey: .label)
        try container.encode(confidence, forKey: .confidence)
        try container.encode(width, forKey: .width)
        try container.encode(height, forKey: .height)
        try container.encode(x, forKey: .x)
        try container.encode(y, forKey: .y)
        try container.encode(isClassification, forKey: .isClassification)

        // Encoding the tuple array
        var otherLabelsContainer = container.nestedUnkeyedContainer(forKey: .otherLabels)
        for otherLabel in otherLabels {
            var labelContainer = otherLabelsContainer.nestedContainer(keyedBy: CodingKeys.self)
            try labelContainer.encode(otherLabel.label, forKey: .label)
            try labelContainer.encode(otherLabel.confidence, forKey: .confidence)
        }
    }

    // Implementing Decodable
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(UUID.self, forKey: .id)
        label = try container.decode(String.self, forKey: .label)
        confidence = try container.decode(String.self, forKey: .confidence)
        width = try container.decode(CGFloat.self, forKey: .width)
        height = try container.decode(CGFloat.self, forKey: .height)
        x = try container.decode(CGFloat.self, forKey: .x)
        y = try container.decode(CGFloat.self, forKey: .y)
        isClassification = try container.decode(Bool.self, forKey: .isClassification)

        // Decoding the tuple array
        var otherLabelsContainer = try container.nestedUnkeyedContainer(forKey: .otherLabels)
        var otherLabelsArray: [(label: String, confidence: String)] = []
        while !otherLabelsContainer.isAtEnd {
            let labelContainer = try otherLabelsContainer.nestedContainer(keyedBy: CodingKeys.self)
            let otherLabel = try labelContainer.decode(String.self, forKey: .label)
            let otherConfidence = try labelContainer.decode(String.self, forKey: .confidence)
            otherLabelsArray.append((label: otherLabel, confidence: otherConfidence))
        }
        otherLabels = otherLabelsArray
    }
}

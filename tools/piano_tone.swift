import Foundation
import AVFoundation

// usage: piano_tone <out.wav> <holdSeconds> <midiNote1> [midiNote2 ...]
let args = CommandLine.arguments
guard args.count >= 4 else {
    FileHandle.standardError.write("usage: piano_tone <out.wav> <holdSeconds> <midiNote1> [midiNote2 ...]\n".data(using: .utf8)!)
    exit(1)
}
let outPath = args[1]
guard let holdSeconds = Double(args[2]) else {
    FileHandle.standardError.write("bad duration\n".data(using: .utf8)!)
    exit(1)
}
let notes: [UInt8] = args[3...].compactMap { UInt8($0) }
guard !notes.isEmpty else {
    FileHandle.standardError.write("no notes\n".data(using: .utf8)!)
    exit(1)
}

let dlsURL = URL(fileURLWithPath: "/System/Library/Components/CoreAudio.component/Contents/Resources/gs_instruments.dls")

let engine = AVAudioEngine()
let sampler = AVAudioUnitSampler()
engine.attach(sampler)

let sampleRate = 44100.0
let format = AVAudioFormat(standardFormatWithSampleRate: sampleRate, channels: 2)!
engine.connect(sampler, to: engine.mainMixerNode, format: format)

do {
    try sampler.loadSoundBankInstrument(
        at: dlsURL,
        program: 0,
        bankMSB: UInt8(kAUSampler_DefaultMelodicBankMSB),
        bankLSB: UInt8(kAUSampler_DefaultBankLSB)
    )
} catch {
    FileHandle.standardError.write("failed to load instrument: \(error)\n".data(using: .utf8)!)
    exit(1)
}

let tailSeconds = 1.4
let totalSeconds = holdSeconds + tailSeconds

do {
    try engine.enableManualRenderingMode(.offline, format: format, maximumFrameCount: 4096)
    try engine.start()
} catch {
    FileHandle.standardError.write("engine setup failed: \(error)\n".data(using: .utf8)!)
    exit(1)
}

let outSettings: [String: Any] = [
    AVFormatIDKey: kAudioFormatLinearPCM,
    AVSampleRateKey: sampleRate,
    AVNumberOfChannelsKey: 2,
    AVLinearPCMBitDepthKey: 16,
    AVLinearPCMIsFloatKey: false,
    AVLinearPCMIsBigEndianKey: false
]

guard let outFile = try? AVAudioFile(forWriting: URL(fileURLWithPath: outPath), settings: outSettings) else {
    FileHandle.standardError.write("cannot create output file\n".data(using: .utf8)!)
    exit(1)
}

guard let buffer = AVAudioPCMBuffer(pcmFormat: engine.manualRenderingFormat, frameCapacity: engine.manualRenderingMaximumFrameCount) else {
    FileHandle.standardError.write("cannot create buffer\n".data(using: .utf8)!)
    exit(1)
}

let totalFrames = AVAudioFramePosition(totalSeconds * sampleRate)
let holdFrames = AVAudioFramePosition(holdSeconds * sampleRate)

for note in notes {
    sampler.startNote(note, withVelocity: 115, onChannel: 0)
}

var renderedFrames: AVAudioFramePosition = 0
var stopped = false

while renderedFrames < totalFrames {
    let framesToRender = min(buffer.frameCapacity, AVAudioFrameCount(totalFrames - renderedFrames))
    do {
        let status = try engine.renderOffline(framesToRender, to: buffer)
        switch status {
        case .success:
            try outFile.write(from: buffer)
            renderedFrames += AVAudioFramePosition(buffer.frameLength)
            if !stopped && renderedFrames >= holdFrames {
                for note in notes {
                    sampler.stopNote(note, onChannel: 0)
                }
                stopped = true
            }
        case .insufficientDataFromInputNode:
            break
        case .cannotDoInCurrentContext:
            continue
        case .error:
            FileHandle.standardError.write("render error\n".data(using: .utf8)!)
            exit(1)
        @unknown default:
            fatalError()
        }
    } catch {
        FileHandle.standardError.write("render exception: \(error)\n".data(using: .utf8)!)
        exit(1)
    }
}

print("done")

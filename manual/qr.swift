// QR code for the guide's cover, from macOS's own generator:  swift qr.swift <url> <out.png>
import Foundation
import CoreImage
import AppKit

let args = CommandLine.arguments
guard args.count == 3 else { print("usage: qr.swift <text> <out.png>"); exit(1) }
let filter = CIFilter(name: "CIQRCodeGenerator")!
filter.setValue(args[1].data(using: .utf8), forKey: "inputMessage")
filter.setValue("M", forKey: "inputCorrectionLevel")
let image = filter.outputImage!.transformed(by: CGAffineTransform(scaleX: 16, y: 16))
let rep = NSBitmapImageRep(ciImage: image)
let png = rep.representation(using: .png, properties: [:])!
try! png.write(to: URL(fileURLWithPath: args[2]))

import cv2
import depthai as dai
import argparse
from ultralytics import YOLO  # Make sure YOLOv8 is installed
import torch
import numpy as np

def getFrame(queue):
    frame = queue.get()
    while queue.has():
        queue.get()
    return frame.getCvFrame()

def getColorCamera(pipeline, stream_name):
    colorCam = pipeline.createColorCamera()
    colorCam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
    colorCam.setInterleaved(False)
    colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
    colorCam.setFps(30)
    colorCam.setPreviewSize(640, 480)

    xout = pipeline.createXLinkOut()
    xout.setStreamName(stream_name)
    colorCam.preview.link(xout.input)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="YOLOv8 Detection on OAK-D Camera")
    parser.add_argument('--model', type=str, required=True, help='Path to YOLOv8 model (e.g. yolov8n.pt)')
    args = parser.parse_args()

    # Load YOLOv8 model
    model = YOLO(args.model)

    pipeline = dai.Pipeline()
    stream_name = "center"
    getColorCamera(pipeline, stream_name)

    with dai.Device(pipeline) as device:
        device.setLogLevel(dai.LogLevel.WARN)
        device.setLogOutputLevel(dai.LogLevel.WARN)
        queue = device.getOutputQueue(name=stream_name, maxSize=1, blocking=False)

        cv2.namedWindow("YOLOv8 Detection")

        while True:
            try:
                frame = getFrame(queue)
                img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                # Run YOLOv8 inference
                results = model(img, verbose=False)[0]

                # Draw results on frame
                annotated_frame = results.plot()

                cv2.imshow("YOLOv8 Detection", annotated_frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break

            except Exception as e:
                print(f"Error: {e}")
                continue

        cv2.destroyAllWindows()

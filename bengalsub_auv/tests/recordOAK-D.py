import cv2
import depthai as dai
import argparse
import os
from datetime import datetime

def getFrame(queue):
    frame = queue.get()
    while queue.has():
        queue.get()
    return frame.getCvFrame()

def getMonoCamera(pipeline, board_socket, stream_name):
    mono = pipeline.createMonoCamera()
    mono.setBoardSocket(board_socket)
    mono.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono.setFps(30)
    xout = pipeline.createXLinkOut()
    xout.setStreamName(stream_name)
    mono.out.link(xout.input)

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
    parser = argparse.ArgumentParser(description="Access specific OAK-D camera via CLI.")
    parser.add_argument('--cam', type=str, choices=['left', 'right', 'center'], required=True,
                        help='Camera to access: left, right, or center')
    parser.add_argument('--save_dir', type=str, default='recorded_videos',
                        help='Directory to save recorded video')
    args = parser.parse_args()

    # Prepare pipeline
    pipeline = dai.Pipeline()
    stream_name = args.cam
    if args.cam == 'left':
        getMonoCamera(pipeline, dai.CameraBoardSocket.CAM_B, stream_name)
    elif args.cam == 'right':
        getMonoCamera(pipeline, dai.CameraBoardSocket.CAM_C, stream_name)
    elif args.cam == 'center':
        getColorCamera(pipeline, stream_name)

    # Ensure save directory exists
    os.makedirs(args.save_dir, exist_ok=True)
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    video_filename = os.path.join(args.save_dir, f"{args.cam}_camera_{timestamp}.avi")

    # Start device
    with dai.Device(pipeline) as device:
        device.setLogLevel(dai.LogLevel.WARN)
        device.setLogOutputLevel(dai.LogLevel.WARN)
        queue = device.getOutputQueue(name=stream_name, maxSize=1, blocking=False)

        # Set video properties (depends on camera type)
        width, height = (640, 400) if args.cam in ['left', 'right'] else (640, 480)
        fourcc = cv2.VideoWriter_fourcc(*'XVID')
        out = cv2.VideoWriter(video_filename, fourcc, 30.0, (width, height))

        print(f"[INFO] Recording started: {video_filename}")
        cv2.namedWindow(f"{args.cam.capitalize()} Camera")

        while True:
            try:
                frame = getFrame(queue)
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                out.write(frame)  # Save frame to video
                cv2.imshow(f"{args.cam.capitalize()} Camera", frame)

                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("[INFO] Recording stopped.")
                    break

            except Exception as e:
                print(f"Error getting frame: {e}")
                continue

        out.release()
        cv2.destroyAllWindows()

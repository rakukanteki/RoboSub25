import cv2
import depthai as dai
import argparse

def getFrame(queue):
    # Get the latest frame and discard any buffered ones to reduce lag
    frame = queue.get()
    # Clear any remaining frames in the queue
    while queue.has():
        queue.get()
    return frame.getCvFrame()

def getMonoCamera(pipeline, board_socket, stream_name):
    mono = pipeline.createMonoCamera()
    mono.setBoardSocket(board_socket)
    mono.setResolution(dai.MonoCameraProperties.SensorResolution.THE_400_P)
    mono.setFps(30)  # Set explicit FPS

    xout = pipeline.createXLinkOut()
    xout.setStreamName(stream_name)
    mono.out.link(xout.input)

def getColorCamera(pipeline, stream_name):
    colorCam = pipeline.createColorCamera()
    colorCam.setBoardSocket(dai.CameraBoardSocket.CAM_A)
    
    # Reduced resolution for better performance
    colorCam.setResolution(dai.ColorCameraProperties.SensorResolution.THE_720_P)
    colorCam.setInterleaved(False)
    colorCam.setColorOrder(dai.ColorCameraProperties.ColorOrder.BGR)
    
    # Set FPS to reduce processing load
    colorCam.setFps(30)
    
    # Use preview for lower latency and smaller data transfer
    colorCam.setPreviewSize(640, 480)

    xout = pipeline.createXLinkOut()
    xout.setStreamName(stream_name)
    # Use preview instead of video for lower latency
    colorCam.preview.link(xout.input)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Access specific OAK-D camera via CLI.")
    parser.add_argument('--cam', type=str, choices=['left', 'right', 'center'], required=True,
                        help='Camera to access: left, right, or center')
    args = parser.parse_args()

    pipeline = dai.Pipeline()
    stream_name = ""

    if args.cam == 'left':
        stream_name = "left"
        getMonoCamera(pipeline, dai.CameraBoardSocket.CAM_B, stream_name)

    elif args.cam == 'right':
        stream_name = "right"
        getMonoCamera(pipeline, dai.CameraBoardSocket.CAM_C, stream_name)

    elif args.cam == 'center':
        stream_name = "center"
        getColorCamera(pipeline, stream_name)

    # Start pipeline
    with dai.Device(pipeline) as device:
        # Configure device for better performance
        device.setLogLevel(dai.LogLevel.WARN)
        device.setLogOutputLevel(dai.LogLevel.WARN)
        
        # Non-blocking queue with minimal buffering
        queue = device.getOutputQueue(name=stream_name, maxSize=1, blocking=False)
        cv2.namedWindow(f"{args.cam.capitalize()} Camera")

        frame_skip = 0
        while True:
            try:
                frame = getFrame(queue)
                
                # Optional: Skip frames for even lower latency (uncomment if needed)
                # frame_skip += 1
                # if frame_skip % 2 == 0:  # Skip every other frame
                #     continue

                # Convert mono to BGR for consistent display
                if len(frame.shape) == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)

                cv2.imshow(f"{args.cam.capitalize()} Camera", frame)
                
                # Reduced waitKey time for more responsive exit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            except Exception as e:
                print(f"Error getting frame: {e}")
                continue

        cv2.destroyAllWindows()
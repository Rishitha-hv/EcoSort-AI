
import cv2

# 0 = default laptop camera
# 1 = usually the external USB webcam
camera = cv2.VideoCapture(1)

if not camera.isOpened():
    print("External webcam not found. Trying laptop camera...")
    camera = cv2.VideoCapture(0)

if not camera.isOpened():
    print("Error: No webcam detected.")
    exit()

print("Webcam connected successfully!")
print("Press Q to close the camera.")

while True:
    success, frame = camera.read()

    if not success:
        print("Unable to capture frame.")
        break

    cv2.imshow("Waste Detection - Webcam Test", frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

camera.release()
cv2.destroyAllWindows()

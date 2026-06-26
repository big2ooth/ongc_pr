from ultralytics import YOLO
import cv2

# load pretrained model (downloads automatically ~6MB)
model = YOLO("yolov8n.pt")

# run on one image from your dataset
img_path = "Construction-Site-Safety-27/train/images"

import os
first_image = os.listdir(img_path)[0]
full_path = os.path.join(img_path, first_image)

print(f"Testing on: {first_image}")

results = model(full_path)
annotated = results[0].plot()

cv2.imwrite("sanity_output.jpg", annotated)
print("Done — check sanity_output.jpg in your project folder")
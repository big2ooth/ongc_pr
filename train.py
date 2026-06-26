from ultralytics import YOLO

def main():
    model = YOLO("yolov8n.pt")

    model.train(
        data="Construction-Site-Safety-27/data.yaml",
        epochs=50,
        imgsz=640,
        batch=8,
        device=0,
        workers=0,      # Start with 0 on Windows
        cache=True,
        project="runs/train",
        name="safety_model"
    )

    print("Training complete — check runs/train/safety_model/")

if __name__ == "__main__":
    main()
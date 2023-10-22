#Yeah, this is really it 
from ultralytics import YOLO

#I'm definitely going to forget how to use this at some point
if(sys.argv[1] == "-h" or sys.argv[1] == "--help"):
    print("Usage: train.py <dataset annotations> <epochs> <image size> <batch> <name> <yolo-model-size>")
    sys.exit(0)
 
# Load a model to train based on 
# options range from
# nano to large (CPU -> GPU)
model = YOLO("yolov8" + sys.argv[6] + ".pt")
 
# Training.
results = model.train(
   data=sys.argv[1],
   imgsz=int(sys.argv[3]),
   epochs=int(sys.argv[2]),
   batch=int(sys.argv[4]),
   name=sys.argv[5]
)
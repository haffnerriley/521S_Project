from ultralytics import YOLO
import cv2
from ultralytics.utils.plotting import Annotator  # ultralytics.yolo.utils.plotting is deprecated

model = YOLO('../Model/model.pt')
cap = cv2.VideoCapture(0)
cap.set(3, 1280)
cap.set(4, 720)

classList = ["Spoon", "Bowl", "Measuring cup", "Spatula", "Salt tin", "Pan", "Salt and pepper shakers", "Oatmeal box"]

while True:
    _, img = cap.read()
    
    results = model.predict(img)

    for r in results:
        
        annotator = Annotator(img)
        
        boxes = r.boxes
        for box in boxes:
            
            b = box.xyxy[0]
            c = box.cls

            #too lazy to fix class names, catch them on the fly
            classname = model.names[int(c)]

            match classname:
                case "Fork":
                    classname = "Spatula"
                case "Box":
                    classname = "Oatmeal box"
                case "Tin can":
                    classname = "Salt tin"
                case "Frying pan":
                    classname = "Pan"
                case "Mixing bowl":
                    classname = "Bowl"
                case "Coffee cup":
                    classname = "Measuring cup"

            #if not a class we want, skip class
            if 1==2:#classname not in classList:
                continue

            annotator.box_label(b, classname)
          
    img = annotator.result()  
    cv2.imshow('YOLO V8 Detection', img)     
    if cv2.waitKey(1) & 0xFF == ord(' '):
        break

cap.release()
cv2.destroyAllWindows()
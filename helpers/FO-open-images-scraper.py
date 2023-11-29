import fiftyone as fo
import fiftyone.zoo as foz
import random
from datetime import datetime
import sys
import os

# Random number with system time
random.seed(datetime.now())

#data-name stuff
dataset_name = "Identification-" + str(random.randint(1,32000))
data_types = ["train", "validation", "test"]

#I'm definitely going to forget how to use this at some point
#["Spoon", "Bowl", "Salt and pepper shakers", "Frying pan", "Measuring cup", "Box", "Tin can"]
if(sys.argv[1] == "-h" or sys.argv[1] == "--help"):
    print("Usage: FO-open-images-scraper.py <Export path> <dataset-version (6/7)> <sample limit> <class names (space separated)>")
    sys.exit(0)

#make our output dir
os.mkdir(sys.argv[1])

#grab the training data, then validation, then test
for model_type in data_types:
    dataset = foz.load_zoo_dataset(
        "open-images-v" + sys.argv[2], 
        model_type,
        label_types=["detections"], 
        classes = sys.argv[4:],
        max_samples=int(sys.argv[3]),
        seed=1,
        shuffle=True,
        dataset_name="openImages-" + dataset_name + model_type,
    )

    dataset.export(
        export_dir="./open-images7-" + model_type + dataset_name,
        dataset_type = fo.types.YOLOv5Dataset
    )

#create new structure for yolo and combine them
os.mkdir(sys.argv[1] + "/images")
os.mkdir(sys.argv[1] + "/labels")

for model_type in data_types:
    os.system("cp -r ./open-images7-" + model_type + dataset_name + "/images/val " + sys.argv[1] + "/images/" + model_type)
    os.system("cp -r ./open-images7-" + model_type + dataset_name + "/labels/val " + sys.argv[1] + "/labels/" + model_type)

#make the new yaml definition
#make sure we use the training yaml file or we overrun the end of the class list
os.system("cp ./open-images7-" + "train" + dataset_name + "/*.yaml " + sys.argv[1] + "/dataset.yaml")


#fix the error in the conversion "val" vs "validation"
lines = open(sys.argv[1] + "/dataset.yaml", "r").readlines()
ammended_line = "val: ./images/validation\n"
lines[-1] = ammended_line
lines.append("test: ./images/test/\n")
lines.append("train: ./images/train/")

open(sys.argv[1] + "/dataset.yaml", "a").writelines(lines)

#remove temp folders
for model_type in data_types:
    os.system("rm -rf ./open-images7-" + model_type + dataset_name)
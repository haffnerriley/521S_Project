import fiftyone as fo
import fiftyone.zoo as foz
import sys 
import os

classes = " "

#I'm definitely going to forget how to use this at some point
if(sys.argv[1] == "-h" or sys.argv[1] == "--help"):
    print("Usage: FOScrapingUtility.py <coco export path (relative)> <class names (space separated)> ")
    sys.exit(0)

#check if export dir exists and make if doesnt
if (not os.path.isdir(sys.argv[1])):
    os.mkdir(sys.argv[1])

# The Dataset or DatasetView containing the samples you wish to export
dataset_or_view = foz.load_zoo_dataset("coco-2017", classes = [classes.join(sys.argv[2:])], label_types=["detections", "segmentations"], splits="train")

# The directory to which to write the exported dataset
export_dir = sys.argv[1]

# The type of dataset to export
# Exporting to COCO for now and converting to YOLO later
dataset_type = fo.types.COCODetectionDataset

# Export the dataset
dataset_or_view.export(
    export_dir=export_dir,
    dataset_type=dataset_type
)
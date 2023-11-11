import fiftyone as fo
import fiftyone.zoo as foz
import sys
import os 

#I'm definitely going to forget how to use this at some point
if(sys.argv[1] == "-h" or sys.argv[1] == "--help"):
    print("Usage: FiftyOneUI.py <dataset name> <samples> <class name>")
    sys.exit(0)

#grab dataset for quick parsing
dataset = foz.load_zoo_dataset(
    sys.argv[1],
    split="train",
    max_samples=int(sys.argv[2]),
    classes=[sys.argv[3]],
    shuffle=True,
    dataset_name="dataset-"+sys.argv[1]+"-"+sys.argv[2]+"-"+str(os.getpid()) 
)

#show
session = fo.launch_app(dataset)
session.wait()
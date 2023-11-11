import fiftyone as fo
import fiftyone.zoo as foz

dataset = foz.load_zoo_dataset(
    "open-images-v7", 
    "test",
    label_types=["detections"], 
    classes = ["Spoon", "Bowl", "Salt and pepper shakers", "Frying pan", "Measuring cup", "Box", "Tin can"],
    max_samples=10000,
    seed=51,
    shuffle=True,
    dataset_name="open-images-testinger-boxadded",
)

dataset.export(
   export_dir="./open-images7-test-boxadded",
   dataset_type = fo.types.YOLOv5Dataset
)

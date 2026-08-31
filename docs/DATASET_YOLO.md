# Dataset And YOLO Notes

## Source Dataset

The source dataset lives at `Malaysian Car Plate Dataset` and currently contains:

- `train/images`
- `train/labels`
- `val/images`
- `val/labels`
- stale source `data.yaml` paths from Google Drive

The source labels include two classes:

- `0`: car
- `1`: car plate

The first prototype should train and infer only `car plate` detections.

## Label Compatibility Decision

Use YOLO detection for the first prototype, not segmentation. The product workflow needs a plate crop for OCR, and a bounding box is sufficient for cropping. The source dataset contains many polygon annotations, so the preparation script converts plate polygons to bounding boxes.

The preparation step also filters out `car` annotations and remaps source class `1` to target class `0`, which is required for a valid one-class YOLO dataset.

## Generated Dataset

The generated dataset path is ignored by Git:

```text
ml/datasets/generated/car_plate_yolo
```

Generate it only after user approval to proceed with dataset preparation:

```bash
python scripts/prepare_car_plate_yolo_dataset.py --write-prepared-dataset
```

The script writes:

- `docs/dataset_yolo_report.json`
- `ml/datasets/car_plate_test_manifest.txt`
- `ml/datasets/generated/car_plate_yolo/...` when `--write-prepared-dataset` is supplied

## Test Split

A deterministic test subset is reserved from the original validation split using seed `20260831`. This gives the prototype a separate held-out test list without changing the original downloaded dataset.

## Training Command

ML dependencies and the `yolo11n.pt` base weights have been installed/downloaded after user approval. Local training is not preferred because this machine currently reports CPU-only PyTorch. Use the Colab workflow for GPU training.

```bash
ml/.venv/Scripts/yolo.exe cfg=ml/configs/car_plate_train.yaml
```
## Observed Training Results

The user reported overall model performance of 92.8 percent on the test dataset from the initial Colab run. The next Colab training pass should use 150 epochs to attempt improvement while keeping the same one-class `car plate` dataset and `yolo11n.pt` base model.
## Trained Model Artifact

The 150-epoch Colab run produced a downloaded `best.pt` artifact. It is stored locally at:

```text
models/trained/car_plate_yolo_best.pt
```

The user reported 93.1 percent accuracy on the test dataset for this run. The `models/` directory is ignored by Git, so the binary model artifact is intentionally local unless a separate model-release or artifact-storage process is chosen later.
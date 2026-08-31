# Google Colab YOLO Training

Google Colab is recommended for YOLO training because the local machine currently reports CPU-only PyTorch.

## Local Preparation

The prepared one-class dataset is generated from the source dataset with:

```bash
ml/.venv/Scripts/python.exe scripts/prepare_car_plate_yolo_dataset.py --write-prepared-dataset
```

Package it for upload:

```bash
ml/.venv/Scripts/python.exe scripts/package_colab_yolo_dataset.py
```

This writes:

```text
ml/datasets/car_plate_yolo_colab.zip
```

The zip is ignored by Git because it is generated data.

## Colab Workflow

1. Upload `car_plate_yolo_colab.zip` to Google Drive, preferably under `MyDrive/capstone-alpr/`.
2. Open `ml/notebooks/car_plate_yolo_colab.ipynb` in Google Colab.
3. Set runtime type to GPU.
4. Run the notebook cells in order.
5. Download the best trained weights from the Colab run output.

## Expected Dataset Shape

The notebook expects this extracted structure:

```text
/content/datasets/car_plate_yolo/
  train/images
  train/labels
  val/images
  val/labels
  test/images
  test/labels
```

The dataset contains one class:

```yaml
names:
  0: car plate
```

## Training Notes

The notebook uses `yolo11n.pt` with 150 epochs. The initial test performance was reported as 92.8 percent, so this pass keeps the same small base model and increases training duration before trying larger models.
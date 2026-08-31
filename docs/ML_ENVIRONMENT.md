# ML Environment Notes

## Interpreter

Use Python 3.12 for ML work. Python 3.14 is installed on this machine, but the ML package constrains installs to `<3.13` because OpenCV, PyTorch, and Ultralytics compatibility is safer on Python 3.12.

Create or recreate the environment with:

```bash
py -3.12 -m venv ml/.venv
ml/.venv/Scripts/python.exe -m pip install --upgrade pip setuptools wheel
ml/.venv/Scripts/python.exe -m pip install -e "ml[yolo,dev]"
```

## Installed Verification

The local ML environment has been verified with:

```bash
ml/.venv/Scripts/python.exe -c "import cv2, ultralytics, torch; print(cv2.__version__, ultralytics.__version__, torch.__version__, torch.cuda.is_available())"
```

Observed state:

- OpenCV: 4.14.0
- Ultralytics: 8.4.136
- PyTorch: 2.13.0+cpu
- CUDA available: false

Training can run on CPU, but it will be slower. Prefer GPU if available for full training.

## Base Weights

YOLO base weights were downloaded for training preparation and stored at:

```text
models/base/yolo11n.pt
```

The `models/` directory is ignored by Git.
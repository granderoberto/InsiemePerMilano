#!/bin/sh
# Scarica i modelli della verifica del documento (idempotente): OpenCV YuNet e SFace (volti) e i dati di Tesseract (italiano e inglese).
# Fonti ufficiali: opencv/opencv_zoo (YuNet: licenza MIT, SFace: Apache-2.0) e tesseract-ocr/tessdata_fast (Apache-2.0).
set -e
cd "$(dirname "$0")"
mkdir -p tessdata
scarica() { [ -s "$2" ] || { echo "scarico $2"; curl -fsSL --retry 3 -o "$2" "$1"; }; }
scarica https://github.com/opencv/opencv_zoo/raw/main/models/face_detection_yunet/face_detection_yunet_2023mar.onnx face_detection_yunet_2023mar.onnx
scarica https://github.com/opencv/opencv_zoo/raw/main/models/face_recognition_sface/face_recognition_sface_2021dec.onnx face_recognition_sface_2021dec.onnx
scarica https://github.com/tesseract-ocr/tessdata_fast/raw/main/ita.traineddata tessdata/ita.traineddata
scarica https://github.com/tesseract-ocr/tessdata_fast/raw/main/eng.traineddata tessdata/eng.traineddata
echo "modelli pronti in $(pwd)"

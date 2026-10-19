# Modelli per la verifica del documento

File **non versionati** (si scaricano con `sh apps/web/modelli/scarica.sh`; il `Dockerfile` lo fa in automatico):

| File | Cosa è | Licenza |
|---|---|---|
| `face_detection_yunet_2023mar.onnx` | YuNet: trova i volti (OpenCV Zoo) | MIT |
| `face_recognition_sface_2021dec.onnx` | SFace: confronta due volti (OpenCV Zoo) | Apache-2.0 |
| `tessdata/ita.traineddata`, `eng.traineddata` | dati di Tesseract OCR (tessdata_fast) | Apache-2.0 |

Serve anche il programma **Tesseract** (`brew install tesseract` su macOS, `apt install tesseract-ocr` su Debian). Se manca qualcosa il sito usa il controllo simulato (`IA_DOCUMENTO=auto`).

# Video player on a random video VREVideo plus various neural networks DataProducers

Supported neural networks:
- PHG-MAE-Distil
- YOLO

```bash
python main.py video.mp4 [--weights_path_phg model_phg.ckpt] [--weights_path_yolo model_yolo.ckpt]
```

To get checkpoints, use these links:
- 150k: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_150k.ckpt?ref_type=heads)
- 430k: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_430k.ckpt?ref_type=heads)
- 1M: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_1M.ckpt?ref_type=heads)
- 4M: [link](https://gitlab.com/video-representations-extractor/video-representations-extractor/-/raw/master/vre_repository/semantic_segmentation/safeuav/weights/model_4M.ckpt?ref_type=heads)

Controls:
- `ESC` - closes the window
- `SPACE` - pauses or plays the video
- `->` - skips on second ahead
- `<-` - goes one second behind

Webcam trickeries via ffmpeg:

```bash
ffmpeg -i https://w3.webcamromania.ro/busteni/index.m3u8 -f rawvideo -pix_fmt rgb24 - | CUDA_VISIBLE_DEVICES=0 VRE_VIDEO_LOGLEVEL=2 ROBOBASE_LOGLEVEL=2 ROBOIMPL_LOGLEVEL=2 ./main.py - --weights_path_yolo yolo11s.pt --yolo_threshold 0.1 --frame_resolution 800 1280 --fps 30
```

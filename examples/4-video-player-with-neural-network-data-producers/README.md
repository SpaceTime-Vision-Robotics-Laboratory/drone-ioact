# Video player on a random video VREVideo plus various neural networks DataProducers

Supported neural networks:
- PHG-MAE-Distil
    - TODO: flags
- TODO: YOLO

```bash
# TODO: argparse this properly
python main.py video.mp4 model.ckpt
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

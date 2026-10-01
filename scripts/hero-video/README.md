# Thrum hero demo video

Generates the swipe-deck animation used in the phone mockup on `/thrum/`.

It's not a screen recording — real TMDB poster art can't be reused outside
the app (this is also why the App Store listing was rejected once already,
see the site repo's commit history around `e2be3b2`). Instead this draws the
UI chrome from scratch with Pillow, pulling colors/layout straight from the
real app's components (`MovieCard.tsx`, `CardStack.tsx`), and uses three
licensed Unsplash photos (see `../../assets/images/CREDITS.md`) as stand-ins
for movie posters, labeled with fictional titles.

## Usage

```bash
python3 build_swipe_gif.py
```

Writes 46 PNG frames to `video_frames/` and a preview GIF to `swipe-demo.gif`
(both gitignored — regenerate, don't commit). Then encode to the two formats
the site actually uses:

```bash
ffmpeg -framerate 100/7 -i video_frames/frame_%03d.png \
  -c:v libx264 -pix_fmt yuv420p -crf 20 -movflags +faststart \
  thrum-hero-phone-screen-vN.mp4

ffmpeg -framerate 100/7 -i video_frames/frame_%03d.png \
  -c:v libvpx-vp9 -pix_fmt yuv420p -crf 32 -b:v 0 \
  thrum-hero-phone-screen-vN.webm
```

420×908, ~14.29fps (100/7), 3.22s, looping. Copy both files into
`../../assets/images/` and update the `<source>` tags in `../../thrum/index.html`.

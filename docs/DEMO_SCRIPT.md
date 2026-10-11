# FieldLens AI demo recording script

Use this script to record the real browser workflow after granting the screen-recording permission requested by macOS or your capture tool. Keep the browser at a readable desktop width and record about 60–90 seconds.

1. Show the FieldLens AI landing page and the local/fallback status badge.
2. Choose **Plan an outdoor mission**, select 30 minutes, Park, and Birds, then choose **Create my field mission**.
3. Pause on the generated card long enough to read its title, steps, duration, and explicit `fallback` or `local_model` source label.
4. Start **screen-free mode**, show the timer and safety reminder, then return and complete the mission.
5. Save an observation in the journal, scroll to the saved entry, reload the page, and show that the entry remains.
6. End on the FieldLens AI name and repository URL.

The checked-in PNGs in this folder are genuine captures of the running app. They must not be stitched together and presented as a live recording. The current development environment did not produce a video file because the macOS `screencapture` video mode did not return an output file; create `docs/demo.mp4` with a real capture before publication if screen-recording permission is available.

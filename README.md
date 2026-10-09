# Inquisitor Halloween transition

Static, silent, continuously looping video for a Genially iframe. The public HTML URL remains [https://english-with-svetlana.github.io/inquisitor-Halloween/](https://english-with-svetlana.github.io/inquisitor-Halloween/). No repository, remote, or GitHub Pages configuration was changed.

## Loading investigation and fixes

The previously published playback MP4 was **12,049,668 bytes** for a **2.534017-second** presentation. Its reported video bitrate was about **31.2 Mbps**. Earlier optimization had removed audio and moved metadata to the front but had not compressed video. Its H.264 High profile, level 4.0, and 1920×1080 resolution are ordinary browser-compatible settings; the excessive data rate was the main avoidable loading cost. It had only one keyframe, with an edit list requiring preroll before the displayed animation.

The published Inquisitor HTML and MP4 were fetched and matched the local version and its SHA-256 hash. The reference [Tunnel page](https://english-with-svetlana.github.io/tunnel-Halloween/) used essentially the same full-viewport `contain` layout and frame-callback/opacity reveal approach. Its MP4 was 7,164,965 bytes for about seven seconds, with a reported video bitrate of about 7.9 Mbps. Its inspected HTML did not enable native looping, and its media contained audio, so those parts were not copied.

One Inquisitor MP4 request timed out after 60 seconds with no first byte; a retry succeeded with a 0.91-second first byte and a 2.43-second complete download. Tunnel downloaded in 3.76 seconds, with a 1.09-second first byte. These measurements are from this environment, not the user's browser. They show intermittent delivery trouble but cannot determine whether DNS, connection, proxy, CDN, or the Genially/browser environment caused the reported minute-long wait. File-size reduction cannot guarantee elimination of network outages.

Both public pages and MP4s returned `Cache-Control: max-age=600`, ETags, and byte-range support. A subsequent Inquisitor request returned **206 Partial Content** for bytes 0–1023, and an ETag revalidation returned **304 Not Modified**. There is no evidence that the page forces a fresh full download on every refresh: it has no cache-busting queries, fetch/blob loading, or cache-disabling code. Browser refresh/cache policy and Genially's iframe lifecycle determine actual reuse. Browser request traces were unavailable.

The implementation now:

- Compresses all 73 encoded frames while preserving their presentation order, timestamps, durations, the original edit window, 1920×1080 resolution, and aspect ratio.
- Uses silent H.264/yuv420p MP4 with faststart and a maximum 48-frame keyframe interval. The new reported video bitrate is about 17.5 Mbps; the detailed source is still relatively expensive to compress at full resolution.
- Uses the video element's native poster lifecycle instead of an opacity gate waiting for a frame callback. The existing first-frame JPEG remains unchanged. A separate image is shown only on autoplay rejection or media error.
- Keeps native infinite looping, muted inline autoplay, zero volume, and disabled controls. There are no end handlers or disappearance timers.
- Pauses only on document visibility/page lifecycle signals and resumes without seeking back to zero. Ordinary `pageshow` does not trigger duplicate playback. Cross-origin parent CSS hiding may not produce these signals.
- Centers an explicit 16:9 stage within the viewport using `width: min(100vw, 177.777778vh)`. It prevents scrollbars and white margins. A viewport with another aspect ratio necessarily has black letterboxing if cropping and stretching are prohibited. Use a 16:9 iframe in Genially to avoid those bands.

| Asset | Bytes |
| --- | ---: |
| Retained original `inquisitor.mp4` | 12,095,807 |
| Previous playback MP4 | 12,049,668 |
| New playback MP4 | 6,765,197 |
| Unchanged first-frame JPEG | 552,935 |

Reduction: **44.07% from the original**, **43.86% from the previous playback file**. Compression changes pixel values slightly. An all-73-frame SSIM comparison measured **0.965001**. A corresponding middle frame was inspected side by side; its composition and appearance were preserved. This is not a full-motion perceptual review.

## Run locally

From this folder:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/`. No build or package installation is needed for playback.

## Optimize or replace the source

Requirements: Python 3, FFmpeg with libx264, FFprobe, and Node.js for the playback logic tests. Preserve a backup before replacing the retained original `inquisitor.mp4`.

```sh
python3 scripts/optimize.py
python3 scripts/check.py
node scripts/check-playback.cjs
```

The optimizer is tailored to this non-transparent, version-0-timing MP4. It decodes with the source edit list disabled so none of the 73 encoded frames is lost, compresses with libx264 slow/CRF 24, and restores the exact edit window and sample-duration table. It rebuilds the MP4 atom sizes and adjusts chunk offsets when metadata grows. The fixed B-frame/keyframe settings preserve this source's irregular final frame duration. It validates all displayed and preroll frame timing before writing published assets. Different frame rates, edit lists, or timing structures may require adapting the workflow; unsupported timing fails rather than silently publishing changed timing. Transparent input must use a different compatible media solution.

The first-frame poster is generated from the original displayed first frame, not a shifted preroll frame. The original source is never overwritten. The generated playback MP4 contains no audio stream. The original retained MP4 has audio and is never referenced by the page.

Edit `scripts/index.template.html` for page changes. Rebuilding regenerates `index.html` and `assets.json`, preserving silent looping, poster/error behavior, and layout. Video and poster names contain the first 16 hexadecimal characters of their SHA-256 hashes. Changed bytes get new filenames; unchanged assets retain their cacheable filenames. No random query parameters are used. Old hashed files remain for cached older HTML; remove them only when no published/cached HTML still needs them.

## Publish and embed

Review and test, then personally commit and push using the existing GitHub Pages process. Include the regenerated HTML and all assets referenced by `assets.json`; retain scripts and source for maintenance. No commit, push, or deployment was performed for this change.

In Genially, embed the **existing HTML page URL** through an iframe/web-content embed, rather than the raw MP4 or a video-player widget. Where iframe markup is allowed, use `allow="autoplay"`. Keep iframe dimensions at 16:9. The workspace does not expose the Genially presentation, so its embed settings have not been inspected or modified.

Cached HTML can keep referencing the older, larger video until its cache expires. The observed GitHub Pages freshness window was ten minutes; Genially and browser caches may differ. Changed asset hashes take effect once updated HTML loads through the same public URL. The page cannot invalidate parent caches or configure GitHub Pages headers.

## Verification and limitations

`check.py` verifies source/output frame timestamps and durations for all 73 encoded frames and the 61-frame edited presentation, exact video/movie duration, dimensions and aspect ratio, error-free decoding, all-frame SSIM, no audio, faststart, hashes and actual active `src`/poster paths, autoplay/loop/controls configuration, matching template output, layout fit calculations across five viewport sizes, and real localhost HTTP responses.

`check-playback.cjs` verifies immediate native poster/video visibility, zero volume, silent native-loop configuration, rejected and thrown autoplay fallback, media-error fallback, no end handler, visibility/page-restoration resume, initial-hidden startup, and absence of duplicate initial playback or restart seeks. These are simulated application-event tests, not an actual browser media engine.

No real browser was connected. Ten-second playback, repeated native loops, refresh behavior in a browser, measured startup in Genially, and rendered iframe layouts remain unverified. Native looping is configured; it has not been watched over multiple iterations. Browser or parent permissions can still reject autoplay, in which case the first-frame image stays visible and controls are never offered. Network failure likewise leaves the poster. Genially can hide retained cross-origin iframes without a child visibility signal; the page cannot reliably detect every such hide/show. The source is not transparent, and black pixels in the video remain unchanged.

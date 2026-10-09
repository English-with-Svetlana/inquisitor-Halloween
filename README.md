# Inquisitor transition

A static video page for a Genially iframe. The existing page path is unchanged. No repository, remote, or GitHub Pages configuration is changed.

The original `inquisitor.mp4` is retained for future optimization. It contains non-transparent H.264 High-profile video, 1920×1080, square pixels, and AAC audio. Its video track has 73 encoded frames and an MP4 edit list defining a 2.534017-second presentation. Not all encoded frames are visible: decoding the edited presentation yields 61 frames. The optimized copy preserves every encoded video packet, timestamp, and presentation duration, removes audio, and places MP4 metadata before video data for fast startup.

| Asset | Size |
| --- | ---: |
| Original MP4 | 12,095,807 bytes |
| Playback MP4 | 12,049,668 bytes |
| First-frame JPEG | 552,935 bytes |

Video reduction: **0.38%**. A trial H.264 re-encode produced 61 encoded frames and a 2.541992-second duration, violating exact frame and timing preservation. It was discarded. This workflow deliberately uses lossless stream copying rather than introducing timing changes. The poster is a high-quality, full-resolution JPEG from the actual first displayed frame, with no cropping or resizing. JPEG compression may introduce small pixel differences.

## Run locally

From this folder:

```sh
python3 -m http.server 8000
```

Open `http://localhost:8000/`. The page needs no build, package installation, or server-side code. For parent-controlled autoplay, use an iframe with `allow="autoplay"` in Genially if its embedding settings permit it.

## Optimize or replace the source

Install Python 3, FFmpeg, and FFprobe. Keep a backup of the existing original before replacing `inquisitor.mp4`. Run:

```sh
python3 scripts/optimize.py
python3 scripts/check.py
node scripts/check-playback.cjs
```

The optimizer is tailored to this non-transparent MP4 and its version-0 timing atoms and edit list. It refuses unsupported timing structures. For a source with different container/edit-list structures or transparency, adapt the workflow and checks before publishing; do not flatten transparent media to ordinary H.264. It stream-copies video, removes sound, restores the original presentation timing that FFmpeg otherwise rebuilds, makes a poster, and regenerates `index.html` and `assets.json` from `scripts/index.template.html`. Edit that template for future page changes.

Video and poster filenames contain the first 16 hexadecimal characters of their SHA-256 content hashes. Identical assets keep their filenames; changed content gets new filenames automatically. No random query parameters are used. Old generated assets are retained by the optimizer; remove obsolete files only after checking that no published HTML still references them. The original source is never overwritten by the workflow.

## Publish future changes

Review and test the files, then personally commit and push using the repository's existing GitHub Pages publication process. Include `index.html` and every asset referenced by `assets.json`. Keep the repository name, Pages settings, and existing Genially iframe URL unchanged. The scripts and original media can also be committed for future maintenance.

HTML caching in Genially, the browser, or GitHub Pages can delay updated references. New assets become visible through the same iframe URL after publication and normal HTML cache expiration. A static page cannot force parent-page cache invalidation or configure GitHub Pages cache headers.

## Playback and layout

The page preloads the poster and requests the video immediately with muted autoplay, inline playback, and no controls. The poster stays beneath the video and the video is revealed after a presented-frame callback when supported; older browsers use the `playing` event. Failed loading or rejected autoplay returns to the poster without retry loops or visible loading UI. Playback ends naturally on its last frame; no hiding timer or loop is added.

Both media elements fill the iframe using centered `object-fit: contain`. The original 16:9 composition fits arbitrary iframe dimensions without cropping or stretching. Unused iframe space is transparent, and video pointer interaction is disabled. Black pixels present in the original video remain unchanged. There are no margins, white backgrounds, or scrollbars. The original has no transparency.

The page pauses when the document becomes hidden and replays from the beginning when document visibility returns. It also replays after page restoration when `pagehide` was observed. Ordinary initial `pageshow` does not restart playback. Genially can hide an iframe with CSS without notifying its cross-origin document; this cannot be reliably detected inside the iframe. Such a hide/show may not replay unless Genially reloads it or exposes a visibility signal. Browser or parent permissions can still block autoplay; the poster remains the fallback. Actual playback cannot appear before bytes arrive, the page stays transparent until the poster loads.

## Verification

`check.py` checks all 73 compressed video packet hashes and timestamps against the original, exact duration, resolution and aspect ratio, removed audio, faststart atom order, poster dimensions, hashed filenames, active asset references, playback/layout settings, and real HTTP responses from a temporary localhost server. `check-playback.cjs` checks playback logic with simulated events: first-frame reveal, rejected autoplay, errors, visibility replay, page restoration, and duplicate initial playback prevention. Re-running the optimizer produced identical hashes.

No browser was available in this session. Actual autoplay, rendered iframe layouts at multiple viewport sizes, perceptual poster matching, and real Genially behavior remain unverified. Layout settings were checked statically; playback events were simulated. Test the published page in Genially before relying on replay behavior.

## Genially embedding and autoplay fix

Embed the existing GitHub Pages **HTML page URL** in Genially's iframe/web-content embed, rather than linking to `inquisitor.mp4` or an `assets/*.mp4` file or using a video-player widget. A raw MP4 opens the browser or Genially media player, whose controls this page cannot disable. Keep the same public page URL. If iframe markup is supported, use the existing page URL as its `src` and include `allow="autoplay"`.

The page explicitly assigns `autoplay = true`, `muted = true`, `defaultMuted = true`, `playsInline = true`, and `controls = false`, and removes the controls attribute. No failure handler enables controls or creates a Play button. Playback is requested as soon as the video and handlers exist. Rejected autoplay leaves the first-frame poster visible. Parent autoplay permissions and browser policy remain outside this page's control.

The local HTML already had no controls attribute or code enabling controls before this fix. The reported player UI may come from a raw-video embed, a Genially video widget, or cached older HTML. The Genially presentation was not accessible for inspection here; verify its embed targets the HTML page after you publish. No media was re-encoded or recompressed for this fix.

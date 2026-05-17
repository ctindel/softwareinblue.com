# Whimsical balloon-cartoon generation prompt

Use this in ChatGPT (with image generation enabled) to add a guest into the
existing podcast balloon scene. This is the recipe that actually worked
for Episode 45 / Roberta Kang and Episode 44 / Ian Spandow.

## Attach two images alongside the prompt

1. **The original podcast cover** with Chad and Steve in the balloon:
   `hugosite/static/img/logos/podcast-cover-3000x3000.png`
2. **The guest's background-removed headshot** (PNG, transparent):
   `design/episodes/Episode<N>/headshots/<slug>-nobg.png`
   (run `rembg` on the original Hugo guest photo if you don't have it yet)

## The prompt

```
Take this podcast cover and add a third caricature based on our guest
<GUEST FULL NAME> whose photo is attached also. The 3 bodies should be
roughly equivalent in size (don't put one in the background, all 3 are
equally important) and don't change the look of either of the two
existing caricatures either, and make the guest's caricature cartoony
so it matches the look and feel of the two hosts that are already in
the balloon. Have very low detail in facial lines, eyes / eyebrows /
facial hair, actual hair etc. so the look and feel matches how Chad
and Steve are already drawn.
```

Replace `<GUEST FULL NAME>` with the guest's name (e.g. "Roberta Kang",
"Ian Spandow") so the model knows which face it's drawing from.

The pre-filled version with the right name + attachment paths is also
printed by `python3 design/preflight.py <EPISODE_NUM>` whenever the
no-overlay balloon for that episode is missing — copy/paste it
straight into ChatGPT.

## What worked / didn't work in earlier attempts

- A long descriptive prompt enumerating sky color, balloon parts, three
  character descriptions, lighting, etc. → produced inconsistent results
  and didn't match the existing show style.
- Just attaching one reference image without explicit "don't change the
  hosts" instruction → ChatGPT redrew Chad and Steve too, breaking the
  brand continuity.
- Without the "low detail / cartoony" instruction → ChatGPT rendered the
  guest in a more photoreal style (sharper eyes, hair strands, skin
  texture) which doesn't match how the hosts are drawn.
- The prompt above (short + explicit same-size + don't-change-hosts
  + low-detail style match) → produces a faithful match.

## After generating

1. Save the result as
   `design/episodes/Episode<N>/illustrations/SIB_E<N>_Balloon_no_overlay.png`
   (e.g. `SIB_E44_Balloon_no_overlay.png`). Never leave it living only in
   `~/Downloads` — the per-episode dir under the repo is the canonical home.
2. Auto-add the wordmark strip with:
   `python3 design/add_wordmark_overlay.py <EPISODE_NUM>`
   This writes `SIB_E<N>_Balloon_with_overlay.png` alongside.
3. The compositor reads both:
   - `SIB_E<N>_Balloon_with_overlay.png` → W1 wide/banner backdrop
   - `SIB_E<N>_Balloon_no_overlay.png`  → W1/W2 square + 9:16 cartoon fill,
     plus the photo circle of the A1w / A2w / A3w whimsical-emblem variants

## Reusability

Per-episode artifact — generate fresh for each guest. The prompt itself is
constant across episodes; only the guest name and the headshot attachment
change.

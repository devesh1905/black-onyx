# Brand override slot

To use your own emblem image for the splash screen and the sidebar logo, put a file here named one of:

    emblem.png   emblem.webp   emblem.jpg   emblem.svg

or point the `BLACKONYX_EMBLEM` environment variable at any image file. Restart the app (or reload the page).

- A transparent PNG works best. Wide images are fine; the splash scales them to fit.
- If your image already contains the wordmark and tagline, the splash shows it as-is (scanline reveal, subtle RGB split, one slice glitch, fade out) and skips its own text.
- Without a file here, the app uses the built-in Black Onyx emblem and a crisp "BLACK ONYX" wordmark.
- `emblem.*` in this folder is git-ignored so it stays on your machine. Remove that line from `.gitignore` if you want to commit it.

You are responsible for having the right to use any image you add.

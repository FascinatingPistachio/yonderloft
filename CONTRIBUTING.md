# Contributing to Yonderloft

Thanks for helping keep the attic lit. The most useful contribution is usually
**adding or fixing a title in the catalog** — that needs no app release and no
Python.

## Adding a title

A title is one entry in [`catalog/manifest.json`](catalog/manifest.json) plus a
cover-art file in [`catalog/art/`](catalog/art/). Open a merge request with both.

1. **Add a JSON entry** to the `titles` array. The shape is defined and validated
   by [`catalog/schema.json`](catalog/schema.json). Minimum fields:

   ```jsonc
   {
     "id": "my-game",                       // kebab-case, unique
     "name": "My Game Rewritten",           // ≤ 40 chars, shown on the card
     "category": "penguins",                // must match a categories[].id
     "runtime": "ruffle",                   // ruffle | flash | web | client
     "art": "art/my-game.png",
     "servers": [
       {
         "name": "Main",
         "url": "https://example.com/play",
         "status_url": "https://example.com/",
         "default": true
       }
     ],
     "tags": ["flash", "as2"]
   }
   ```

2. **Pick the right `runtime`.** This is the only field that's easy to get wrong:

   | If the game is…                                   | use        |
   |---------------------------------------------------|------------|
   | AS2 Flash that Ruffle renders correctly           | `ruffle`   |
   | AS3 Flash Ruffle can't render yet                 | `flash`    |
   | An HTML5 rewrite (no Flash)                        | `web`      |
   | Distributed as its own native/Electron client     | `client`   |

   When in doubt, prefer `ruffle` and **test it** — load the server's SWF in
   [the Ruffle web demo](https://ruffle.rs/demo/) first. If it renders and is
   playable, tag it `ruffle`. If it errors or stalls, fall back to `flash` and
   note why in the entry's `notes` field.

3. **Add cover art** as `catalog/art/<id>.png`. Square-ish, ≥ 460px on the short
   edge, no baked-in promo text. Don't use a rights-holder's official key art —
   use a screenshot of the community client or original fan art.

4. **Confirm the server is live** the day you submit, and that `status_url`
   returns a 2xx/3xx to a `GET`. The pinger uses it for the status badge.

5. **Validate before opening the MR:**

   ```sh
   python3 -m yonderloft.tools.validate_catalog catalog/manifest.json
   ```

   CI runs the same check. A manifest that fails the schema is rejected.

## What not to submit

- No game assets, SWFs, or client binaries in the repo. Yonderloft fetches those
  from the community server at runtime, like a browser.
- No servers you run or are affiliated with, presented as neutral catalog
  entries, without disclosing it in the MR.
- No titles you haven't actually confirmed are live and playable.

## Working on the app itself

The shell is Python + PyGObject (GTK4 / libadwaita). See
[`README.md`](README.md) §4 and §11 for architecture and layout. Build it with
Meson or, preferably, the Flatpak manifest in
[`build-aux/flatpak/`](build-aux/flatpak/):

```sh
flatpak-builder --user --install --force-clean _build \
  build-aux/flatpak/uk.aaronworld.Yonderloft.json
```

Match the surrounding style; keep the shell free of game-specific hacks — those
belong in the manifest, not the code.

## Licensing

By contributing you agree your contribution is licensed under
**GPL-3.0-or-later**, the project license.

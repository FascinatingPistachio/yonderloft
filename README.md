# Yonderloft



## Getting started

To make it easy for y# Yonderloft

> The attic where the old web lives on.

A native Linux launcher and installer for "rewritten" childhood MMOs and revival
projects — Club Penguin, Moshi Monsters, Bin Weevils, Pixie Hollow, Toontown and
the rest of the dead-flash-game graveyard that fans have brought back. Built with
GTK4 / libadwaita so it looks and behaves like a first-class GNOME app, themes
correctly on KDE, and ships as a Flatpak and AppImage.

- **Project name:** Yonderloft
- **App ID:** `uk.aaronworld.Yonderloft`
- **Repo:** `gitlab.com/FascinatingPistachio/yonderloft`
- **License:** GPL-3.0-or-later
- **Status:** design / pre-alpha

---

## 1. The problem

When a beloved online game shuts down, fans rebuild it. Club Penguin alone has a
dozen private servers; Moshi Monsters, Bin Weevils, Pixie Hollow, Virtual Magic
Kingdom, Toontown and FusionFall all have active revivals. But playing them on
Linux is a mess:

- **Flash is dead.** Most of these games were Flash. You either need Ruffle (a
  Rust/WASM Flash emulator), a sandboxed legacy Pepper Flash plugin, or the game's
  own bundled client — and which one depends on the title and even the specific
  server.
- **The tooling is Windows-first.** The main community launcher (Dragon9135's
  CPPS-Launcher) is Electron 11.5 with hard-coded `pepflashplayer.dll` paths. It's
  Windows-only and Club-Penguin-only.
- **Discovery is word-of-mouth.** The list of what's alive lives in SpaceHey forum
  threads and Discord servers. Servers go up and down constantly.
- **Security is a real concern.** These are legacy runtimes with unpatched
  Chromium/Flash vulnerabilities, and some revival servers have leaked user data.
  Running them unsandboxed on your main machine is a bad idea.

There is no native Linux app that catalogs these games, picks the right runtime
automatically, sandboxes each one, and tells you what's currently online.
Yonderloft is that app.

---

## 2. What Yonderloft is

A launcher shell plus a remote catalog.

The **shell** is a libadwaita app: a browsable grid of game "cards," each showing
cover art, a category, and a live online/offline/unstable status badge. You click
Play, and Yonderloft launches that title in the correct runtime, in its own
sandboxed window, with its own isolated profile.

The **catalog** is a remote JSON manifest (hosted in the repo / on aaronworld.uk)
describing every supported title: where its servers are, what runtime it needs,
what art to show, and how to check if it's online. Because the catalog is remote,
new games and server changes ship without a new app release.

### What it is not

- Not a server emulator. Yonderloft doesn't host games; it connects to existing
  community servers and runs their existing clients.
- Not a content redistributor. It bundles open-source runtimes (Ruffle) and links
  to community servers. It does not redistribute Disney / Mind Candy / 55pixels
  assets. Game content is fetched at runtime from the community servers, exactly
  as a browser would.
- Not affiliated with any rights holder or any individual revival project.

---

## 3. Design direction

The brief is nostalgia, but the execution must not be twee. The trap here is
making something that looks like a 2009 Flash portal — gradients, beveled buttons,
Comic Sans energy. Instead, Yonderloft is a **quiet, modern Adwaita app that holds
loud, old content.** The restraint is the point: the app is a clean glass case;
the games inside it are the colorful artifacts. This contrast is the whole
identity.

### Tokens

**Palette** — derived from the GNOME HIG palette so it sits natively alongside
other Adwaita apps, with one signature accent.

- `--loft-amber: #E5A50A`   — signature accent: warm attic/dormer light. The "on"
  state, the glow, the highlight. (GNOME palette "Yellow 5".)
- `--loft-dusk: #241F31`    — deep window-chrome / dark-mode base ("Dark 4").
- `--loft-paper: #FAF8F5`   — light-mode surface, very slightly warm.
- `--loft-slate: #5E5C64`   — secondary text / dividers ("Dark 1").
- `--loft-green: #2EC27E`   — status: online ("Green 4").
- `--loft-red: #E01B24`     — status: offline ("Red 3").
- `--loft-orange: #FF7800`  — status: unstable ("Orange 3").

Straight surfaces get flat color; gradients are reserved for curved/glowing
elements only (per HIG). The amber is used sparingly — the single warm point in an
otherwise neutral shell, like light from a loft window.

**Type** — system Adwaita stack, with intentional weight, not custom faces (custom
display faces fight the native look and break theming):

- Display / titles: **Cantarell** (or system Adwaita Sans) at 700, tight tracking.
- Body / UI: same family at 400/500.
- Data / status / version strings: a monospace face (**Source Code Pro** /
  Adwaita Mono) at small sizes — used only for technical metadata (server URL,
  runtime type, version), which makes "this is a real tool" legible.

**Signature element** — the **loft window**. The app icon is a glowing attic
dormer window; inside the app, the empty state and the "loading a game" transition
both reuse the lit-window motif (a dark frame, warm light spilling out). It's the
one memorable thing, and everything else stays disciplined around it.

### Layout

`AdwApplicationWindow` with `AdwNavigationSplitView`:

```
+----------------------------------------------------------+
| [≡]  Yonderloft                         [search]  [menu] |  <- AdwHeaderBar
+------------------+---------------------------------------+
|  Sidebar         |   Content                             |
|                  |                                       |
|  ◆ All           |   [card] [card] [card] [card]         |  <- AdwFlowBox grid
|  ◆ Favorites     |   [card] [card] [card] [card]         |     of game cards
|  ◆ Recent        |                                       |
|                  |   each card:                          |
|  Penguins        |    +------------------+               |
|  Pets & Monsters |    |  cover art       |               |
|  Fairy worlds    |    |                  |               |
|  Disney          |    |  ● online        |  <- badge     |
|  Other           |    +------------------+               |
|                  |    Moshi Monsters Rewritten           |
|                  |    Pets & Monsters · Ruffle           |
+------------------+---------------------------------------+
```

- **Sidebar:** pinned views (All / Favorites / Recent) then categories. Categories
  come from the manifest, so they're data, not hardcoded.
- **Grid:** `AdwFlowBox` of cards. Card = cover art, title, category + runtime
  badge, status dot. Hovering a card lifts it slightly (respecting
  `prefers-reduced-motion`). Clicking opens the **detail view**.
- **Detail view** (`AdwNavigationPage` pushed onto the stack): large art, full
  description, a server picker (some titles have multiple servers), a prominent
  **Play** button, last-played time, and a small disclosures panel showing the
  technical truth (runtime, server URL, sandbox status) in the mono face.
- **Game window:** a separate, sandboxed window — not the launcher chrome. Minimal:
  the game surface, a thin header with the title, a back/close, and a "clear data"
  affordance.

### Copy voice

Plain, active, slightly warm but never cutesy. "Play" not "Launch experience."
Empty Favorites reads: *"Nothing saved yet. Star a game to keep it here."* An
offline server reads: *"Penguin Journey isn't responding. The server may be down —
try again later or pick another."* Errors state what happened and what to do; they
don't apologize and they don't use a persona.

---

## 4. Architecture

```
                      +---------------------------+
                      |   Remote catalog (JSON)   |
                      |  manifest + art + status  |
                      +-------------+-------------+
                                    | fetch / cache
                                    v
+-----------------------------------------------------------+
|                     Yonderloft shell                      |
|                  (GTK4 + libadwaita, Python/PyGObject)    |
|                                                           |
|  +-------------+   +--------------+   +----------------+   |
|  | Catalog     |   | Status       |   | Profile /      |   |
|  | service     |   | pinger       |   | data manager   |   |
|  +-------------+   +--------------+   +----------------+   |
|         |                 |                  |            |
|         v                 v                  v            |
|  +----------------------------------------------------+   |
|  |              Runtime router                        |   |
|  |  decides per-title how to launch                   |   |
|  +----+-----------+-----------+-----------+-----------+   |
|       |           |           |           |               |
|       v           v           v           v               |
|   Ruffle      Sandboxed   WebKitGTK   External         |
|   (WASM/      Pepper      (HTML5      client            |
|    native)    Flash       rewrites)   (e.g. Waddle)    |
+-----------------------------------------------------------+
```

### Language / toolkit choice

**Python + PyGObject (GTK4/libadwaita)** for the shell. Rationale:

- Fastest path to a polished, native Adwaita app; PyGObject is first-class on
  GNOME and trivial to Flatpak.
- The shell is UI + orchestration, not hot-path compute — Python is fine.
- Runtimes that need performance (Ruffle) are separate binaries/components, not
  Python.

(Rust + relm4 is a legitimate alternative if you want a single static binary and
are happy writing more GTK boilerplate. Python wins on iteration speed for a
solo/small project, which matches how you work.)

### Components

- **Catalog service** — fetches the remote manifest, validates it against the
  schema, caches it locally (`~/.var/app/uk.aaronworld.Yonderloft/cache/`), and
  falls back to the cached copy when offline. Refreshes on launch and on manual
  pull-to-refresh.
- **Status pinger** — for each visible card, performs a lightweight reachability
  check against the title's `status_url` (HEAD/GET with timeout), debounced and
  cached, to drive the online/unstable/offline badge. Runs async so the grid never
  blocks.
- **Runtime router** — the core logic. Reads a title's `runtime` field and launches
  it the right way (see §6).
- **Profile / data manager** — each title gets an isolated profile directory
  (cookies, local storage, Flash SOL files). Nothing leaks between servers. A
  per-game "Clear data" wipes only that title. Important given revival servers'
  spotty security history.

---

## 5. Catalog manifest

A single versioned JSON document. Hosted in-repo (`/catalog/manifest.json`) and
served raw; optionally mirrored on aaronworld.uk. Schema versioned so the app can
refuse manifests it doesn't understand.

```jsonc
{
  "schema_version": 1,
  "updated": "2026-06-22",
  "categories": [
    { "id": "penguins",      "name": "Penguins" },
    { "id": "pets_monsters", "name": "Pets & Monsters" },
    { "id": "fairy",         "name": "Fairy worlds" },
    { "id": "disney",        "name": "Disney" },
    { "id": "other",         "name": "Other" }
  ],
  "titles": [
    {
      "id": "moshi-monsters-rewritten",
      "name": "Moshi Monsters Rewritten",
      "category": "pets_monsters",
      "description": "A community recreation of the 2008 monster-adoption game...",
      "art": "art/moshi-monsters-rewritten.png",   // relative to catalog root
      "runtime": "ruffle",                          // ruffle | flash | web | client
      "servers": [
        {
          "name": "Main",
          "url": "https://www.moshimonstersrewritten.com/",
          "status_url": "https://www.moshimonstersrewritten.com/",
          "default": true
        }
      ],
      "ruffle": {
        "swf_url": null,            // null = let the page load its own SWF
        "flashvars": {},
        "force_scale": "showAll"
      },
      "tags": ["flash", "as2"],
      "notes": "No membership paywall, unlike the original.",
      "homepage": "https://www.moshimonstersrewritten.com/"
    },
    {
      "id": "new-club-penguin",
      "name": "New Club Penguin",
      "category": "penguins",
      "runtime": "flash",           // needs real Flash; Ruffle AS3 coverage incomplete
      "servers": [
        { "name": "Main", "url": "https://newcp.net/", "status_url": "https://newcp.net/", "default": true }
      ],
      "art": "art/new-club-penguin.png",
      "tags": ["flash", "as3"]
    },
    {
      "id": "waddle-forever",
      "name": "Waddle Forever",
      "category": "penguins",
      "runtime": "client",          // ships its own Electron client
      "client": {
        "kind": "appimage_or_flatpak",
        "source_url": "https://github.com/nhaar/Waddle-Forever/releases",
        "install_hint": "Single-player CP archive; downloads its own client."
      },
      "art": "art/waddle-forever.png",
      "tags": ["singleplayer", "archive"]
    }
  ]
}
```

### Field notes

- `runtime` is the routing key. Everything downstream keys off it.
- `servers[]` supports titles with multiple live servers (common for CP). The UI
  shows a picker; `default: true` is preselected.
- `status_url` is what the pinger hits. Separate from `url` because some games load
  the playable client from a different host than their status/landing page.
- `art` is referenced relative to the catalog root so art and manifest version
  together. The app caches fetched art.
- Adding a game = a JSON entry + an art file + a merge request. No app release.
  Community can contribute titles via MR.

---

## 6. Runtime routing

The router maps `runtime` to a launch strategy. This is the part that doesn't
exist anywhere else for Linux.

| `runtime` | Strategy | Used for | Notes |
|-----------|----------|----------|-------|
| `ruffle`  | Load the game in a WebKitGTK window with **Ruffle** (Rust/WASM Flash emulator) handling SWFs. | Most AS2 Flash (Bin Weevils, Moshi, older CP servers) | No insecure plugin. Ruffle is bundled (MIT/Apache). Preferred path. |
| `flash`   | Load in a **sandboxed Pepper Flash** runtime, fully isolated inside the Flatpak sandbox. | AS3 servers Ruffle can't yet run (e.g. some New CP) | The "use at your own risk" path. Sandboxed, isolated profile, network-restricted to the title's domains. |
| `web`     | Plain **WebKitGTK** window. | HTML5 rewrites / newer revivals | No emulation needed. |
| `client`  | Yonderloft **fetches/installs and wraps the game's own client** (e.g. Waddle Forever's Electron build) and launches it. | Titles that ship a native/Electron client | Yonderloft becomes a manager/installer, not a renderer. |

### Ruffle vs Flash decision

Ruffle's AS2 support is strong; AS3 is improving but incomplete. So:

1. Prefer `ruffle` wherever it actually works (verified per-title and recorded in
   the manifest `tags`).
2. Fall back to sandboxed `flash` only where Ruffle can't yet render the title.
3. As Ruffle's AS3 coverage improves, titles get flipped from `flash` to `ruffle`
   in the manifest — again, no app release needed.

**Action item before build:** verify current Ruffle AS3 coverage against Bin
Weevils Rewritten, Moshi Monsters Rewritten, and New Club Penguin specifically, so
each title's `runtime` is set correctly at launch.

### Sandboxing & safety

- Every game runs in its own isolated profile (cookies / storage / Flash SOLs).
- The `flash` runtime in particular is confined: no host filesystem access beyond
  its own profile, network scoped to the title's declared domains where feasible.
- A persistent, honest disclosure in the detail view: which runtime is in use,
  whether it's a legacy/unmaintained runtime, and a one-line security note for
  `flash` titles ("Legacy runtime — don't reuse passwords here").
- Per-game "Clear data."
- No telemetry.

---

## 7. Packaging & distribution

- **Flatpak (primary).** Sandboxing is a genuine feature here, not just
  convenience — it's the safe way to run legacy game runtimes. Target Flathub.
  App ID `uk.aaronworld.Yonderloft`. Ruffle bundled as part of the build (or a
  Flatpak extension). Finish-args scoped tightly (network, wayland/x11 socket,
  no broad filesystem).
- **AppImage (secondary).** For non-Flatpak distros.
- **MetaInfo** (`uk.aaronworld.Yonderloft.metainfo.xml`) with proper summary,
  description, categories (`Game;Launcher;`), screenshots, and release notes — all
  to pass Flathub quality checks.

### Flathub quality checklist (for store presence)

- Icon: SVG, square, no baked-in shadows/glows, follows GNOME app-icon style,
  sits correctly in the icon grid, ships a symbolic variant.
- Name ≤ 15 chars ("Yonderloft" = 10). ✓
- Screenshots: native window only, default theme, no edited promo graphics.
- Brand colors derived from the icon (amber + dusk).

---

## 8. The icon

Metaphor: **a glowing attic dormer window** — the loft, lit from within, seen at
dusk. Reads instantly at small sizes, unique, and ties the whole identity together
(matches the name, the empty state, and the loading motif).

- Full-color 128px following the GNOME app-icon template: simple geometric shapes,
  flat color on the straight window frame, a warm amber gradient only on the glow
  (curved/light surface), a ~4px darker "front" lip on the sill for the
  characteristic Adwaita depth, no external shadow.
- Symbolic 16px variant: the window outline in a single 2px stroke, monochrome.
- Built in App Icon Preview (`org.gnome.design.AppIconPreview`) + Inkscape with the
  GNOME HIG color palette loaded. Source `.svg` kept in `/data/icons/` in the repo.
- Optional: open a GNOME icon request for a community-polished version once the app
  targets Flathub / GNOME Circle.

---

## 9. Seed catalog (launch titles)

Confirmed-active revivals to ship in the first manifest:

**Penguins** — New Club Penguin, Club Penguin Journey, CPZero, Waddle Forever
(single-player archive).
**Pets & Monsters** — Moshi Monsters Rewritten, Bin Weevils Rewritten.
**Fairy worlds** — We The Pixies, Fairyabc (Pixie Hollow revivals).
**Disney** — MyVMK (Virtual Magic Kingdom), Toontown Rewritten.
**Other** — OpenFusion (FusionFall), Panfu (panfu.us), Nicktropolis Timewarp.

Stretch / verify-then-add: OpenFK (U.B. Funkeys), SpongeBob revivals, The Legend
of Pirates Online, Habbo Origins.

Each entry needs: confirmed-live server URL, correct `runtime` (Ruffle-verified
where possible), cover art, and a status endpoint.

---

## 10. Roadmap

**MVP (v0.1)**
- libadwaita shell: sidebar + card grid + detail view.
- Remote manifest fetch + cache + offline fallback.
- `ruffle` and `web` runtimes working.
- Isolated profiles + per-game clear data.
- Live status badges.
- Seed catalog with the Ruffle-able titles.
- Flatpak build.

**v0.2**
- `flash` sandboxed runtime for AS3-only titles.
- `client` runtime (Waddle Forever installer/wrapper).
- Favorites + Recent.
- Server picker for multi-server titles.

**v0.3**
- Flathub submission (icon, metainfo, screenshots, quality pass).
- Community catalog contributions via MR + a contribution guide.
- Discord Rich Presence (optional, off by default).
- AppImage build.

**Later**
- Per-title Ruffle version pinning.
- Network-level ad/tracker blocking inside game windows.
- Auto-flip titles `flash` → `ruffle` as coverage lands.
- Localization.

---

## 11. Repo layout

```
yonderloft/
├── data/
│   ├── icons/
│   │   ├── uk.aaronworld.Yonderloft.svg          # full-color app icon
│   │   └── symbolic/uk.aaronworld.Yonderloft-symbolic.svg
│   ├── uk.aaronworld.Yonderloft.desktop
│   ├── uk.aaronworld.Yonderloft.metainfo.xml
│   └── uk.aaronworld.Yonderloft.gschema.xml      # settings
├── catalog/
│   ├── manifest.json                              # the remote catalog (served raw)
│   ├── schema.json                                # JSON Schema for validation
│   └── art/                                       # cover art per title
├── src/
│   └── yonderloft/
│       ├── __init__.py
│       ├── application.py                         # AdwApplication
│       ├── window.py                              # main window, split view
│       ├── views/                                 # grid, detail, game window
│       ├── catalog.py                             # fetch/validate/cache manifest
│       ├── status.py                              # async status pinger
│       ├── profiles.py                            # per-title data isolation
│       └── runtimes/
│           ├── router.py
│           ├── ruffle.py
│           ├── flash.py
│           ├── web.py
│           └── client.py
├── build-aux/
│   └── flatpak/uk.aaronworld.Yonderloft.json      # Flatpak manifest
├── po/                                            # translations
├── meson.build
├── README.md
├── LICENSE
└── CONTRIBUTING.md                                # how to add a title
```

---

## 12. Legal / ethical posture

- Yonderloft bundles only open-source runtimes (Ruffle: MIT/Apache). It does not
  bundle or redistribute any rights-holder's game assets.
- It links to and connects to community revival servers; it does not host them.
  Game content is fetched at runtime from those servers, as a browser would.
- Clear in-app and README disclaimer: independent project, not affiliated with or
  endorsed by Disney, Mind Candy, 55pixels, or any revival project; no game content
  is hosted or distributed by Yonderloft.
- A note that revival servers are run by third parties of varying trustworthiness,
  with a reminder not to reuse passwords — backed by the per-title isolation and
  the `flash` security disclosure.ou to get started with GitLab, here's a list of recommended next steps.

Already a pro? Just edit this README.md and make it your own. Want to make it easy? [Use the template at the bottom](#editing-this-readme)!

## Add your files

* [Create](https://docs.gitlab.com/user/project/repository/web_editor/#create-a-file) or [upload](https://docs.gitlab.com/user/project/repository/web_editor/#upload-a-file) files
* [Add files using the command line](https://docs.gitlab.com/topics/git/add_files/#add-files-to-a-git-repository) or push an existing Git repository with the following command:

```
cd existing_repo
git remote add origin https://gitlab.com/aaronateataco/yonderloft.git
git branch -M main
git push -uf origin main
```

## Integrate with your tools

* [Set up project integrations](https://gitlab.com/aaronateataco/yonderloft/-/settings/integrations)

## Collaborate with your team

* [Invite team members and collaborators](https://docs.gitlab.com/user/project/members/)
* [Create a new merge request](https://docs.gitlab.com/user/project/merge_requests/creating_merge_requests/)
* [Automatically close issues from merge requests](https://docs.gitlab.com/user/project/issues/managing_issues/#closing-issues-automatically)
* [Enable merge request approvals](https://docs.gitlab.com/user/project/merge_requests/approvals/)
* [Set auto-merge](https://docs.gitlab.com/user/project/merge_requests/auto_merge/)

## Test and Deploy

Use the built-in continuous integration in GitLab.

* [Get started with GitLab CI/CD](https://docs.gitlab.com/ci/quick_start/)
* [Analyze your code for known vulnerabilities with Static Application Security Testing (SAST)](https://docs.gitlab.com/user/application_security/sast/)
* [Deploy to Kubernetes, Amazon EC2, or Amazon ECS using Auto Deploy](https://docs.gitlab.com/topics/autodevops/requirements/)
* [Use pull-based deployments for improved Kubernetes management](https://docs.gitlab.com/user/clusters/agent/)
* [Set up protected environments](https://docs.gitlab.com/ci/environments/protected_environments/)

***

# Editing this README

When you're ready to make this README your own, just edit this file and use the handy template below (or feel free to structure it however you want - this is just a starting point!). Thanks to [makeareadme.com](https://www.makeareadme.com/) for this template.

## Suggestions for a good README

Every project is different, so consider which of these sections apply to yours. The sections used in the template are suggestions for most open source projects. Also keep in mind that while a README can be too long and detailed, too long is better than too short. If you think your README is too long, consider utilizing another form of documentation rather than cutting out information.

## Name
Choose a self-explaining name for your project.

## Description
Let people know what your project can do specifically. Provide context and add a link to any reference visitors might be unfamiliar with. A list of Features or a Background subsection can also be added here. If there are alternatives to your project, this is a good place to list differentiating factors.

## Badges
On some READMEs, you may see small images that convey metadata, such as whether or not all the tests are passing for the project. You can use Shields to add some to your README. Many services also have instructions for adding a badge.

## Visuals
Depending on what you are making, it can be a good idea to include screenshots or even a video (you'll frequently see GIFs rather than actual videos). Tools like ttygif can help, but check out Asciinema for a more sophisticated method.

## Installation
Within a particular ecosystem, there may be a common way of installing things, such as using Yarn, NuGet, or Homebrew. However, consider the possibility that whoever is reading your README is a novice and would like more guidance. Listing specific steps helps remove ambiguity and gets people to using your project as quickly as possible. If it only runs in a specific context like a particular programming language version or operating system or has dependencies that have to be installed manually, also add a Requirements subsection.

## Usage
Use examples liberally, and show the expected output if you can. It's helpful to have inline the smallest example of usage that you can demonstrate, while providing links to more sophisticated examples if they are too long to reasonably include in the README.

## Support
Tell people where they can go to for help. It can be any combination of an issue tracker, a chat room, an email address, etc.

## Roadmap
If you have ideas for releases in the future, it is a good idea to list them in the README.

## Contributing
State if you are open to contributions and what your requirements are for accepting them.

For people who want to make changes to your project, it's helpful to have some documentation on how to get started. Perhaps there is a script that they should run or some environment variables that they need to set. Make these steps explicit. These instructions could also be useful to your future self.

You can also document commands to lint the code or run tests. These steps help to ensure high code quality and reduce the likelihood that the changes inadvertently break something. Having instructions for running tests is especially helpful if it requires external setup, such as starting a Selenium server for testing in a browser.

## Authors and acknowledgment
Show your appreciation to those who have contributed to the project.

## License
For open source projects, say how it is licensed.

## Project status
If you have run out of energy or time for your project, put a note at the top of the README saying that development has slowed down or stopped completely. Someone may choose to fork your project or volunteer to step in as a maintainer or owner, allowing your project to keep going. You can also make an explicit request for maintainers.

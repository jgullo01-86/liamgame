# Civilization Deluxe - Claude Code Project Notes

## Overview
A 4X strategy game built with Python + Ursina (Panda3D). Isometric hex-based map with AI-generated terrain textures and unit sprites, orthographic camera, turn-based gameplay with AI opponents.

## How to Run
```bash
cd ~/liamgame && python3 main.py
```
Must run from foreground terminal (macOS blocks GUI windows from background processes).

## Architecture

### Entry Point
- `main.py` — `GameApp` class, main menu → game lifecycle, input routing, ESC priority chain

### Models (`src/models/`)
- `game_state.py` — `GameState`, `Player`, `Civilization`, turn logic, combat, movement, victory, `_auto_select_next_unit()`
- `unit.py` — `Unit`, `UnitType`, `UnitStats`, A* pathfinding, Dijkstra movement range
- `city.py` — `City`, `ProductionType`, `PRODUCTION_ITEMS`, yields
- `map.py` — `GameMap`, `Tile`, hex grid, terrain types

### Views (`src/views/`)
- `game_view_3d.py` — `GameView3D`, hex map rendering, minimal 3D decorations (mountains/forest only), water shimmer, hover/movement overlays
- `hex_mesh.py` — `HexTile3D`, UV-mapped textured hex meshes with vertex color bevel (dark corners → bright center), texture cache
- `unit_renderer.py` — `Unit3D` (billboard sprites with 2-frame walk animation), `City3D` (billboard sprites with 3 population tiers), `UnitManager3D`
- `camera_controller.py` — `OrbitCamera`, orthographic projection, WASD pan, Q/E rotate, right-drag orbit, middle-drag pan, scroll zoom, C reset
- `ui_overlay.py` — `UIOverlay`, HUD top bar, unit info panel, production picker, help overlay, escape menu, notifications
- `main_menu.py` — `MainMenu`, title screen with New Game / How to Play / Quit

### Controllers (`src/controllers/`)
- `ai_controller.py` — AI opponent logic

### Utils (`src/utils/`)
- `hex_utils.py` — `HexCoord`, hex math, `hex_to_world_3d()`, `hex_corners_3d()`

### Config
- `config.py` — All constants: window, map, hex, camera, terrain colors/heights, combat, victory
- `assets/data/civilizations.json` — 15 civilizations with colors, leaders, city names

### Assets
- `assets/textures/` — AI-generated terrain textures (grassland, forest, ocean, coast, mountains, desert, plains, hills)
- `assets/textures/units/` — AI-generated unit sprites (warrior, settler, scout, archer, horseman × 2 frames each)
- `assets/textures/cities/` — AI-generated city sprites (village, town, city for 3 population tiers)

## Visual System — IMPORTANT

### Terrain: UV-Mapped Textures
- Hex tiles use **AI-generated PNG textures** applied via UV mapping (NOT vertex colors for top face)
- Textures cached at class level in `HexTile3D._texture_cache` to avoid loading 1200× per map
- `TERRAIN_TEXTURES` dict in `hex_mesh.py` maps terrain types to texture paths
- Vertex colors on top face are WHITE (inner ring) → DARK GRAY (outer corners) for bevel border effect
- Vertex colors MULTIPLY with texture in Panda3D, creating darkened hex edges
- Side/bottom faces still use rgb_tuple vertex colors (barely visible with flat tiles)
- `setLightOff()` on all hex tiles so textures render at full brightness

### Units: Billboard Sprites
- Units are flat `model='quad'` billboards with `billboard=True` (always face camera)
- `UNIT_SPRITES` dict maps UnitType to (frame1_path, frame2_path) tuples
- Sprites cached at class level in `Unit3D._sprite_cache`
- `set_transparency(True)` required for transparent sprite backgrounds
- White backgrounds removed from sprites via Pillow (near-white → alpha=0)
- Walk animation: toggles between frame 1 and frame 2 every 0.18s when `_is_moving`
- Idle: frame 1 with subtle sine-wave bob
- Player color shown via base disk on ground (circle model under sprite)
- Health bar positioned above sprite at y=3.2
- Current sprite scale: (6.75, 6.75), position: (0, 3.0, 0) relative to parent

### Cities: Billboard Sprites (3 Population Tiers)
- `City3D` uses billboard sprites like units
- `CITY_SPRITES` dict maps tier names to PNG paths in `assets/textures/cities/`
- 3 tiers: village (pop 1-2), town (pop 3-4), city (pop 5+)
- Sprite auto-upgrades when population crosses tier thresholds
- Player color shown via larger base disk (scale 2.5 vs 1.5 for units)
- Name label + population badge + capital star above sprite

### Camera: Orthographic Isometric
- `camera.orthographic = True` in `_update_camera_position()`
- `camera.fov` controls zoom (not distance) in ortho mode
- Fixed orbit distance of 100 units (far enough to see everything)
- Default angle: 55° from horizontal
- Camera does NOT auto-pan on unit auto-select (was jarring) — only pans on explicit Space key

### Hex Tile Config (flat tiles)
- `HEX_3D_HEIGHT = 0.08` (paper-thin prisms)
- Terrain heights nearly flat: ocean -0.08, mountains 0.12, everything else ≈ 0
- `y_scale = 1.0` (no Y exaggeration)

## Critical Ursina 7 / Panda3D Gotchas

### Color Normalization (MAJOR BUG SOURCE)
- `color.rgb(r, g, b)` stores RAW 0-255 values. Panda3D expects 0-1 range.
- For **UI elements** (parent=camera.ui): use `_c(r, g, b, a=255)` helper → `Color(r/255, g/255, b/255, a/255)`
- For **3D entities**: use `_color_entity(entity, color_obj)` which auto-normalizes
- Both helpers are defined in their respective files. ALWAYS use them.

### Z-ordering in UI
- `parent=camera.ui`: positive z = behind, negative z = in front
- Panels at z=0.05 (bg) and z=0.04 render BEHIND text at z=0

### setLightOff()
- Hex tiles: YES (so textures + vertex colors show at full brightness)
- Unit sprites + overlays (health bars, selection rings, base disks): YES
- 3D decorations (mountain peaks, forest canopy bumps): NO (respond to scene lighting)

### Billboard Sprite Transparency
- Must call `entity.set_transparency(True)` after creating the sprite entity
- White backgrounds in AI-generated images must be removed (Pillow: near-white pixels → alpha=0)

### animate_position() Bug
- Calling `animate_position()` every frame RESTARTS the animation, so unit never arrives
- Fix: track `_move_target`, only call animate when target hex actually changes
- Idle bob (`self.y = ...`) conflicts with animation — skip bob when `_is_moving`

### Screenshots
- macOS `screencapture` cannot capture Panda3D/OpenGL windows
- Use `base.win.saveScreenshot()` for internal screenshots

## Current Features

### Visual
- Orthographic isometric camera (CTP-style flat 2D look)
- AI-generated terrain textures on every hex tile
- AI-generated unit billboard sprites with 2-frame walk animation
- UV-mapped hex meshes with bevel edge effect (dark corners)
- Sky blue atmosphere + exponential fog
- Water shimmer (sine wave brightness ripple)
- Minimal 3D decorations (mountain peaks, forest canopy bumps only)
- Green/red circle overlays for movement/attack range
- Player-colored base disks under units
- Unit info/action panel on left side when unit selected

### Gameplay
- 15 civilizations (Egypt, Rome, Greece, China, England, France, Japan, Persia, Mongolia, Aztec, America, India, Zulu, Russia, Brazil)
- 5 unit types: Warrior, Settler, Scout, Archer, Horseman
- City founding, production queue, population growth
- Dijkstra movement range, A* pathfinding
- Combat with terrain defense bonuses, counter-damage, ranged attacks
- AI opponents
- Score/elimination victory

### Controls
- WASD/Arrows: Pan camera
- Q/E: Rotate camera
- Right-drag: Orbit camera
- Middle-drag: Pan camera
- Scroll: Zoom in/out
- C: Reset camera angle/zoom
- Left click: Select / Move / Attack
- B: Found city (settler)
- Space: Next unit (pans camera to it)
- Enter: End turn
- H/F1: Help overlay
- ESC: Deselect → Pause menu

## Key Patterns

### AI-Generated Asset Workflow
1. Give user prompts for AI image generator (Midjourney/DALL-E)
2. User generates images, saves to Desktop
3. Copy to `assets/textures/` (or `assets/textures/units/`)
4. Remove white backgrounds with Pillow if needed
5. Wire into game via texture cache + UV mapping (terrain) or billboard sprites (units)

### Unit movement flow
1. Left-click unit → `game_state.select_unit()`
2. `GameView3D._update_movement_range()` shows green/red overlays
3. Left-click green tile → `game_state.handle_hex_click()` → `move_unit()` → `unit.move_to()`
4. `Unit3D.update_position()` — only calls `animate_position` when target hex changes
5. Walk animation cycles frames while `_is_moving`
6. When movement exhausted, `_auto_select_next_unit()` fires (camera stays put)

### Production flow
1. Click city → `UIOverlay.show_production_picker()`
2. Select item → `game_state.set_city_production()`
3. Each turn, `city.process_turn()` accumulates production → spawns unit when complete

## What To Do Next

### High Priority
- **Sound effects** — No audio. Add click, move, attack, turn-end sounds
- **Minimap** — Hard to navigate 40x30 map without one

### Medium Priority
- **Tech tree / research system** — Core Civ mechanic, not implemented
- **Better AI** — Currently very basic
- **Save/Load** — Can't save games
- **More unit types** — Only 5 currently

### Lower Priority
- **Diplomacy between civilizations**
- **Civilization-specific abilities** (data structure exists in JSON but `abilities: {}` for all)
- **Terrain improvements** (farms, mines, roads)

## Utility Files (can be deleted)
- `hex_style_tester.py` — Hex style comparison tool (used during development, no longer needed)
- `generate_textures.py` — Pillow-based texture generator (replaced by AI-generated textures)

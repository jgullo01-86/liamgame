# Civilization Deluxe

A turn-based 4X strategy game built with Python and Pygame.

## Features

### Phase 1 - Foundation
- **Hex-based map** with procedurally generated terrain
- **Terrain types**: Grassland, Plains, Desert, Hills, Mountains, Forest, Coast, Ocean
- **Unit movement** with terrain-based movement costs
- **Camera panning** with arrow keys or WASD
- **Turn-based gameplay** with End Turn button

### Phase 2 - Cities & Settlers
- **15 Historical Civilizations** with unique leaders and city names
- **Settlers** can found new cities on the map
- **City founding** with custom naming for your capital
- **City spacing** - cities must be at least 4 hexes apart
- **City production** - build Warriors or new Settlers
- **City growth** - food surplus accumulates for population growth
- **Tile yields** - cities work nearby tiles for food, production, and gold

## Installation

1. Make sure you have Python 3.11+ installed
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Running the Game

```bash
python main.py
```

## Controls

| Key/Action | Function |
|------------|----------|
| Arrow Keys / WASD | Pan camera |
| Left Click | Select unit/city or move unit |
| ESC | Deselect |
| B | Found city (when Settler selected) |
| Space | Select next unit |
| Enter | End turn |

## Civilizations

| Civilization | Leader |
|--------------|--------|
| Egypt | Cleopatra |
| Rome | Julius Caesar |
| Greece | Alexander |
| China | Qin Shi Huang |
| England | King George III |
| France | Napoleon |
| Japan | Oda Nobunaga |
| Persia | Cyrus |
| Mongolia | Genghis Khan |
| Aztec | Montezuma |
| America | Abraham Lincoln |
| India | Gandhi |
| Zulu | Shaka |
| Russia | Peter the Great |
| Brazil | Pedro II |

## Tile Yields

| Terrain   | Food | Production | Gold |
|-----------|------|------------|------|
| Grassland | 2    | 0          | 0    |
| Plains    | 1    | 1          | 0    |
| Desert    | 0    | 0          | 1    |
| Hills     | 0    | 2          | 0    |
| Forest    | 1    | 1          | 0    |
| Coast     | 1    | 0          | 1    |
| Ocean     | 1    | 0          | 0    |
| Mountains | -    | -          | -    |

## Movement Costs

| Terrain   | Cost       |
|-----------|------------|
| Grassland | 1          |
| Plains    | 1          |
| Desert    | 1          |
| Coast     | 1          |
| Hills     | 2          |
| Forest    | 2          |
| Mountains | Impassable |
| Ocean     | Impassable |

## Project Structure

```
civilization_deluxe/
├── main.py              # Entry point
├── config.py            # Game constants
├── requirements.txt     # Dependencies
├── assets/data/
│   ├── terrain.json     # Terrain definitions
│   └── civilizations.json # Civ data
└── src/
    ├── models/          # Game data (MVC Model)
    │   ├── game_state.py
    │   ├── map.py
    │   ├── unit.py
    │   └── city.py
    ├── views/           # Rendering (MVC View)
    │   ├── game_view.py
    │   └── ui_elements.py
    ├── controllers/     # Game logic (MVC Controller)
    │   ├── game_controller.py
    │   └── input_handler.py
    └── utils/
        └── hex_utils.py # Hex grid utilities
```

## How to Play

1. **Start the game** - You begin with a Settler unit
2. **Found your capital** - Select the Settler, find a good spot, press B or click "Found City"
3. **Name your city** - Enter a name for your capital city
4. **Set production** - Click the city to open the city panel, choose what to build
5. **Expand** - Build more Settlers to found additional cities
6. **Build an army** - Produce Warriors to explore and defend

## Upcoming Features (Phase 3+)

- Technology research
- Combat system
- Hero units with special abilities
- Multiple AI players
- Victory conditions

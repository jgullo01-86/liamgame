#!/usr/bin/env python3
"""
Simple test to verify 3D rendering works
"""

from ursina import *

app = Ursina()

# Tall cubes in different colors - unlit so colors show properly
Entity(model='cube', color=color.red, position=(0, 1, 0), scale=(1, 2, 1), unlit=True)
Entity(model='cube', color=color.green, position=(3, 1, 0), scale=(1, 2, 1), unlit=True)
Entity(model='cube', color=color.blue, position=(-3, 1, 0), scale=(1, 2, 1), unlit=True)
Entity(model='cube', color=color.yellow, position=(0, 1, 3), scale=(1, 2, 1), unlit=True)
Entity(model='cube', color=color.orange, position=(0, 1, -3), scale=(1, 2, 1), unlit=True)

# Gray floor cube
Entity(model='cube', color=color.light_gray, position=(0, -0.5, 0), scale=(20, 1, 20), unlit=True)

# Use the default editor camera for testing
EditorCamera()

print("You should see: RED cube center, GREEN right, BLUE left, YELLOW back, ORANGE front")
print("GRAY floor underneath")
print("Use right-click drag to rotate view, scroll to zoom")

app.run()

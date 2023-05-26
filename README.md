# LEO Alpha Paint
[Blender](https://www.blender.org/) add-on for optimally working with vertex colors on game models. 

Features instant button for quick game-ready vertex COLOR exports, fast vertex color isolation and paint, vertex color optimized shading, sampling and selection of vertices with specific colors, vertex-color-integrated color palette tools, and vertex color layer transfer tools.
> Blender version 2.83 - 3.5+

<a name="navigation"></a>
## Navigation
1. [Installation](#installation)
2. [Instant COLOR for game-ready exports](#instant)
3. [Vertex colors in AGMG](#vertexcolors)
4. [Isolation and paint](#isolationpaint)
5. [Optimized shading](#shading)
6. [Sampling and selection](#selectionshading)
7. [Color palette](#colorpalette)
8. [Layer transfer tools](#layertransfer)

<a name="installation"></a>
## Installation
1. Download release from https://github.com/HummyR/LEOAlphaPaint/releases (source code: https://github.com/HummyR/LEOAlphaPaint/blob/main/LEOAlphaPaint.py)
2. In Blender, open the Preferences window (Edit>Preferences) and select the Add-ons tab.
3. Press the 'Install...' button and select the python file you downloaded.
4. Enable the add-on and save preferences. If you want to uninstall the addon, simply disable it in preferences and then delete the python file.

<img src="https://github.com/HummyR/LEOAlphaPaint/blob/1e71bb244406272443f1b43f914ce4d3ef03fa8d/img/Screenshot%202023-05-25%20233151.png" width="640">

<a name="instant"></a>
## Instant COLOR for game-ready exports

<a name="vertexcolors"></a>
## Vertex colors in AGMG
Primarily/intended to be used to help make Anime Game mods at AGMG: https://discord.gg/agmg. Notes about the specific vertex color channels:

R = Ambient Occlusion (Higher = no occlude, Lower = Ambient Occlusion)
G = Shadow Smoothing (Higher = Sharper, Lower = Smoother)
B = Outline z/depth-index (Higher = behind, Lower = in front)
A = Outline thickness (Higher = thicker, Lower = less width)

Standard values:
R = 1    , lower this to give usually shaded areas ambient occlusion

G = 0.502, soft clothing tend to have smoother values between 0.251 - 0.2

B = 0.502, (raise this value to push outlines back in the Z/depth-axis relative to the model, but usually no need to change)

A = 0.502, generally: exposed hands and feet are 0.4, concave edges have low values, areas with a lot of small details have 0.302-0.106 (for example, a small spike whose outline gets thinner towards the tip), eyes are 0

<a name="isolationpaint"></a>
## Isolation and paint

<a name="shading"></a>
## Optimized shading

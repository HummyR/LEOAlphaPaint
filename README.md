# LEO Alpha Paint
[Blender](https://www.blender.org/) add-on for optimally working with vertex colors on game models. 

Features instant button for quick game-ready vertex COLOR exports, fast vertex color isolation and paint, vertex color optimized shading, sampling and selection of vertices with specific colors, vertex-color-integrated color palette tools, and vertex color layer transfer tools. Almost every button can be assigned a shortcut via right-click.
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
1. Download release from https://github.com/HummyR/LEOAlphaPaint/releases ([source code](https://github.com/HummyR/LEOAlphaPaint/blob/main/LEOAlphaPaint.py))
3. In Blender, open the Preferences window (Edit>Preferences) and select the Add-ons tab.
4. Press the 'Install...' button and select the python file you downloaded.
5. Enable the add-on and save preferences. If you want to uninstall the addon, simply disable it in preferences and then delete the python file.
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/1e71bb244406272443f1b43f914ce4d3ef03fa8d/img/Screenshot%202023-05-25%20233151.png" width="480">
</p>

<a name="instant"></a>
## Instant COLOR for game-ready exports
Select an object, go into vertex mode, open the right side panel using the + button or press N on a keyboard, click on the Vertex Paint tab, and finally click "Quick Optimize COLOR" and OK to be instantly finished!
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-26%20001849.png" width="480">
</p>

<a name="vertexcolors"></a>
## Vertex colors in AGMG
Primarily/intended to be used to help make Anime Game mods at AGMG: https://discord.gg/agmg. Notes about the specific vertex color channels:

- R = Ambient Occlusion (Higher = no occlude, Lower = Ambient Occlusion)
- G = Shadow Smoothing (Higher = Sharper, Lower = Smoother)
- B = Outline z/depth-index (Higher = behind, Lower = in front)
- A = Outline thickness (Higher = thicker, Lower = less width)

Standard values:

- R = 1, lower this to give usually shaded areas ambient occlusion
- G = 0.502, soft clothing tend to have smoother values between 0.251 - 0.2
- B = 0.502, (raise this value to push outlines back in the Z/depth-axis relative to the model, but usually no need to change)
- A = 0.502, generally: exposed hands and feet are 0.4, concave edges have low values, areas with a lot of small details have 0.302-0.106 (for example, a small spike whose outline gets thinner towards the tip), eyes are 0

<a name="isolationpaint"></a>
## Isolation and paint
Special paint fill button that does not cause the alpha layer to turn white! You can right click the button to assign a shortcut instead of using the old fill shortcut. It works with selection masking and isolated channels. Be sure to disable "affect alpha" before painting so that the built-in blender painting tool dont create streaks of white in the alpha channel.
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234155.png" width="350">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234218.png" width="400">
</p>

Special thanks to [andyp123](https://github.com/andyp123/blender_vertex_color_master), Bartosz Styperek, and RylauChelmi for the gradient tool. Really useful for drawing smooth linear/circular gradients. You might use this if you are creating tapering outlines that get thinner from edge to tip.
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234815.png" width="480">
</p>
Hover over an isolation channel button to see what that specific channel does to the in-game model. Channel isolation workflow has been optimized to make it more comfortable to work with vertex colors!
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234557.png" width="480">
</p>

<a name="shading"></a>
## Optimized shading
There is a "Shade FLAT" button at the top, below "Quick Optimize COLOR", and another button beside it called "affect alpha". Be sure to enable "Shade FLAT" so that you can accurately sample vertex colors with the built-in paint tool ("S" is the keyboard shortcut to for the color-picker tool). Also be sure to disable "affect alpha" so that you can make sure you dont accidently paint the alpha layer.

<a name="selectionshading"></a>
## Sampling and selection
There are 2 ways to sample: 
- select a vertex and click "Sample selected colors" (this will sample your selected colors in the selection mask for their average color)
- "Palette vertex colors" button will add all the selected colors to a new color palette (or every color in the mesh if none are selected, dont worry it isn't laggy)

There are 2 ways to select, both are using the "Select" button with either the "Brush" or "Palette" mode
- "Brush" mode will select all vertices within an error margin of your primary brush color. (error margin can be changed in bottom left popup box)
- "Palette" mode will select all vertices within an error margin of all the colors in your active palette. (be careful to not have 500+ colors or smth as that will greatly increase calculation time)
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234030.png" width="600">
</p>

<a name="colorpalette"></a>
## Color palette
A special feature that allows you to quickly store and retreive vertex colors, all integrated into the add-on. You can sample vertex colors from the mesh onto your palette, create a new palette, and easily delete old palettes (there is no easy button to do this as far as i have seen in the default blender interface).
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20235024.png" width="480">
</p>

<a name="layertransfer"></a>
## Layer transfer tools
If you ever need to work with multiple color layers, which I doubt you will but just in case... I have added some channel/layer transfer and blending tools. It will take a source layer's channels and transfer them onto the active (isolated) layer, with blending modes or a factor layer to determine strength of the blending. The default Blend: Mix/Factor: None will give a simple transfer of channnels.
<p align="middle">
  <img src="https://github.com/HummyR/LEOAlphaPaint/blob/8ab0fd1ddd77a115ff45def01679610f49aa13bf/img/Screenshot%202023-05-25%20234651.png" width="480">
</p>
The add-on currently only supports mono to multi, multi to mono, mono to mono, and same multi to multi channel transfers. It does not support different multi channel to multi channel transfers (like RG to GBA).

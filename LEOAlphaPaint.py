# Foundational script by LeoMods (https://github.com/leotorrez) and Blue (https://github.com/SharpCyan)
# Edits by HummyR (https://github.com/HummyR) (tool developer at https://discord.gg/agmg)
# Credits to Gradient tool by andyp123 (https://github.com/andyp123/blender_vertex_color_master), Bartosz Styperek, and RylauChelmi, adapted and updated for alpha paint

# Primarily/intended to be used to help make Anime Game mods at https://discord.gg/agmg

# R = Ambient Occlusion (Higher = no occlude, Lower = Ambient Occlusion)

# G = Shadow Smoothing (Higher = Sharper, Lower = Smoother)

# B = Outline z/depth-index (Higher = behind, Lower = in front)

# A = Outline thickness (Higher = thicker, Lower = less width)

# Standard values:

#     R = 1    , lower this to give usually shaded areas ambient occlusion
#     G = 0.502, soft clothing tend to have smoother values between 0.251 - 0.2
#     B = 0.502, (raise this value to push outlines back in the Z/depth-axis relative to the model, but usually no need to change)
#     A = 0.502, generally: exposed hands and feet are 0.4, concave edges have low values, areas with a lot of small details have 0.302-0.106 (for example, a small spike whose outline gets thinner towards the tip), eyes are 0

import bpy
import bmesh
from mathutils import Color, Vector, Matrix
import gpu
from gpu_extras.batch import batch_for_shader
from bpy_extras import view3d_utils
from math import fmod

bl_info = {
    "name": "LEOAlphaPaint",
    "blender": (3, 5, 1),
    "author": "LeoMods (https://github.com/leotorrez), Blue, and HummyR (https://github.com/HummyR)",
    "location": "Vertex Paint",
    "description": "Paint Vertex colors for Anime Game mods at https://discord.gg/agmg. Credits to Gradient tool by andyp123 (https://github.com/andyp123/blender_vertex_color_master), Bartosz Styperek, and RylauChelmi, adapted and updated for alpha paint. Tested to work on blender version 2.83 and above",
    "category": "Paint",
    "tracker_url": "https://github.com/HummyR",
}

FL = [0,1,2]

channel_list = ['R','G','B','A']

keyName = "_viewLayer_generated_"

blending_modes = [

            ('', 'Normal', ''), #---------------------------------------------
            
            ('MIX', "Mix", "S"),
            ('PAINTMIX', "Paint Mix", "sqrt(S^2+D^2)"),
            ('ALPHAOVER','Alpha Over', 'S*(sA): basically Mix with source alpha layer factor'),
            
            ('','Light',''), #------------------------------------------------
            
            ('ADD', "Add", "S+D"),
            ('LIGHTEN', "Lighten","max(S,D)"),
            ('COLORDODGE','Color Dodge','D/(1-S)'),
            ('SCREEN','Screen','1-(1-S)*(1-D)'),
            
            ('','Dark',''), #-------------------------------------------------
            
            ('DARKEN', "Darken", "min(S,D)"), 
            ('MUL', "Multiply", "S*D"),
            ('LINEARBURN', 'Linear Burn','S+D-1'), 
            ('COLORBURN', 'Color Burn','1-(1-D)/S'),
            
            ('','Cancel',''), #-----------------------------------------------
            
            ('SUB', "Subtract", "D-S"),
            ('DIV', "Divide", "D/S"),

            ('','Contrast',''), #---------------------------------------------

            ('OVERLAY','Overlay','Multiply(dark) + Screen(light), depending on Source Layer value'),
            ('HARDLIGHT','Hard Light','Multiply(dark) + Screen(light), depending on Active Layer value'),
            ('SOFTLIGHT','Soft Light','(1-2D)S^2+2D*S'),

            ('','Component',''), #-------------------------------------------
            
            ('HUE', "Hue", "S.h"),
            ('SATURATION', "Saturation", "S.s"),
            ('COLOR', "Color", "S.sh"),
            ('VALUE', "Value", "S.v"),
        ]

class PaintAlphaPropertyGroup(bpy.types.PropertyGroup):

    one_layer_isolate : bpy.props.BoolProperty(
        name='Isolate one layer',
        description='Only isolate one layer at a time. \nRight click to assign shortcut',
        default=True
    )

    enable_transfer_tools : bpy.props.BoolProperty(
        name="Enable Transfer Tools",
        default=False,
        description="Show/hide tools for transfering/blending data between vertex color layers/channels. \nRight click to assign shortcut"
    )

    enable_indiscriminate_fill : bpy.props.BoolProperty(
        name="allow use ALL vertices",
        description="WARNING: this will allow you to paint all verticies at the click of one button. \nRight click to assign shortcut. Can be undone with Control + Z",
        default=True
    ) 

    isolated_Channel : bpy.props.StringProperty(
        name="isolated_Channel",
        default=""
    )

    blend_mode : bpy.props.EnumProperty(
        name='Blend type',
        items=blending_modes,
        default="MIX",
    )

    def vcol_layer_items(self, context):
        obj = context.active_object
        mesh = obj.data
        try: vcollayers = mesh.vertex_colors
        except: vcollayers = mesh.attributes.color
        items = [] if vcollayers is None else [(vcol.name, vcol.name, "") for vcol in vcollayers]
        return items

    def vcol_layer_items_factor(self, context):
        obj = context.active_object
        mesh = obj.data
        try: vcollayers = mesh.vertex_colors
        except: vcollayers = mesh.attributes.color
        items = [('NONE','None','')] 
        if vcollayers is not None:
            items.extend([(vcol.name, vcol.name, "") for vcol in vcollayers])
        return items

    src_vcol: bpy.props.EnumProperty(
        name="Source",
        items=vcol_layer_items,
        description="Source vertex color layer",
    )

    factor_vcol: bpy.props.EnumProperty(
        name="Factor",
        description="Factor color channel. 0-1 RGBA channels corresponds to how much the blend mode will be applied",
        items=vcol_layer_items_factor,
    )

    factor_slider : bpy.props.FloatProperty(
        name="Mix",
        description="Factor amount",
        default=1,
        max=1,
        min=0,
    )

    src_ch: bpy.props.BoolVectorProperty(
        name="Source Channel",
        description="Source color channel. Click and drag to enable/disable multiple simultaneously",
        size=4,
        default=(False,False,False,False),
    )

    past_shading : bpy.props.StringProperty(default = 'UnInitialized')
    space_shader_storage : bpy.props.StringProperty(default = 'VERTEX')

    select_color_mode : bpy.props.EnumProperty(
        name='Select mode',
        items=[
            ('BRUSH', 'Brush', 'Primary brush color'),
            ('PALETTE', 'Palette', 'All colors in active palette')
        ],
        default='BRUSH'
    )

def refreshMesh(bm, obj):
    bm.to_mesh(obj)
    bm.free()
    obj.update()

def findActiveColorLayer(color_data, obj):
    try: color_layer = color_data[obj.vertex_colors.active.name]
    except: 
        try: color_layer = color_data[obj.attributes.active_color.name]
        except: color_layer = color_data.active
    return color_layer

def trySetActiveVC(obj, basename):
    try: obj.vertex_colors.active = obj.vertex_colors[basename]
    except: 
        try: obj.attributes.active_color = obj.attributes[basename]
        except: pass

def clamp01(inp):
    return max(0, min(inp, 1))

def blendChannels(self,context, settings, obj, bm, color_data):
    
    blend_mode = self.blend_mode
    factor = self.factor_vcol
    factor_slider = self.factor_slider
    dstname = self.dst_vcol
    dst = color_data[dstname]
    src = color_data[self.src_vcol]

    src_ch = [i for i, x in enumerate(self.src_ch) if x]
    if not src_ch: src_ch = [0,1,2]

    settings.isolated_Channel = dstname.split(keyName)[1] if keyName in dstname else ""
    isolated_channels = [int(x) for x in settings.isolated_Channel if x]
    alpha_mode = bool(3 in isolated_channels)
    if not isolated_channels or alpha_mode: isolated_channels = [0,1,2]

    if blend_mode == 'ALPHAOVER':
        src_ch = [x for x in src_ch if x!=3]
        isolated_channels = [x for x in isolated_channels if x!=3]

    src_count = len(src_ch)
    iso_count = len(isolated_channels)

    referenceColor = color_data.new()
    referenceColor.copy_from(src)
    # MIX [1,2] COLORD COLORS COLORF 1.0 

    if src_count == 1 or iso_count==1 or alpha_mode:
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for x in isolated_channels:
                    loop[referenceColor][x] = 0
                    for c in src_ch:
                        loop[referenceColor][x] += loop[src][c]/src_count

    elif set(src_ch) == set(isolated_channels):
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in src_ch:
                    loop[referenceColor][c] = loop[src][c]
    else:
        self.report({'ERROR'},'Plugin does not support multi-to-multi-different-channel transfer')
        return {'FINISHED'}

    if blend_mode == 'MIX':
        pass
    elif blend_mode == 'ALPHAOVER':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels: 
                    a = loop[referenceColor][3]
                    loop[referenceColor][c] = loop[referenceColor][c]*a + (1-a)*loop[dst][c]
    elif blend_mode == 'PAINTMIX':
         for vertex in bm.verts:
            for loop in vertex.link_loops:
                dstCol = Color(loop[dst][:3])
                refCol = Color(loop[referenceColor][:3])
                referenceColorConv = Color([
                                            clamp01(clamp01(dstCol[0]*(1-.25*refCol[2])*(1-.25*refCol[1]))+\
                                            clamp01(refCol[0]*(1-.25*dstCol[2])*(1-.25*dstCol[1]))),\

                                            clamp01(clamp01(dstCol[1]*(1-.7*refCol[0]))+\
                                            clamp01(refCol[1]*(1-.3*dstCol[0]))),\

                                            clamp01(clamp01(dstCol[2]*(1-.3*refCol[1]))+\
                                            clamp01(refCol[2]*(1-.7*dstCol[1])))
                                            ])
                loop[referenceColor][:3] = referenceColorConv[:3]

    elif blend_mode == 'ADD':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = clamp01(loop[dst][c]+loop[referenceColor][c])
    elif blend_mode == 'LIGHTEN':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = max(loop[dst][c],loop[referenceColor][c])
    elif blend_mode == 'COLORDODGE':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = 1 if 1-loop[referenceColor][c]==0 else clamp01(loop[dst][c]/(1-loop[referenceColor][c]))
    elif blend_mode == 'SCREEN':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = clamp01(1-(1-loop[referenceColor][c])*(1-loop[dst][c]))

    elif blend_mode == 'DARKEN':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = min(loop[referenceColor][c],loop[dst][c])
    elif blend_mode == 'MUL':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] *= loop[dst][c]
    elif blend_mode == 'LINEARBURN':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = clamp01(loop[referenceColor][c]+loop[dst][c]-1)
    elif blend_mode == 'COLORBURN':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = 0 if loop[referenceColor][c]==0 else clamp01(1-(1-loop[dst][c])/loop[referenceColor][c])

    elif blend_mode == 'SUB':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = clamp01(loop[dst][c]-loop[referenceColor][c])
    elif blend_mode == 'DIV':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = 1 if loop[referenceColor][c]==0 else clamp01(loop[dst][c]/loop[referenceColor][c])

    elif blend_mode == 'OVERLAY':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    if loop[referenceColor][c] < 0.5:
                        loop[referenceColor][c] = clamp01(loop[dst][c]*2*loop[referenceColor][c])
                    else:
                        loop[referenceColor][c] = clamp01(1-2*(1-loop[referenceColor][c])*(1-loop[dst][c]))
    elif blend_mode == 'HARDLIGHT':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    if loop[dst][c] < 0.5:
                        loop[referenceColor][c] = clamp01(loop[dst][c]*2*loop[referenceColor][c])
                    else:
                        loop[referenceColor][c] = clamp01(1-2*(1-loop[referenceColor][c])*(1-loop[dst][c]))
    elif blend_mode == 'SOFTLIGHT':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[referenceColor][c] = clamp01((1-2*loop[dst][c])*loop[referenceColor][c]**2 + 2*loop[dst][c]*loop[referenceColor][c])

    elif blend_mode == 'HUE':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                dstCol = Color(loop[dst][:3])
                refCol = Color(loop[referenceColor][:3])
                dstCol.h = refCol.h
                loop[referenceColor][:3] = dstCol[:]
    elif blend_mode == 'SATURATION':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                dstCol = Color(loop[dst][:3])
                refCol = Color(loop[referenceColor][:3])
                dstCol.s = refCol.s
                loop[referenceColor][:3] = dstCol[:]
    elif blend_mode == 'COLOR':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                dstCol = Color(loop[dst][:3])
                refCol = Color(loop[referenceColor][:3])
                dstCol.h = refCol.h
                dstCol.s = refCol.s
                loop[referenceColor][:3] = dstCol[:]
    elif blend_mode == 'VALUE':
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                dstCol = Color(loop[dst][:3])
                refCol = Color(loop[referenceColor][:3])
                dstCol.v = refCol.v
                loop[referenceColor][:3] = dstCol[:]

    if self.factor_vcol != 'NONE':
        factorvc = color_data[self.factor_vcol]
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    f = loop[factorvc][c]*factor_slider
                    loop[dst][c] = loop[referenceColor][c]*f + (1-f)*loop[dst][c]
    else:
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                for c in isolated_channels:
                    loop[dst][c] = loop[referenceColor][c]*factor_slider + (1-factor_slider)*loop[dst][c]

    color_data.remove(referenceColor)
    refreshMesh(bm, obj)
    trySetActiveVC(obj, dstname)

class BlendChannels(bpy.types.Operator):
    bl_idname = "paint.blendchannels"
    bl_label = "Blend Transfer Channels"
    bl_description = "Transfer vertex colors from another layer to the active isolated layer with specified blend mode. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER', 'UNDO'}

    blend_mode : bpy.props.EnumProperty(
        name='Blend type',
        items=blending_modes,
    )

    def vcol_layer_items(self, context):
        obj = context.active_object
        mesh = obj.data
        try: vcollayers = mesh.vertex_colors
        except: vcollayers = mesh.attributes.color
        items = [] if vcollayers is None else [(vcol.name, vcol.name, "") for vcol in vcollayers]
        return items

    def vcol_layer_items_factor(self, context):
        obj = context.active_object
        mesh = obj.data
        try: vcollayers = mesh.vertex_colors
        except: vcollayers = mesh.attributes.color
        items = [('NONE','None','')] 
        if vcollayers is not None:
            items.extend([(vcol.name, vcol.name, "") for vcol in vcollayers])
        return items

    src_vcol: bpy.props.EnumProperty(
        name="Source",
        items=vcol_layer_items,
        description="Source vertex color layer",
    )

    dst_vcol: bpy.props.EnumProperty(
        name="Destination",
        items=vcol_layer_items,
        description="Destination vertex color layer",
    )

    factor_vcol: bpy.props.EnumProperty(
        name="Factor",
        description="Factor color channel. 0-1 RGBA channels corresponds to how much the blend mode will be applied",
        items=vcol_layer_items_factor,
    )

    factor_slider : bpy.props.FloatProperty(
        name="Mix",
        description="Factor amount",
        max=1,
        min=0,
    )

    src_ch: bpy.props.BoolVectorProperty(
        name="Source Channel",
        description="Source color channel. Click and drag to enable/disable multiple simultaneously",
        size=4,
        subtype='XYZ',
    )

    def invoke(self, context, event):
        sett = context.scene.paint_alpha_settings
        obj = context.active_object.data
        self.blend_mode = sett.blend_mode
        self.src_ch = sett.src_ch
        self.src_vcol = sett.src_vcol
        self.factor_slider = sett.factor_slider
        self.factor_vcol = sett.factor_vcol

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color
        self.dst_vcol = findActiveColorLayer(color_data, obj).name

        blendChannels(self, context, sett, obj, bm, color_data)
        return {'FINISHED'}
    
    def execute(self,context):
        sett = context.scene.paint_alpha_settings
        obj = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color

        blendChannels(self, context, sett, obj, bm, color_data)
        return {'FINISHED'}

class SampleAverageVertex(bpy.types.Operator):
    bl_idname = "paint.sample_vertex"
    bl_label = "Sample average vertex"
    bl_description = "Sample a selected vertex or group of vertices for their average color. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'UNDO'}

    def execute(self, context):
        settings = settings = context.scene.paint_alpha_settings
        obj = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color
        color_layer = findActiveColorLayer(color_data, obj)

        if obj.use_paint_mask_vertex:
            vertex_data = [v for v in bm.verts if v.select]
        elif settings.enable_indiscriminate_fill:
            vertex_data = bm.verts

        face_loops = [0,0,0]
        i=0
        for vertex in vertex_data:
            if obj.use_paint_mask:
                for loop in vertex.link_loops: 
                    if loop.face.select: 
                        face_loops = [face_loops[i]+loop[color_layer][i] for i in FL]
                        i+=1
            else:
                for loop in vertex.link_loops:
                    face_loops = [face_loops[i]+loop[color_layer][i] for i in FL]
                    i+=1
        flg = (face_loops[0]/i, face_loops[1]/i, face_loops[2]/i)

        flgc = Color(flg)
        context.tool_settings.vertex_paint.brush.color = flgc

        srgb502 = 128/255
        srgb251 = 64/255

        pal = bpy.data.palettes.get("LEO_Alpha_Palette")
        if not pal:
            pal = bpy.data.palettes.new("LEO_Alpha_Palette")
            # add a color to that palette
            default = pal.colors.new()
            default.color = (1, srgb502, srgb502)
            pal.colors.new().color = (0, srgb502, srgb502)
            pal.colors.new().color = (1, srgb251, srgb502)
            pal.colors.new().color = (srgb502, srgb502, srgb502)
            # make default active
            pal.colors.active = default
            bpy.context.tool_settings.vertex_paint.palette = pal
        
        setColors = set()
        for col in pal.colors:
            setColors.add(tuple(col.color))
        if flg not in setColors:
            flc = pal.colors.new()
            flc.color = flgc
            pal.colors.active = flc

        return {'FINISHED'}

class FlatShading(bpy.types.Operator):
    bl_idname = "paint.flat_shading"
    bl_label = "ToggleVertexShading"
    bl_description = "Set 3d view to flat shading to accurately view vertex colors. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        settings = context.scene.paint_alpha_settings
        current_shading = context.space_data.shading.light
        space_shader_current = context.space_data.shading.color_type
        
        if current_shading != 'FLAT' or space_shader_current != 'VERTEX':   
            settings.past_shading = context.space_data.shading.light
            context.space_data.shading.light = 'FLAT'
            settings.space_shader_storage = context.space_data.shading.color_type
            context.space_data.shading.color_type = 'VERTEX'     
        elif settings.past_shading != 'UnInitialized':
            context.space_data.shading.light = settings.past_shading
            context.space_data.shading.color_type = settings.space_shader_storage
            settings.past_shading = 'FLAT'
        return {'FINISHED'}

def paintChannel(self, context):
    old_color_layer = None
    settings = context.scene.paint_alpha_settings
    # Get the active object
    brushcolor1 = context.tool_settings.vertex_paint.brush.color
    obj = context.active_object.data
    
    bm = bmesh.new()
    bm.from_mesh(obj)
    bm.verts.ensure_lookup_table()
    color_data = bm.loops.layers.color

    color_layer = findActiveColorLayer(color_data, obj)

    basename = color_layer.name
    isolated_channels = [int(x) for x in settings.isolated_Channel]
    if not isolated_channels or any((x==3 for x in isolated_channels)): isolated_channels = FL

    if obj.use_paint_mask_vertex:
        vertex_data = [v for v in bm.verts if v.select]
    elif settings.enable_indiscriminate_fill:
        vertex_data = bm.verts
    else:
        self.report({'ERROR'}, "Cannot paint when no vertices are selected and ALL option is off.")
        return {'FINISHED'}

    for vertex in vertex_data:

        if obj.use_paint_mask:
            face_loops = [loop for loop in vertex.link_loops if loop.face.select]
        else:
            face_loops = [loop for loop in vertex.link_loops]
        for loop in face_loops:
            for x in isolated_channels:
                loop[color_layer][x] = brushcolor1[x]

    refreshMesh(bm, obj)
    trySetActiveVC(obj, basename)

    return {'FINISHED'}

class PaintAlphaOperator(bpy.types.Operator):
    bl_idname = "paint.paint_alpha_operator"
    bl_label = "Paint Color"
    bl_description = "Paint color for the selected vertices in vertex paint mode. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        
        paintChannel(self, context)

        return {'FINISHED'}

def isolateChannel(self, context, ch):
    subtract_channels = False
    color_layer = None
    old_layer_name = None
    addOld = False
    channel = str(ch)
    former_ch = []

    settings = context.scene.paint_alpha_settings
    obj = context.active_object.data
    Mono = settings.one_layer_isolate
    settings.isolated_Channel = ""

    bm = bmesh.new()
    bm.from_mesh(obj)
    bm.verts.ensure_lookup_table()
    color_data = bm.loops.layers.color

    active_color_layer = findActiveColorLayer(color_data, obj)

    basename = active_color_layer.name

    if keyName in basename:
        old_ch = basename.split(keyName)[1]
        former_ch = [int(x) for x in old_ch if x]
        basename = basename.split(keyName)[0]

        settings.isolated_Channel = old_ch

        try: color_layer = color_data[basename]
        except: 
            color_layer = color_data.new(basename)
            color_layer.copy_from(active_color_layer)

        if ch in former_ch:
            subtract_channels = True
            settings.isolated_Channel = old_ch
        else:
            old_layer = active_color_layer
            if not Mono: active_color_layer = color_data.new(basename+keyName+old_ch+channel)
            else: active_color_layer = color_data.new(basename+keyName+channel)
            addOld = True

    else:
        old_layer = active_color_layer
        concisoname = basename+keyName
        old_layer_name = next((x for x in color_data.keys() if concisoname in x), False)

        if old_layer_name:
            old_ch = old_layer_name.split(keyName)[1]
            former_ch = [int(x) for x in old_ch if x]
            old_layer = color_data[old_layer_name]

            settings.isolated_Channel = old_ch

            try: color_layer = color_data[basename]
            except:
                color_layer = color_data.new(basename)
                color_layer.copy_from(active_color_layer)

            if ch in former_ch:
                subtract_channels = True
                settings.isolated_Channel = old_ch
            else:
                if not Mono: active_color_layer = color_data.new(concisoname+old_ch+channel)
                else: active_color_layer = color_data.new(concisoname+channel)
                addOld = True

        else: 
            color_layer = color_data[basename]
            active_color_layer = color_data.new(concisoname+channel)

    if subtract_channels:
        settings.isolated_Channel = settings.isolated_Channel.replace(channel,"")
        isolated_channels = [int(x) for x in settings.isolated_Channel]

        if 3 in isolated_channels and not ch==3:
            if not old_layer_name: prev_layer = active_color_layer
            else: prev_layer = old_layer
            new_active_name = basename+keyName+settings.isolated_Channel
            active_color_layer = color_data.new(new_active_name)
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    a = Color(loop[prev_layer][:3]).v
                    loop[active_color_layer][:3] = [a,a,a]
            if not old_layer_name: color_data.remove(prev_layer)
            else: color_data.remove(old_layer)

        elif ch==3 and not isolated_channels:
            settings.isolated_Channel = ""
            if not old_layer_name:
                for vertex in bm.verts:
                    for loop in vertex.link_loops:
                        loop[color_layer][3] = Color(loop[active_color_layer][:3]).v
                color_data.remove(active_color_layer)
            else: color_data.remove(old_layer)
            new_active_name = basename

        elif ch==3:
            prev_layer = active_color_layer
            new_active_name = basename+keyName+settings.isolated_Channel
            active_color_layer = color_data.new(new_active_name)
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    loop[color_layer][3] = Color(loop[prev_layer][:3]).v
                    rgb_c = [0,0,0]
                    for x in isolated_channels:
                        rgb_c[x] = loop[color_layer][x]
                    loop[active_color_layer][:3] = rgb_c
            if not old_layer_name: color_data.remove(prev_layer)
            else: color_data.remove(old_layer)

        elif isolated_channels:
            prev_layer = active_color_layer
            new_active_name = basename+keyName+settings.isolated_Channel
            active_color_layer = color_data.new(new_active_name)
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    rgb_c = [0,0,0]
                    for x in former_ch:
                        loop[color_layer][x]=loop[prev_layer][x]
                    for x in isolated_channels:
                        rgb_c[x] = loop[color_layer][x]
                    loop[active_color_layer][:3] = rgb_c
            if not old_layer_name: color_data.remove(prev_layer)
            else: color_data.remove(old_layer)
            
        else:
            settings.isolated_Channel = ""
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    loop[color_layer][ch] = loop[active_color_layer][ch]
            if not old_layer_name: color_data.remove(active_color_layer)
            else: color_data.remove(old_layer)
            new_active_name = basename

        refreshMesh(bm, obj)
        trySetActiveVC(obj, new_active_name)

        return {'FINISHED'}

    if Mono: settings.isolated_Channel = channel

    old_channels = [int(x) for x in settings.isolated_Channel]
    
    if channel not in settings.isolated_Channel:
        settings.isolated_Channel += channel
    isolated_channels = [int(x) for x in settings.isolated_Channel]

    if ch==3:
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                a = loop[color_layer][3]
                loop[active_color_layer][:3] = (a,a,a)
        if addOld:
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    for x in former_ch:
                        loop[old_layer][x] = loop[color_layer][x]

    elif 3 in isolated_channels:
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                a = Color(loop[old_layer][:3]).v
                loop[active_color_layer][:3] = (a,a,a)

    else:
        old_channels = [x for x in old_channels if x!=ch]
        if 3 in former_ch and not old_layer_name:
            former_ch = [x for x in former_ch if x!=3]
            for vertex in bm.verts:
                for loop in vertex.link_loops:
                    for x in former_ch:
                        loop[color_layer][x]=loop[old_layer][x]
                    loop[color_layer][3]=Color(loop[old_layer][:3]).v
        
        for vertex in bm.verts:
            for loop in vertex.link_loops:
                rgb_c = [0,0,0]
                for x in old_channels:
                    rgb_c[x]=loop[old_layer][x]
                rgb_c[ch]=loop[color_layer][ch]
                loop[active_color_layer][:3] = rgb_c[:3]

    if addOld: color_data.remove(old_layer)
    refreshMesh(bm, obj)
    trySetActiveVC(obj, basename+keyName+settings.isolated_Channel)

    return bm, obj

class IsolateVertexAlpha(bpy.types.Operator):
    bl_idname = "paint.isolate_vertex_alpha"
    bl_label = "A"
    bl_description = "Isolate the vertex color alpha channel. \nOutline thickness (Higher = thicker, Lower = less width). \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'UNDO'}
    def execute(self, context):
        isolateChannel(self, context, 3)
        return {'FINISHED'}

class IsolateVertexRed(bpy.types.Operator):
    bl_idname = "paint.isolate_vertex_red"
    bl_label = "R"
    bl_description = "Isolate the vertex color red channel. \nAmbient Occlusion (Higher = no occlude, Lower = Ambient Occlusion). \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'UNDO'}
    def execute(self, context):
        isolateChannel(self, context, 0)
        return {'FINISHED'}

class IsolateVertexGreen(bpy.types.Operator):
    bl_idname = "paint.isolate_vertex_green"
    bl_label = "G"
    bl_description = "Isolate the vertex color green channel. \nShadow Smoothing (Higher = Sharper, Lower = Smoother). \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'UNDO'}
    def execute(self, context):
        isolateChannel(self, context, 1)
        return {'FINISHED'}

class IsolateVertexBlue(bpy.types.Operator):
    bl_idname = "paint.isolate_vertex_blue"
    bl_label = "B"
    bl_description = "Isolate the vertex color blue channel. \nOutline z/depth-index (Higher = behind, Lower = in front). \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'UNDO'}
    def execute(self, context):
        isolateChannel(self, context, 2)
        return {'FINISHED'}

# Gradient tool by andyp123 adapted for leo alpha paint; github at: https://github.com/andyp123/blender_vertex_color_master
def draw_gradient_callback(self, context, line_params, line_shader, circle_shader):
    line_batch = batch_for_shader(line_shader, 'LINES', {
        "pos": line_params["coords"],
        "color": line_params["colors"]})
    line_shader.bind()
    line_batch.draw(line_shader)

    if circle_shader is not None:
        a = line_params["coords"][0]
        b = line_params["coords"][1]
        radius = (b - a).length
        steps = 50
        circle_points = []
        for i in range(steps+1):
            angle = (2.0 * math.pi * i) / steps
            point = Vector((a.x + radius * math.cos(angle), a.y + radius * math.sin(angle)))
            circle_points.append(point)

        circle_batch = batch_for_shader(circle_shader, 'LINE_LOOP', {
            "pos": circle_points})
        circle_shader.bind()
        circle_shader.uniform_float("color", line_params["colors"][1])
        circle_batch.draw(circle_shader)

def mapsum(self, x):
    e = self.error_margin
    errorlist = [x[0]+e, x[1]+e, x[2]+e]
    errorlist_ = [x[0]-e, x[1]-e, x[2]-e]

    return (errorlist_,errorlist)

class SelectByIsolatedVertexColor(bpy.types.Operator):
    bl_idname = "paint.selectbyisolatedvertexcolor"
    bl_label = "Select Color"
    bl_description = "Select by isolated vertex color. \nRight click to assign shortcut"
    bl_options = {'REGISTER','UNDO'}

    error_margin : bpy.props.FloatProperty(
        name="Error margin",
        description="precision of color select value",
        default=0.001,
        min=0
    )

    restrict_loops : bpy.props.BoolProperty(
        name="Exclude Loops",
        description="Exclude vertices that have a loop which does not match the primary color",
        default=False
    )

    def execute(self, context):
        obj = context.active_object.data
        brush = bpy.context.tool_settings.vertex_paint.brush

        obj.use_paint_mask_vertex = True

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color

        color_layer = findActiveColorLayer(color_data, obj)

        brushError_, brushError = mapsum(self, brush.color)

        for vertex in bm.verts:
            for loop in vertex.link_loops:
                x = loop[color_layer] 
                if all((brushError_[i] <= x[i] <= brushError[i] for i in FL)):
                    try: vertex.select_set(True)
                    except: vertex.select = True
                elif self.restrict_loops:
                    try: vertex.select_set(False)
                    except: vertex.select = False
                    break

        refreshMesh(bm, obj)

        return {'FINISHED'}

class SelectByPaletteColor(bpy.types.Operator):
    bl_idname = "paint.selectbypalettecolor"
    bl_label = "Select Palette"
    bl_description = "Select by colors in the active palette. WARNING: Slow. Complexity of selection is # of non-hidden vertices * # of palette colors. \nRight click to assign shortcut"
    bl_options = {'REGISTER','UNDO'}

    error_margin : bpy.props.FloatProperty(
        name="Error margin",
        description="precision of color select value",
        default=0.001,
        min=0
    )

    restrict_loops : bpy.props.BoolProperty(
        name="Exclude Loops",
        description="Exclude vertices that have a loop which does not match the primary color",
        default=False
    )

    def execute(self, context):
        obj = context.active_object.data
        palette = context.tool_settings.vertex_paint.palette.colors

        obj.use_paint_mask_vertex = True

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color

        color_layer = findActiveColorLayer(color_data, obj)

        paletteError = [mapsum(self, x.color) for x in palette]

        for vertex in bm.verts:
            for loop in vertex.link_loops:
                x = loop[color_layer]
                for a, b in paletteError:
                    if all((a[i] <= x[i] <= b[i] for i in FL)):
                        try: vertex.select_set(True)
                        except: vertex.select = True
                        break
                if self.restrict_loops and vertex.select == False:
                    try: vertex.select_set(False)
                    except: vertex.select = False
                    break

        refreshMesh(bm, obj)

        return {'FINISHED'}

class PaintGradient(bpy.types.Operator):
    """Draw a line with the mouse to paint a vertex color gradient"""
    bl_idname = "paint.gradienttool"
    bl_label = "Gradient Tool"
    bl_description = "Paint vertex color gradient. \nRight click to assign shortcut"
    bl_options = {"REGISTER", "UNDO"}

    _handle = None

    line_shader = gpu.shader.from_builtin('2D_SMOOTH_COLOR')
    circle_shader = gpu.shader.from_builtin('2D_UNIFORM_COLOR')

    start_color: bpy.props.FloatVectorProperty(
        name="Start Color",
        subtype='COLOR_GAMMA',
        default=[1.0,0.0,0.0],
        description="Start color of the gradient",
        min=0.0,
        max=1.0,
    )

    end_color: bpy.props.FloatVectorProperty(
        name="End Color",
        subtype='COLOR_GAMMA',
        default=[0.0,1.0,0.0],
        description="End color of the gradient",
        min=0.0,
        max=1.0,
    )

    circular_gradient: bpy.props.BoolProperty(
        name="Circular Gradient",
        description="Paint a circular gradient",
        default=False
    )

    use_hue_blend: bpy.props.BoolProperty(
        name="Use Hue Blend",
        description="Gradually blend start and end colors using full hue range instead of simple blend",
        default=False
    )

    @classmethod
    def poll(cls, context):
        obj = context.active_object
        return bpy.context.object.mode == 'VERTEX_PAINT' and obj is not None and obj.type == 'MESH'

    def paintVerts(self, context, start_point, end_point, start_color, end_color, circular_gradient=False, use_hue_blend=False):

        region = context.region
        rv3d = context.region_data

        obj = context.active_object
        mesh = obj.data

        # Create a new bmesh to work with
        bm = bmesh.new()
        bm.from_mesh(mesh)
        bm.verts.ensure_lookup_table()

        # List of structures containing 3d vertex and project 2d position of vertex
        # vertex_data = None # Will contain vert, and vert coordinates in 2d view space
        if mesh.use_paint_mask_vertex: # Face masking not currently supported
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world @ v.co)) for v in bm.verts if v.select]
        else:
            vertex_data = [(v, view3d_utils.location_3d_to_region_2d(region, rv3d, obj.matrix_world @ v.co)) for v in bm.verts]

        # Vertex transformation math
        down_vector = Vector((0, -1, 0))
        direction_vector = Vector((end_point.x - start_point.x, end_point.y - start_point.y, 0)).normalized()
        rotation = direction_vector.rotation_difference(down_vector)

        translation_matrix = Matrix.Translation(Vector((-start_point.x, -start_point.y, 0)))
        inverse_translation_matrix = translation_matrix.inverted()
        rotation_matrix = rotation.to_matrix().to_4x4()
        combinedMat = inverse_translation_matrix @ rotation_matrix @ translation_matrix

        transStart = combinedMat @ start_point.to_4d() # Transform drawn line : rotate it to align to horizontal line
        transEnd = combinedMat @ end_point.to_4d()
        minY = transStart.y
        maxY = transEnd.y
        heightTrans = maxY - minY  # Get the height of transformed vector

        transVector = transEnd - transStart
        transLen = transVector.length

        # Calculate hue, saturation and value shift for blending
        if use_hue_blend:
            start_color = Color(start_color[:3])
            end_color = Color(end_color[:3])
            c1_hue = start_color.h
            c2_hue = end_color.h
            hue_separation = c2_hue - c1_hue
            if hue_separation > 0.5:
                hue_separation = hue_separation - 1
            elif hue_separation < -0.5:
                hue_separation = hue_separation + 1
            c1_sat = start_color.s
            sat_separation = end_color.s - c1_sat
            c1_val = start_color.v
            val_separation = end_color.v - c1_val

        color_layer = findActiveColorLayer(bm.loops.layers.color, mesh)

        for data in vertex_data:
            vertex = data[0]
            vertCo4d = Vector((data[1].x, data[1].y, 0))
            transVec = combinedMat @ vertCo4d

            t = 0

            if circular_gradient:
                curVector = transVec.to_4d() - transStart
                curLen = curVector.length
                t = abs(max(min(curLen / transLen, 1), 0))
            else:
                t = abs(max(min((transVec.y - minY) / heightTrans, 1), 0))

            color = Color((1, 0, 0))
            if use_hue_blend:
                # Hue wraps, and fmod doesn't work with negative values
                color.h = fmod(1.0 + c1_hue + hue_separation * t, 1.0) 
                color.s = c1_sat + sat_separation * t
                color.v = c1_val + val_separation * t
            else:
                color.r = start_color[0] + (end_color[0] - start_color[0]) * t
                color.g = start_color[1] + (end_color[1] - start_color[1]) * t
                color.b = start_color[2] + (end_color[2] - start_color[2]) * t

            if mesh.use_paint_mask: # Masking by face
                face_loops = [loop for loop in vertex.link_loops if loop.face.select] # Get only loops that belong to selected faces
            else: # Masking by verts or no masking at all
                face_loops = [loop for loop in vertex.link_loops] # Get remaining vert loops

            for loop in face_loops:
                new_color = loop[color_layer]
                new_color[:3] = color
                loop[color_layer] = new_color

        bm.to_mesh(mesh)
        bm.free()
        bpy.ops.object.mode_set(mode='VERTEX_PAINT')

    def axis_snap(self, start, end, delta):
        if start.x - delta < end.x < start.x + delta:
            return Vector((start.x, end.y))
        if start.y - delta < end.y < start.y + delta:
            return Vector((end.x, start.y))
        return end

    def modal(self, context, event):
        context.area.tag_redraw()

        # Begin gradient line and initialize draw handler
        if self._handle is None:
            if event.type == 'LEFTMOUSE':
                # Store the foreground and background color for redo
                brush = context.tool_settings.vertex_paint.brush
                self.start_color = brush.color
                self.end_color = brush.secondary_color

                # Create arguments to pass to the draw handler callback
                mouse_position = Vector((event.mouse_region_x, event.mouse_region_y))
                self.line_params = {
                    "coords": [mouse_position, mouse_position],
                    "colors": [brush.color[:] + (1.0,),
                               brush.secondary_color[:] + (1.0,)],
                    "width": 1, # currently does nothing
                }
                args = (self, context, self.line_params, self.line_shader,
                    (self.circle_shader if self.circular_gradient else None))
                self._handle = bpy.types.SpaceView3D.draw_handler_add(draw_gradient_callback, args, 'WINDOW', 'POST_PIXEL')
        else:
            # Update or confirm gradient end point
            if event.type in {'MOUSEMOVE', 'LEFTMOUSE'}:
                line_params = self.line_params
                delta = 20

                # Update and constrain end point
                start_point = line_params["coords"][0]
                end_point = Vector((event.mouse_region_x, event.mouse_region_y))
                if event.shift:
                    end_point = self.axis_snap(start_point, end_point, delta)
                line_params["coords"] = [start_point, end_point]

                if event.type == 'LEFTMOUSE' and end_point != start_point: # Finish updating the line and paint the vertices
                    bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                    self._handle = None

                    # Gradient will not work if there is no delta
                    if end_point == start_point:
                        return {'CANCELLED'}

                    start_color = line_params["colors"][0]
                    end_color = line_params["colors"][1]

                    use_hue_blend = self.use_hue_blend

                    self.paintVerts(context, start_point, end_point, start_color, end_color, self.circular_gradient, use_hue_blend)
                    return {'FINISHED'}            

        # Allow camera navigation
        if event.type in {'MIDDLEMOUSE', 'WHEELUPMOUSE', 'WHEELDOWNMOUSE'}:
            return {'PASS_THROUGH'}

        if event.type in {'RIGHTMOUSE', 'ESC'}:
            if self._handle is not None:
                bpy.types.SpaceView3D.draw_handler_remove(self._handle, 'WINDOW')
                self._handle = None
            return {'CANCELLED'}

        # Keep running until completed or cancelled
        return {'RUNNING_MODAL'}

    def execute(self, context):
        
        start_point = self.line_params["coords"][0]
        end_point = self.line_params["coords"][1]
        start_color = self.start_color
        end_color = self.end_color

        use_hue_blend = self.use_hue_blend

        self.paintVerts(context, start_point, end_point, start_color, end_color, self.circular_gradient, use_hue_blend)

        return {'FINISHED'}

    def invoke(self, context, event):
        if context.area.type == 'VIEW_3D':
            context.window_manager.modal_handler_add(self)
            return {'RUNNING_MODAL'}
        else:
            self.report({'WARNING'}, "View3D not found, cannot run operator")
            return {'CANCELLED'}

class CustomNewColorPalette(bpy.types.Operator):
    bl_idname = "paint.custom_new_color_palette"
    bl_label = "New palette"
    bl_description = "Add new color palette. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        newpal = bpy.data.palettes.new(context.active_object.name)
        context.tool_settings.vertex_paint.palette = newpal

        return {'FINISHED'}

def findPaletteIndex(palettes, searchname):
    for i, x in enumerate(palettes):
            if x.name == searchname:
                return i

class CustomRemoveColorPalette(bpy.types.Operator):
    bl_idname = "paint.custom_remove_color_palette"
    bl_label = "Delete palette"
    bl_description = "Delete the active color palette. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        active = context.tool_settings.vertex_paint.palette
        index = findPaletteIndex(bpy.data.palettes, active.name)
        bpy.data.palettes.remove(context.tool_settings.vertex_paint.palette)
        try: context.tool_settings.vertex_paint.palette = bpy.data.palettes[index-1]
        except: pass

        return {'FINISHED'}

class PaletteVertexColors(bpy.types.Operator):
    bl_idname = "paint.palettevertexcolors"
    bl_label = "Palette vertex colors"
    bl_description = "Create a color palette from the active/selected vertex colors. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    def execute(self, context):
        obj = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color
        color_layer = findActiveColorLayer(color_data, obj)
        setColors = set()

        pal = bpy.data.palettes.new(color_layer.name)
        context.tool_settings.vertex_paint.palette = pal

        if obj.use_paint_mask_vertex:
            vertex_data = [v for v in bm.verts if v.select]
        else:
            vertex_data = bm.verts

        for vertex in vertex_data:
            if obj.use_paint_mask:
                face_loops = [loop for loop in vertex.link_loops if loop.face.select]
            else:
                face_loops = [loop for loop in vertex.link_loops]
            for loop in face_loops:
                loopcolor = loop[color_layer][:3]
                t = tuple(loopcolor)
                if t not in setColors:
                    setColors.add(t)
                    pal.colors.new().color = loopcolor
            
        bpy.ops.palette.sort()
        return {'FINISHED'}

class QuickExportVertexColors(bpy.types.Operator):
    bl_idname="paint.quickexportvertexcolors"
    bl_label = "Quick Optimize COLOR"
    bl_description = "Quickly prepare optimal vertex colors for export. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    default_4COLOR : bpy.props.FloatVectorProperty(
        name='COLOR',
        subtype='COLOR_GAMMA',
        size=4,
        default=[1.0,0.502,0.502,0.502],
        description="RGBA color of vertex colors. Default value is optimal",
        min=0.0,
        max=1.0,
    )

    delete_old_vc : bpy.props.BoolProperty(
        name="Delete old COLOR",
        description="Delete other vertex color layers",
        default=True,
    )

    def execute(self, context):
        obj = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color
        new = True

        if self.delete_old_vc:
            deletelist = []
            for layer in color_data.keys():
                if layer != 'COLOR':
                    deletelist.append(layer)
                else: new = False
            for deletelayer in deletelist:
                color_data.remove(color_data[deletelayer])

        if new: color_L = color_data.new("COLOR")

        color_layer = color_data["COLOR"]

        if new: 
            if color_layer != color_L:
                color_L.copy_from(color_layer)

        for vertex in bm.verts:
            for loop in vertex.link_loops:
                loop[color_layer] = self.default_4COLOR

        refreshMesh(bm, obj)
        trySetActiveVC(obj, 'COLOR')

        return {'FINISHED'}

    def invoke(self, context, event):
        return context.window_manager.invoke_props_dialog(self, width=300)

class ResetAddonMemory(bpy.types.Operator):
    bl_idname = "paint.resetaddonmemory"
    bl_label = "Reset View"
    bl_description = "Discard current view layer and reset internal isolated channels memory. \nRight click to assign shortcut"
    bl_context = 'vertexpaint'
    bl_options = {'REGISTER','UNDO'}

    isolated_channels : bpy.props.StringProperty(
        name="isolated channels",
        default="")

    def execute(self, context):
        settings = context.scene.paint_alpha_settings
        settings.isolated_Channel = self.isolated_channels

        obj = context.active_object.data

        bm = bmesh.new()
        bm.from_mesh(obj)
        bm.verts.ensure_lookup_table()
        color_data = bm.loops.layers.color
        color_layer_name = findActiveColorLayer(color_data, obj).name

        if keyName in color_layer_name:
            color_data.remove(color_data[color_layer_name])

        refreshMesh(bm, obj)
        trySetActiveVC(obj, color_layer_name.split(keyName)[0])

        return {'FINISHED'}

class PaintAlphaPanel(bpy.types.Panel):
    bl_idname = "OBJECT_PT_paint_alpha"
    bl_label = "LEO Alpha Paint"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "Vertex Paint"
    bl_context = 'vertexpaint'
    #bpy.data.brushes['Draw'].use_alpha = False

    def draw(self, context):
        settings = context.scene.paint_alpha_settings
        obj = context.active_object.data
        layout = self.layout

        col = layout.column(align=True)
        col.operator("paint.quickexportvertexcolors")

        box = col.box()
        col = box.column()
        row = col.row(align=True)
        if settings.past_shading == 'UnInitialized':
            row.operator("paint.flat_shading", text = "Shade FLAT")
        else:
            row.operator("paint.flat_shading", text = "Shade " + settings.past_shading)
        row.prop(context.tool_settings.vertex_paint.brush, "use_alpha", text = "affect alpha", toggle=True)

        row = col.row(align=True)
        row.prop(obj, "use_paint_mask_vertex", text='Vertex')
        row.prop(obj, "use_paint_mask", text='Face')

        col = layout.column(align=True)
        col.label(text="Isolate Channels")
        row = col.row(align=True)
        row.prop(settings, "one_layer_isolate", toggle=True, text="Mono")
        row.operator("paint.resetaddonmemory")

        row = col.row(align=True)

        backupstring = settings.isolated_Channel
        row.operator("paint.isolate_vertex_red", depress = "0" in backupstring)
        row.operator("paint.isolate_vertex_green", depress = "1" in backupstring)
        row.operator("paint.isolate_vertex_blue", depress = "2" in backupstring)
        col.operator("paint.isolate_vertex_alpha", depress = "3" in backupstring)

        box = col.box()
        col = box.column(align=True)
        
        col.prop(context.tool_settings.vertex_paint.brush, "color", text="")
        row = col.row(align=True)
        row.operator("paint.paint_alpha_operator")
        row.prop(settings, "enable_indiscriminate_fill", text = "ALL", toggle=True)
        row = col.row(align=True)
        if settings.select_color_mode == 'PALETTE':
            row.operator("paint.selectbypalettecolor", text='Select')
        else: row.operator("paint.selectbyisolatedvertexcolor", text='Select')
        row.prop(settings, "select_color_mode", text='')
        
        row = col.row(align=True)
        row.operator("paint.gradienttool", text='Gradient')
        row.prop(context.tool_settings.vertex_paint.brush, "secondary_color", text="")

        col = layout.column(align=True)
        col.prop(settings, "enable_transfer_tools", toggle=True)
        if settings.enable_transfer_tools:
            box = col.box()
            col = box.column(align=True)
            row = col.row(align=True)
            if settings.blend_mode == 'ALPHAOVER': echannellist = enumerate(channel_list[:3])
            else: echannellist = enumerate(channel_list)
            for i,name in echannellist:
                row.prop(settings, "src_ch", index=i, text=name, toggle=True)

            col.prop(settings, "src_vcol")
            col = box.column(align=True)
            col.prop(settings, "blend_mode", text='Blend')
            col.prop(settings, 'factor_vcol')
            col.prop(settings, 'factor_slider', slider=True)
            col = box.column(align=True)
            col.operator("paint.blendchannels")
            try: col.prop(obj.vertex_colors, "active", text='Active')
            except: col.prop(obj.attributes, "active_color", text='Active')
            
        box = layout.box()
        col = box.column()
        col.operator("paint.sample_vertex", text = "Sample selected colors")

        col = box.column(align=True)
        col.operator("paint.palettevertexcolors", text='Palette vertex colors')
        
        row = col.row(align=True)
        row.operator("paint.custom_new_color_palette", text="New")
        row.operator("paint.custom_remove_color_palette", text="Delete")
        col.prop(context.tool_settings.vertex_paint, "palette", text="")
        col.template_palette(context.tool_settings.vertex_paint, "palette", color=True)

        layout.separator()
        
        layout.label(text="For discord.gg/agmg modding")

classes = (
    PaintAlphaPropertyGroup,
    BlendChannels,
    PaintAlphaOperator,
    PaintAlphaPanel,
    FlatShading,
    IsolateVertexAlpha,
    IsolateVertexRed,
    IsolateVertexGreen,
    IsolateVertexBlue,
    SampleAverageVertex,
    SelectByIsolatedVertexColor,
    SelectByPaletteColor,
    PaintGradient,
    CustomNewColorPalette,
    CustomRemoveColorPalette,
    PaletteVertexColors,
    QuickExportVertexColors,
    ResetAddonMemory,
    )

def register():
    # add operators
    for c in classes:
        bpy.utils.register_class(c)
    bpy.types.Scene.paint_alpha_settings = bpy.props.PointerProperty(type=PaintAlphaPropertyGroup)

def unregister():
    # remove operators
    del bpy.types.Scene.paint_alpha_settings 
    for c in reversed(classes):
        bpy.utils.unregister_class(c)

    pal = bpy.data.palettes.get("LEO_Alpha_Palette")
    if pal:
        del pal

if __name__ == "__main__":
    register()

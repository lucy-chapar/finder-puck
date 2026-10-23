"""
Studio renders of the finder puck in Blender 3.5 (Cycles on the Metal GPU).

    MESH_DIR=<dir> /Applications/FreeCAD.app/Contents/Resources/bin/freecadcmd case/export_meshes.py
    MESH_DIR=<dir> /opt/homebrew/bin/blender -b --python case/render_blender.py -- hero,pair,back [samples] [width]

MESH_DIR holds the STLs written by export_meshes.py (default case/blender_mesh).  Views:
  hero  one puck face up, searching (arrow and "38 m"), orange cord through the lanyard tunnel
  pair  two pucks that have found each other: arrows point at one another and the bezels glow (beacon)
  back  one puck turned over like a pancake, showing the debossed radar dial
Renders go to docs/finder_puck_render[_<view>].png; each scene is also saved as <MESH_DIR>/finder_puck_<view>.blend
so it can be opened and tweaked by hand.  The screen graphics, cord and cord lock exist only here, not in the case model.
Units: the assembly's mm scaled to metres, each puck centred on its own empty (12 o'clock = local +Y, button = -Y).
"""

import math
import os
import sys

import bmesh
import bpy
from mathutils import Vector

CASE = os.path.dirname(os.path.abspath(__file__))
PUCK = os.path.dirname(CASE)
MESH = os.environ.get("MESH_DIR") or os.path.join(CASE, "blender_mesh")
DOCS = os.path.join(PUCK, "docs")
FONT = os.path.join(PUCK, "manual", "assets", "fonts", "DejaVuSans-Bold.ttf")
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
VIEWS = (args[0] if args else "hero").split(",")
SAMPLES = int(args[1]) if len(args) > 1 else 512
WIDTH = int(args[2]) if len(args) > 2 else 2400

MM = 0.001
CENTRE = Vector((36.0, -36.0, 0.0))        # board centre in the assembly frame
Z_BOTTOM = -9.7                            # shell underside
Z_FACE = 8.0                               # plate face
Z_SCREEN = 5.5                             # panel top; the crystal starts at 5.7
R_ACTIVE = 32.4 / 2
LANYARD_Y, LANYARD_Z = -35.3, -5.6         # chord bore along X (build_case.py LANYARD_R, LANYARD_Z)
CORD_R = 1.0                               # 2 mm cord in the 2.8 mm bore
LOCK_R, LOCK_L = 3.0, 9.0                  # barrel cord lock
PARTS = ["Shell", "Plate", "Ring", "Bezel", "Cap", "Index", "Crystal", "Panel", "Board",
         "Bolt1", "Bolt2", "Bolt3", "Bolt4"]


# --- Scene ------------------------------------------------------------------
def setup_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    prefs.compute_device_type = "METAL"
    prefs.refresh_devices()
    for d in prefs.devices:
        d.use = True
    c = scene.cycles
    c.device = "GPU"
    c.samples = SAMPLES
    c.use_adaptive_sampling = True
    c.adaptive_threshold = 0.01
    c.use_denoising = True
    c.denoiser = "OPENIMAGEDENOISE"
    c.max_bounces = 12
    c.transmission_bounces = 12
    c.transparent_max_bounces = 12
    c.glossy_bounces = 8
    c.caustics_reflective = False
    c.caustics_refractive = False
    c.blur_glossy = 1.0
    r = scene.render
    r.resolution_x = WIDTH
    r.resolution_y = int(WIDTH * 2 / 3)
    r.resolution_percentage = 100
    r.film_transparent = False
    r.image_settings.file_format = "PNG"
    r.image_settings.color_mode = "RGB"
    r.image_settings.compression = 50
    scene.view_settings.view_transform = "Filmic"
    scene.view_settings.look = "Medium High Contrast"
    scene.view_settings.exposure = -1.0
    world = bpy.data.worlds.new("Studio")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.010, 0.010, 0.012, 1.0)
    bg.inputs["Strength"].default_value = 1.0
    return scene


# --- Materials --------------------------------------------------------------
def new_material(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nodes = m.node_tree.nodes
    nodes.clear()
    return m, nodes, m.node_tree.links, nodes.new("ShaderNodeOutputMaterial")


def grain(nodes, links, scale, strength, distance, target):
    """Fine noise bump so plastic and cord aren't perfect mathematical surfaces."""
    noise = nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = scale
    noise.inputs["Detail"].default_value = 3.0
    noise.inputs["Roughness"].default_value = 0.6
    bump = nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = strength
    bump.inputs["Distance"].default_value = distance
    links.new(noise.outputs["Fac"], bump.inputs["Height"])
    links.new(bump.outputs["Normal"], target)


def principled(name, color, rough, metallic=0.0, specular=0.5, coat=0.0, sheen=0.0, bump=None):
    m, nodes, links, out = new_material(name)
    p = nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = color
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Specular"].default_value = specular
    p.inputs["Clearcoat"].default_value = coat
    p.inputs["Sheen"].default_value = sheen
    if bump:
        grain(nodes, links, *bump, p.inputs["Normal"])
    links.new(p.outputs["BSDF"], out.inputs["Surface"])
    return m


def emissive(name, color, strength):
    m, nodes, links, out = new_material(name)
    e = nodes.new("ShaderNodeEmission")
    e.inputs["Color"].default_value = color
    e.inputs["Strength"].default_value = strength
    links.new(e.outputs["Emission"], out.inputs["Surface"])
    return m


def glass(name, color, rough, ior):
    m, nodes, links, out = new_material(name)
    g = nodes.new("ShaderNodeBsdfGlass")
    g.inputs["Color"].default_value = color
    g.inputs["Roughness"].default_value = rough
    g.inputs["IOR"].default_value = ior
    links.new(g.outputs["BSDF"], out.inputs["Surface"])
    return m


def make_materials():
    orange = (0.80, 0.17, 0.012, 1)
    m = {
        "black": principled("MatteBlack", (0.016, 0.016, 0.017, 1), 0.62, specular=0.3, bump=(2200, 0.25, 0.00003)),
        "orange": principled("OrangePlastic", orange, 0.42, specular=0.45, coat=0.1),
        "anodised": principled("OrangeAnodised", (0.85, 0.22, 0.03, 1), 0.33, metallic=0.95, specular=0.6),
        "mask": principled("Soldermask", (0.02, 0.04, 0.03, 1), 0.45),
        "panel": principled("PanelBorder", (0.004, 0.005, 0.006, 1), 0.45, specular=0.3),
        "crystal": glass("MineralGlass", (1, 1, 1, 1), 0.0, 1.52),
        "resin": glass("ClearResin", (0.95, 0.96, 0.94, 1), 0.06, 1.50),
        "cord": principled("Cord", orange, 0.75, specular=0.3, sheen=0.6, bump=(900, 0.5, 0.00008)),
        "lock": principled("CordLock", (0.012, 0.012, 0.013, 1), 0.35, specular=0.5),
        "floor": principled("Floor", (0.03, 0.029, 0.032, 1), 0.38, specular=0.35),
        # The LCD is pure emission: a lit panel under a crystal shows its graphics, not studio reflections
        # (the crystal on top supplies those).
        "screen": emissive("ScreenBlack", (0.010, 0.012, 0.016, 1), 1.0),
        "ui_dim": emissive("UiDim", (0.55, 0.42, 0.30, 1), 2.0),
        "ui_orange": emissive("UiOrange", (1.0, 0.22, 0.015, 1), 3.0),
        "ui_white": emissive("UiWhite", (1.0, 0.93, 0.85, 1), 6.0),
    }
    # The beacon: LEDs feeding the light pipes make the whole clear lip glow, brightest where the resin is thickest.
    lit = glass("ResinLit", (1.0, 0.92, 0.86, 1), 0.12, 1.50)
    nodes, links, out = lit.node_tree.nodes, lit.node_tree.links, lit.node_tree.nodes["Material Output"]
    vol = nodes.new("ShaderNodeEmission")
    vol.inputs["Color"].default_value = (1.0, 0.30, 0.04, 1)
    vol.inputs["Strength"].default_value = 1400.0               # per metre of resin: a few mm of lip -> ~3
    links.new(vol.outputs["Emission"], out.inputs["Volume"])
    m["resin_lit"] = lit
    m["halo"] = [emissive("UiHalo%d" % i, (1.0, 0.25, 0.02, 1), 0.5 * (1 - i / 6.0) ** 2) for i in range(6)]
    m["sweep"] = [emissive("UiSweep%d" % i, (1.0, 0.25, 0.03, 1), 0.18 * (1 - i / 16.0) ** 3) for i in range(16)]
    return m


# --- Geometry helpers -------------------------------------------------------
def link(obj, parent=None):
    bpy.context.scene.collection.objects.link(obj)
    obj.parent = parent
    return obj


def finish(obj, material, smooth_angle=35.0):
    me = obj.data
    if smooth_angle:
        for p in me.polygons:
            p.use_smooth = True
        me.use_auto_smooth = True
        me.auto_smooth_angle = math.radians(smooth_angle)
    me.materials.clear()
    me.materials.append(material)
    return obj


def flat(parent, name, verts, faces, material, z):
    """A flat shape from 2D mm coordinates lying at height z (mm), in the puck's own frame."""
    me = bpy.data.meshes.new(name)
    me.from_pydata([(x * MM, y * MM, z * MM) for x, y in verts], [], faces)
    me.update()
    return finish(link(bpy.data.objects.new(name, me), parent), material, smooth_angle=0)


def disc(parent, name, r, z, material, cx=0.0, cy=0.0, n=96):
    verts = [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    return flat(parent, name, verts, [list(range(n))], material, z)


def annulus(parent, name, r0, r1, z, material, a0=0.0, a1=360.0, n=128):
    full = abs(a1 - a0) >= 360.0
    steps = n if full else max(4, int(math.ceil(n * abs(a1 - a0) / 360.0)))
    ring = steps if full else steps + 1
    verts = []
    for i in range(ring):
        a = math.radians(a0 + (a1 - a0) * i / steps)
        verts += [(r0 * math.cos(a), r0 * math.sin(a)), (r1 * math.cos(a), r1 * math.sin(a))]
    faces = [[2 * i, 2 * i + 1, 2 * ((i + 1) % ring) + 1, 2 * ((i + 1) % ring)] for i in range(steps)]
    return flat(parent, name, verts, faces, material, z)


def rotated(points, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return [(x * c - y * s, x * s + y * c) for x, y in points]


# --- The puck ---------------------------------------------------------------
def import_parts(M):
    """Import every STL once; pucks are built from copies that share the mesh data."""
    mats = {"Shell": M["black"], "Plate": M["black"], "Ring": M["black"], "Cap": M["orange"], "Index": M["orange"],
            "Bezel": M["resin"], "Crystal": M["crystal"], "Panel": M["panel"], "Board": M["mask"]}
    parts = {}
    for name in PARTS:
        path = os.path.join(MESH, name + ".stl")
        if not os.path.exists(path):
            sys.exit("missing %s: run export_meshes.py first" % path)
        bpy.ops.import_mesh.stl(filepath=path, global_scale=MM)
        obj = bpy.context.selected_objects[0]
        bm = bmesh.new()
        bm.from_mesh(obj.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-7)
        bm.to_mesh(obj.data)
        bm.free()
        finish(obj, mats.get(name, M["anodised"]), smooth_angle=0 if name == "Board" else 35.0)
        obj.location = -CENTRE * MM
        parts[name] = obj
    return parts


def make_puck(name, parts, M, location=(0, 0, 0), rot_z=0.0, beacon=False):
    root = link(bpy.data.objects.new(name, None))
    root.location = location
    root.rotation_euler = (0, 0, math.radians(rot_z))
    for pname, src in parts.items():
        o = link(src.copy(), root)
        o.name = "%s_%s" % (name, pname)
        if pname == "Bezel" and beacon:
            o.material_slots[0].link = "OBJECT"
            o.material_slots[0].material = M["resin_lit"]
    if beacon:
        # The LEDs' light spilling out of the lit bezel onto the face around it.
        data = bpy.data.lights.new(name + "_beacon", "POINT")
        data.energy = 0.012
        data.shadow_soft_size = 0.012
        data.color = (1.0, 0.35, 0.08)
        lamp = link(bpy.data.objects.new(name + "_beacon", data), root)
        lamp.location = (0, 0, 13 * MM)
        lamp.visible_glossy = False
        lamp.visible_transmission = False
    return root


def make_ui(root, M, bearing, text):
    """The radar face: dim range rings, cardinal ticks (12 o'clock in orange), a sweep fading out behind the
    sweep line, the arrow, the partner blip and the distance.  bearing is degrees anticlockwise from local +X."""
    n = root.name
    z = Z_SCREEN + 0.03
    disc(root, n + "_Screen", R_ACTIVE, Z_SCREEN + 0.01, M["screen"])
    annulus(root, n + "_RingOuter", 14.6, 14.95, z, M["ui_dim"])
    annulus(root, n + "_RingInner", 8.2, 8.45, z, M["ui_dim"])
    for a in (0, 90, 180, 270):
        flat(root, n + "_Tick%d" % a, rotated([(-0.35, 13.2), (0.35, 13.2), (0.35, 15.4), (-0.35, 15.4)], a - 90),
             [[0, 1, 2, 3]], M["ui_orange"] if a == 90 else M["ui_dim"], z)
    lead = bearing + 30.0                                  # the sweep has just passed the partner's blip
    for i, mat in enumerate(M["sweep"]):
        hi = lead - 4.0 * i
        annulus(root, n + "_Sweep%d" % i, 0.0, 14.5, z - 0.005, mat, a0=hi - 4.05, a1=hi, n=360)
    arrow = [(0.0, 9.2), (4.6, -2.6), (0.0, 0.2), (-4.6, -2.6)]
    flat(root, n + "_Arrow", rotated(arrow, bearing - 90), [[0, 1, 2, 3]], M["ui_orange"], z + 0.01)
    bx, by = 12.0 * math.cos(math.radians(bearing)), 12.0 * math.sin(math.radians(bearing))
    disc(root, n + "_Blip", 1.35, z + 0.02, M["ui_orange"], cx=bx, cy=by)
    for i, mat in enumerate(M["halo"]):                    # soft glow: rings fading outwards
        r0 = 1.35 + 0.3 * i
        halo = annulus(root, n + "_BlipHalo%d" % i, r0, r0 + 0.3, z + 0.015, mat, n=64)
        halo.location = (bx * MM, by * MM, 0)
    txt = bpy.data.curves.new(n + "_Distance", "FONT")
    txt.body = text
    txt.size = 4.6 * MM
    txt.align_x = "CENTER"
    txt.align_y = "CENTER"
    txt.resolution_u = 10
    if os.path.exists(FONT):
        txt.font = bpy.data.fonts.load(FONT, check_existing=True)
    txt.materials.append(M["ui_white"])
    label = link(bpy.data.objects.new(n + "_Distance", txt), root)
    label.location = (0.0, -10.2 * MM, (z + 0.02) * MM)


def make_cord(root, M, world_dir):
    """Orange cord through the lanyard tunnel: the two ends drape out of the mouths into a barrel lock on the floor
    straight in front of the tunnel, and the loop then bends off along world_dir (world XY).  Works for a puck
    lying face up or turned over (the root's rotation says which), as long as it rests flat on the floor."""
    rot = root.rotation_euler.to_matrix()
    up = 1.0 if (rot @ Vector((0, 0, 1))).z > 0 else -1.0     # local +Z up (face up) or down (turned over)
    zf_surf = Z_BOTTOM if up > 0 else Z_FACE                   # the local Z that touches the floor
    zf = zf_surf + up * CORD_R
    zl = zf_surf + up * LOCK_R
    d = (rot.inverted() @ Vector((world_dir[0], world_dir[1], 0))).to_2d().normalized()
    ahead = Vector((0.0, -1.0))
    lock = Vector((0.0, -58.0))
    # Centre line of the loop beyond the lock (s = distance along it) and the half-spread of its two strands.
    c0 = lock + ahead * (LOCK_L / 2 + 3.0)
    c1 = c0 + 22.0 * (ahead + d).normalized()
    c2 = c1 + 45.0 * d
    c3 = c2 + 60.0 * d
    loop = [(c0, 1.3), (c1, 3.0), (c2, 5.5), (c3, 7.0)]

    def side(c, tangent, off, z):
        p = Vector((-tangent.y, tangent.x))                    # +X side when heading -Y
        q = c + off * p
        return (q.x, q.y, z)

    tangents = [ahead] + [(loop[i + 1][0] - loop[i - 1][0]).normalized() for i in range(1, 3)] + [d]
    lz = LANYARD_Z
    mid = lz + 0.5 * (zf - lz)
    right = [(9.0, LANYARD_Y, lz), (16.5, LANYARD_Y - 0.9, lz - up * 0.2), (21.0, -39.5, mid), (17.5, -47.0, zf),
             (6.0, -52.0, zf), (1.0, lock.y + LOCK_L / 2 - 0.5, zl), (1.0, lock.y - LOCK_L / 2 + 0.5, zl)]
    right += [side(c, t, off, zf) for (c, off), t in zip(loop, tangents)]
    tip = c3 + 15.0 * d
    left = [(-x, y, z) for x, y, z in right[:7]]
    left += [side(c, t, -off, zf) for (c, off), t in zip(loop, tangents)]
    pts = [(-9.0, LANYARD_Y, lz)] + right + [(tip.x, tip.y, zf)] + left[::-1][:-1]
    cu = bpy.data.curves.new(root.name + "_Cord", "CURVE")
    cu.dimensions = "3D"
    cu.bevel_depth = CORD_R * MM
    cu.bevel_resolution = 6
    cu.resolution_u = 24
    cu.twist_mode = "MINIMUM"
    sp = cu.splines.new("BEZIER")
    sp.bezier_points.add(len(pts) - 1)
    for bp, co in zip(sp.bezier_points, pts):
        bp.co = Vector(co) * MM
        bp.handle_left_type = bp.handle_right_type = "AUTO"
    sp.use_cyclic_u = True
    sp.use_smooth = True
    cu.materials.append(M["cord"])
    link(bpy.data.objects.new(root.name + "_Cord", cu), root)

    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=LOCK_R * MM, radius2=LOCK_R * MM, depth=LOCK_L * MM)
    me = bpy.data.meshes.new(root.name + "_Lock")
    bm.to_mesh(me)
    bm.free()
    obj = finish(link(bpy.data.objects.new(root.name + "_Lock", me), root), M["lock"], smooth_angle=40)
    bev = obj.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.6 * MM
    bev.segments = 4
    bev.limit_method = "ANGLE"
    obj.rotation_euler = Vector((0, 0, 1)).rotation_difference(Vector((0, -1, 0))).to_euler()
    obj.location = Vector((lock.x, lock.y, zl)) * MM


# --- Set, lights, camera ----------------------------------------------------
def make_backdrop(M):
    """Floor and a seamless sweep curving up behind."""
    bm = bmesh.new()
    profile = [(-1.5, Z_BOTTOM * MM)]
    for i in range(1, 25):
        a = math.radians(90 * i / 24)
        profile.append((0.45 + 0.4 * math.sin(a), Z_BOTTOM * MM + 0.4 * (1 - math.cos(a))))
    profile.append((0.85, Z_BOTTOM * MM + 1.6))
    rows = [[bm.verts.new((x, y, zz)) for y, zz in profile] for x in (-1.8, 1.8)]
    for i in range(len(profile) - 1):
        bm.faces.new((rows[0][i], rows[0][i + 1], rows[1][i + 1], rows[1][i]))
    me = bpy.data.meshes.new("Backdrop")
    bm.to_mesh(me)
    bm.free()
    finish(link(bpy.data.objects.new("Backdrop", me)), M["floor"], smooth_angle=60)


def make_lights(aim, rim=(-0.235, 0.58, 0.414), rim_h=0.03):
    """Powers are small because the lights sit 0.3-0.8 m from a 76 mm object.  The rim strip is a long thin
    light behind the puck; a flat crystal magnifies it into a band ~8 mm deep per degree it subtends, so for the
    hero it sits ~2 degrees under the camera's mirror angle off the crystal centre and lands on the far bezel lip."""
    def area(name, loc, size, power, color, shape="SQUARE", size_y=None, spread=None):
        data = bpy.data.lights.new(name, "AREA")
        data.shape = shape
        data.size = size
        if size_y:
            data.size_y = size_y
        if spread:
            data.spread = math.radians(spread)
        data.energy = power
        data.color = color
        obj = link(bpy.data.objects.new(name, data))
        obj.location = loc
        track = obj.constraints.new("TRACK_TO")
        track.target = aim
        track.track_axis = "TRACK_NEGATIVE_Z"
        track.up_axis = "UP_Y"
        return obj

    area("Key", (-0.30, -0.22, 0.42), 0.35, 3.5, (1.0, 0.96, 0.90), spread=45)
    area("Fill", (0.65, -0.35, 0.30), 1.2, 0.4, (0.86, 0.90, 1.0))
    area("Rim", rim, 1.2, 7.0 * 0.03 / rim_h, (1.0, 1.0, 1.0), shape="RECTANGLE", size_y=rim_h)
    area("Top", (-0.05, 0.08, 0.75), 1.6, 0.8, (1.0, 1.0, 1.0), shape="RECTANGLE", size_y=0.10)
    area("Accent", (0.55, 0.30, 0.05), 0.4, 1.0, (1.0, 0.45, 0.12))


def make_camera(scene, elev, azim, dist, look, lens=85, fstop=20.0, shift_x=0.0):
    """Camera on a sphere around `look` (mm, world): azimuth 0 looks from -Y, positive swings to +X."""
    aim = link(bpy.data.objects.new("Aim", None))
    aim.location = Vector(look) * MM
    data = bpy.data.cameras.new("Camera")
    data.lens = lens
    data.sensor_width = 36
    data.shift_x = shift_x
    data.dof.use_dof = True
    data.dof.aperture_fstop = fstop
    data.dof.focus_object = aim
    cam = link(bpy.data.objects.new("Camera", data))
    e, a = math.radians(elev), math.radians(azim)
    cam.location = aim.location + dist * Vector((math.sin(a) * math.cos(e), -math.cos(a) * math.cos(e), math.sin(e)))
    track = cam.constraints.new("TRACK_TO")
    track.target = aim
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    scene.camera = cam
    return aim


# --- Views ------------------------------------------------------------------
def view_hero(scene, parts, M):
    puck = make_puck("Puck", parts, M, rot_z=-12)
    make_ui(puck, M, bearing=52, text="38 m")
    make_cord(puck, M, (-1.0, -0.30))                       # off to the left of the frame
    return make_camera(scene, 36, 22, 0.30, (-3.0, -12.0, 0.0), shift_x=-0.04)


def view_pair(scene, parts, M):
    a_loc, b_loc = Vector((-46.0, 14.0)), Vector((46.0, -14.0))
    a_rot, b_rot = -36.87, 36.87                           # buttons turned out towards the camera
    to_b = math.degrees(math.atan2(*(b_loc - a_loc).yx))
    a = make_puck("PuckA", parts, M, location=tuple(a_loc * MM) + (0,), rot_z=a_rot, beacon=True)
    b = make_puck("PuckB", parts, M, location=tuple(b_loc * MM) + (0,), rot_z=b_rot, beacon=True)
    make_ui(a, M, bearing=to_b - a_rot, text="2 m")
    make_ui(b, M, bearing=to_b + 180 - b_rot, text="2 m")
    make_cord(a, M, (-0.9, -0.45))
    make_cord(b, M, (0.9, -0.45))
    return make_camera(scene, 46, 0, 0.50, (0.0, -6.0, 0.0), fstop=22.0)


def view_back(scene, parts, M):
    puck = make_puck("Puck", parts, M)
    # Turned over like a pancake: the face (Z 8.0) rests on the floor, 12 o'clock stays away from the camera.
    puck.rotation_euler = (math.radians(180), 0, math.radians(166))
    puck.location = (0, 0, (Z_BOTTOM + Z_FACE) * MM)
    make_cord(puck, M, (1.0, -0.35))                         # off to the right
    # A low light from behind left rakes across the underside so the deboss reads.
    graze = bpy.data.lights.new("Graze", "AREA")
    graze.shape = "RECTANGLE"
    graze.size, graze.size_y = 0.5, 0.05
    graze.energy = 2.5
    lamp = link(bpy.data.objects.new("Graze", graze))
    lamp.location = (-0.30, 0.28, 0.07)
    aim = make_camera(scene, 42, -18, 0.38, (-2.0, -24.0, 6.0))
    track = lamp.constraints.new("TRACK_TO")
    track.target = aim
    track.track_axis = "TRACK_NEGATIVE_Z"
    track.up_axis = "UP_Y"
    return aim


# Hero camera (36 deg up, 22 deg round, 0.30 m) sees the crystal centre's mirror image at 33.9 deg: rim at 31.7.
LIGHTS = {"hero": dict(rim=(-0.213, 0.575, 0.377), rim_h=0.015)}
VIEW_FUNCS = {"hero": view_hero, "pair": view_pair, "back": view_back}

os.makedirs(DOCS, exist_ok=True)
for view in VIEWS:
    if view not in VIEW_FUNCS:
        sys.exit("unknown view %r (choose from %s)" % (view, ", ".join(VIEW_FUNCS)))
    scene = setup_scene()
    M = make_materials()
    parts = import_parts(M)
    make_backdrop(M)
    aim = VIEW_FUNCS[view](scene, parts, M)
    for obj in parts.values():                             # the templates; the pucks hold copies
        bpy.data.objects.remove(obj)
    make_lights(aim, **LIGHTS.get(view, {}))
    out = os.path.join(DOCS, "finder_puck_render%s.png" % ("" if view == "hero" else "_" + view))
    scene.render.filepath = out
    bpy.ops.render.render(write_still=True)
    print("rendered", out)
    bpy.context.preferences.filepaths.save_version = 0         # no .blend1 backups next to the scenes
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(MESH, "finder_puck_%s.blend" % view))

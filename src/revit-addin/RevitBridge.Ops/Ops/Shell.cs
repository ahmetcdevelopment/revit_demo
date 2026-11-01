using RevitBridge.Revit;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.DB;
using RevitBridge.Protocol;

namespace RevitBridge.Ops;

/// <summary>create_wall: straight wall on its centre line, type picked/created from (type, thickness).</summary>
public sealed class CreateWallExecutor : OpExecutor
{
    public override string Op => "create_wall";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var p0 = Geo.Pt(a.GetProperty("a"), level.Elevation);
        var p1 = Geo.Pt(a.GetProperty("b"), level.Elevation);
        if (p0.DistanceTo(p1) < 0.05)
        {
            throw new BridgeException("bad_args", $"wall {op.SpecRef} is shorter than 15 mm", op.OpId);
        }
        var type = TypeFactory.Wall(ctx.Doc, Geo.Str(a, "type"), a.GetProperty("thickness").GetDouble());
        return Wall.Create(ctx.Doc, Line.CreateBound(p0, p1), type.Id, level.Id, Geo.M(a, "height"), 0, false, false);
    }
}

/// <summary>create_floor: slab whose top face sits on the level; inner loops are holes (stair well).</summary>
public sealed class CreateFloorExecutor : OpExecutor
{
    public override string Op => "create_floor";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var loops = new List<CurveLoop> { Geo.Loop(Geo.Ring(a.GetProperty("outline"), level.Elevation)) };
        if (a.TryGetProperty("openings", out var holes))
        {
            foreach (var h in holes.EnumerateArray())
            {
                loops.Add(Geo.Loop(Geo.Ring(h, level.Elevation)));
            }
        }
        var type = TypeFactory.Floor(ctx.Doc, a.GetProperty("thickness").GetDouble());
        return Floor.Create(ctx.Doc, loops, type.Id, level.Id);
    }
}

/// <summary>create_roof: flat footprint roof on the roof level (parapet is a known gap).</summary>
public sealed class CreateRoofExecutor : OpExecutor
{
    public override string Op => "create_roof";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var ring = Geo.Ring(a.GetProperty("outline"), level.Elevation);
        var curves = new CurveArray();
        for (var i = 0; i < ring.Count; i++)
        {
            curves.Append(Line.CreateBound(ring[i], ring[(i + 1) % ring.Count]));
        }
        var type = TypeFactory.Roof(ctx.Doc, a.GetProperty("thickness").GetDouble());
        ModelCurveArray mapping = new ModelCurveArray();
        var roof = ctx.Doc.Create.NewFootPrintRoof(curves, level, type, out mapping);
        if (roof == null)
        {
            throw new BridgeException("revit_failure", $"roof {op.SpecRef}: NewFootPrintRoof returned null", op.OpId);
        }
        return roof;
    }
}

/// <summary>create_room: placed by an interior point; the room is bounded by the walls, so a leak shows as area 0.</summary>
public sealed class CreateRoomExecutor : OpExecutor
{
    public override string Op => "create_room";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var ring = Geo.Ring(a.GetProperty("outline"), level.Elevation);
        AddSeparationLines(ctx, op, level, ring);
        var room = ctx.Doc.Create.NewRoom(level, Geo.InteriorPoint(ring))
            ?? throw new BridgeException("revit_failure", $"room {op.SpecRef} could not be placed (no enclosure?)", op.OpId);
        room.Name = Geo.Str(a, "name");
        room.Number = op.SpecRef.StartsWith("R-") ? op.SpecRef[2..] : op.SpecRef;
        return room;
    }

    /// <summary>
    /// Room edges that no wall covers (open core zones) get room separation lines, otherwise Revit
    /// merges the neighbouring rooms into one region. An edge counts as covered when its quarter points
    /// lie on a wall of the level.
    /// </summary>
    private static void AddSeparationLines(OpContext ctx, OpDto op, Level level, IReadOnlyList<XYZ> ring)
    {
        var doc = ctx.Doc;
        var walls = new FilteredElementCollector(doc).OfClass(typeof(Wall)).Cast<Wall>()
            .Where(w => w.LevelId == level.Id && w.Location is LocationCurve).ToList();
        bool Covered(XYZ p) => walls.Any(w =>
        {
            var c = ((LocationCurve)w.Location).Curve;
            var q = new XYZ(p.X, p.Y, c.GetEndPoint(0).Z);
            return c.Distance(q) <= w.Width / 2 + 0.02;
        });
        var drawn = new FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RoomSeparationLines)
            .WhereElementIsNotElementType().OfType<ModelCurve>().Select(m => m.GeometryCurve)
            .Where(c => Math.Abs(c.GetEndPoint(0).Z - level.Elevation) < 0.01).ToList();
        bool Drawn(XYZ p, XYZ q) => drawn.Any(c =>
        {
            var a = c.GetEndPoint(0);
            var b = c.GetEndPoint(1);
            return (a.DistanceTo(p) < 0.02 && b.DistanceTo(q) < 0.02) || (a.DistanceTo(q) < 0.02 && b.DistanceTo(p) < 0.02);
        });
        var open = new CurveArray();
        for (var i = 0; i < ring.Count; i++)
        {
            var p = ring[i];
            var q = ring[(i + 1) % ring.Count];
            if (Enumerable.Range(1, 9).All(k => Covered(p + (q - p) * (k / 10.0))) || Drawn(p, q))
            {
                continue;
            }
            open.Append(Line.CreateBound(p, q));
        }
        if (open.IsEmpty)
        {
            return;
        }
        var view = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
            .First(v => !v.IsTemplate && v.GenLevel?.Id == level.Id);
        var plane = SketchPlane.Create(doc, Plane.CreateByNormalAndOrigin(XYZ.BasisZ, new XYZ(0, 0, level.Elevation)));
        var lines = doc.Create.NewRoomBoundaryLines(plane, open, view);
        var n = 0;
        foreach (ModelCurve m in lines)
        {
            SpecIdStore.Set(m, $"{op.SpecRef}#sep{n++}", OpRunner.Hash(op), ctx.SpecId);
        }
    }
}

/// <summary>tag_room: a room tag (name and area) in the level's floor plan, so the plans in the report read as drawings.</summary>
public sealed class TagRoomExecutor : OpExecutor
{
    public override string Op => "tag_room";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var doc = ctx.Doc;
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var room = ctx.Require<Room>(Geo.Str(a, "room"));
        if (room.Area <= 0)
        {
            throw new BridgeException("revit_failure", $"room {room.Name} has no area (not enclosed); it cannot be tagged", op.OpId);
        }
        var view = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
            .First(v => !v.IsTemplate && v.GenLevel?.Id == level.Id);
        var at = Geo.InteriorPoint(Geo.Ring(a.GetProperty("outline"), level.Elevation));
        var tag = doc.Create.NewRoomTag(new LinkElementId(room.Id), at, view.Id);
        // RoomTagType is not queryable by class in this API version: find the symbol by category
        var type = new FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_RoomTags).OfClass(typeof(FamilySymbol))
            .Cast<FamilySymbol>().FirstOrDefault(t => t.Name == "Room Tag With Area");
        if (type != null)
        {
            tag.ChangeTypeId(type.Id);
        }
        return tag;
    }
}

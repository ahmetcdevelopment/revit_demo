using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Structure;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>
/// place_door / place_window. With a family symbol in the document the instance is hosted in the wall
/// (sized through a duplicated type). Revit 2027 ships no door/window library, so without one the wall
/// gets a real rectangular opening (companion element `ref#void`) and a DirectShape leaf/pane in the
/// Doors/Windows category; the result note says which route was taken.
/// </summary>
public sealed class PlaceOpeningExecutor : OpExecutor
{
    private readonly bool _door;

    public PlaceOpeningExecutor(string op)
    {
        Op = op;
        _door = op == "place_door";
    }

    public override string Op { get; }

    /// <summary>Families shipped with the DefaultMetric template; any other family is used if these are absent.</summary>
    private string PreferredFamily => _door ? "M_Single-Flush" : "M_Window-Casement-Double";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var doc = ctx.Doc;
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        var wall = ctx.Require<Wall>(Geo.Str(a, "host_wall"));
        var width = a.GetProperty("width").GetDouble();
        var height = a.GetProperty("height").GetDouble();
        var sill = Geo.Num(a, "sill", 0);
        var cat = _door ? BuiltInCategory.OST_Doors : BuiltInCategory.OST_Windows;
        var z0 = level.Elevation + Metric.FromMetres(sill);

        var onWall = Geo.Pt(a.GetProperty("at"), z0);

        var symbol = new FilteredElementCollector(doc).OfCategory(cat).OfClass(typeof(FamilySymbol))
            .Cast<FamilySymbol>().OrderBy(s => s.FamilyName == PreferredFamily ? 0 : 1)
            .ThenBy(s => s.FamilyName).ThenBy(s => s.Name).FirstOrDefault();
        if (symbol != null)
        {
            return PlaceInstance(ctx, op, symbol, wall, level, onWall, width, height, sill);
        }
        return PlaceFallback(ctx, op, wall, onWall, width, height, sill, cat);
    }

    private Element PlaceInstance(OpContext ctx, OpDto op, FamilySymbol baseSymbol, Wall wall, Level level,
        XYZ at, double width, double height, double sill)
    {
        var doc = ctx.Doc;
        var name = $"RB {(_door ? "Door" : "Window")} {(int)Math.Round(width * 1000)}x{(int)Math.Round(height * 1000)}";
        var symbol = new FilteredElementCollector(doc).OfClass(typeof(FamilySymbol)).Cast<FamilySymbol>()
            .FirstOrDefault(s => s.FamilyName == baseSymbol.FamilyName && s.Name == name);
        if (symbol == null)
        {
            symbol = (FamilySymbol)baseSymbol.Duplicate(name);
            SetSize(ctx, symbol, width, height);
        }
        if (!symbol.IsActive)
        {
            symbol.Activate();
            doc.Regenerate();
        }
        var inst = doc.Create.NewFamilyInstance(at, symbol, wall, level, StructuralType.NonStructural);
        inst.get_Parameter(BuiltInParameter.INSTANCE_SILL_HEIGHT_PARAM)?.Set(Metric.FromMetres(sill));
        return inst;
    }

    private void SetSize(OpContext ctx, FamilySymbol symbol, double width, double height)
    {
        void Set(BuiltInParameter bip, string lookup, double metres)
        {
            var p = symbol.get_Parameter(bip) ?? symbol.LookupParameter(lookup);
            if (p == null || p.IsReadOnly)
            {
                ctx.Notes.Add($"{symbol.FamilyName}: cannot set '{lookup}'");
                return;
            }
            p.Set(Metric.FromMetres(metres));
        }
        Set(_door ? BuiltInParameter.DOOR_WIDTH : BuiltInParameter.WINDOW_WIDTH, "Width", width);
        Set(_door ? BuiltInParameter.DOOR_HEIGHT : BuiltInParameter.WINDOW_HEIGHT, "Height", height);
    }

    private Element PlaceFallback(OpContext ctx, OpDto op, Wall wall, XYZ at, double width, double height,
        double sill, BuiltInCategory cat)
    {
        var doc = ctx.Doc;
        var curve = ((LocationCurve)wall.Location).Curve;
        var t = (curve.GetEndPoint(1) - curve.GetEndPoint(0)).Normalize();
        var n = XYZ.BasisZ.CrossProduct(t);
        var half = Metric.FromMetres(width) / 2;
        var z1 = at.Z + Metric.FromMetres(height);

        var lo = new XYZ(at.X - t.X * half, at.Y - t.Y * half, at.Z);
        var hi = new XYZ(at.X + t.X * half, at.Y + t.Y * half, z1);
        var hole = doc.Create.NewOpening(wall, lo, hi);
        SpecIdStore.Set(hole, op.SpecRef + "#void", OpRunner.Hash(op), ctx.SpecId);

        var thick = Metric.FromMetres(_door ? 0.045 : 0.025);
        var halfT = thick / 2;
        var c0 = at - t * half - n * halfT;
        var c1 = at + t * half - n * halfT;
        var c2 = at + t * half + n * halfT;
        var c3 = at - t * half + n * halfT;
        var profile = new CurveLoop();
        var pts = new[] { c0, c1, c2, c3 };
        for (var i = 0; i < 4; i++)
        {
            profile.Append(Line.CreateBound(pts[i], pts[(i + 1) % 4]));
        }
        var mat = _door
            ? TypeFactory.Material(doc, "RB Kapi Ahsap", 0x7a, 0x55, 0x33)
            : TypeFactory.Material(doc, "RB Cam", 0x9f, 0xc8, 0xe0);
        var leafHeight = Metric.FromMetres(height) - (_door ? 0.0 : 0.0);
        var solid = GeometryCreationUtilities.CreateExtrusionGeometry(
            new List<CurveLoop> { profile }, XYZ.BasisZ, leafHeight, new SolidOptions(mat, ElementId.InvalidElementId));
        var ds = DirectShape.CreateElement(doc, new ElementId(cat));
        ds.ApplicationId = "RevitBridge";
        ds.ApplicationDataId = op.SpecRef;
        ds.SetShape(new List<GeometryObject> { solid });
        ds.Name = op.SpecRef;
        if (!ctx.Notes.Contains("openings: no door/window family in this document; wall voids + DirectShape leaves used"))
        {
            ctx.Notes.Add("openings: no door/window family in this document; wall voids + DirectShape leaves used");
        }
        return ds;
    }
}

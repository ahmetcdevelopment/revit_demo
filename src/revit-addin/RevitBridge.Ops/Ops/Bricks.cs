using System.Globalization;
using System.Text.Json;
using Autodesk.Revit.DB;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>
/// create_brick_panel: the klinker skin of one exterior wall as ONE DirectShape mesh (Generic Model).
/// The Python side decides every brick span (brick.py); here each span becomes a shallow box standing
/// RELIEF proud of the wall's outer face, so the joints show the wall's mortar-coloured face between bricks.
/// The panel is cladding on top of the wall, not part of its thickness.
/// </summary>
public sealed class CreateBrickPanelExecutor : OpExecutor
{
    public const double ReliefM = 0.02;

    public override string Op => "create_brick_panel";

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var doc = ctx.Doc;
        var a = op.Args;
        var level = ctx.Require<Level>(Geo.Str(a, "level"));
        ctx.Require<Wall>(Geo.Str(a, "wall"));

        var pa = Geo.Pt(a.GetProperty("a"), level.Elevation);
        var pb = Geo.Pt(a.GetProperty("b"), level.Elevation);
        var t = (pb - pa).Normalize();
        var nArr = a.GetProperty("normal");
        var n = new XYZ(nArr[0].GetDouble(), nArr[1].GetDouble(), 0).Normalize();
        var half = Geo.M(a, "thickness") / 2;
        var relief = Metric.FromMetres(ReliefM);
        var brickH = Metric.FromMetres(a.GetProperty("brick").GetProperty("height").GetDouble());
        var layout = a.GetProperty("layout");

        var (r, g, b) = ParseColor(Geo.Str(a, "color"));
        var mat = TypeFactory.Material(doc, "RB Klinker Tugla", r, g, b);

        var builder = new TessellatedShapeBuilder();
        builder.OpenConnectedFaceSet(false);
        var faces = 0;
        var pieces = 0;
        foreach (var course in layout.GetProperty("courses").EnumerateArray())
        {
            var z0 = level.Elevation + Metric.FromMetres(course.GetProperty("z").GetDouble());
            var z1 = z0 + brickH;
            foreach (var span in course.GetProperty("u").EnumerateArray())
            {
                var u0 = Metric.FromMetres(span[0].GetDouble());
                var u1 = Metric.FromMetres(span[1].GetDouble());
                XYZ P(double u, double d, double z) =>
                    new(pa.X + t.X * u + n.X * d, pa.Y + t.Y * u + n.Y * d, z);
                var din = half;
                var dout = half + relief;
                faces += Quad(builder, mat, n, P(u0, dout, z0), P(u1, dout, z0), P(u1, dout, z1), P(u0, dout, z1));    // outer
                faces += Quad(builder, mat, XYZ.BasisZ, P(u0, din, z1), P(u1, din, z1), P(u1, dout, z1), P(u0, dout, z1)); // top
                faces += Quad(builder, mat, -XYZ.BasisZ, P(u0, din, z0), P(u1, din, z0), P(u1, dout, z0), P(u0, dout, z0)); // bottom
                faces += Quad(builder, mat, -t, P(u0, din, z0), P(u0, dout, z0), P(u0, dout, z1), P(u0, din, z1));     // left end
                faces += Quad(builder, mat, t, P(u1, din, z0), P(u1, dout, z0), P(u1, dout, z1), P(u1, din, z1));      // right end
                pieces++;
            }
        }
        builder.CloseConnectedFaceSet();
        builder.Target = TessellatedShapeBuilderTarget.Mesh;
        builder.Fallback = TessellatedShapeBuilderFallback.Salvage;
        builder.Build();
        var shape = builder.GetBuildResult().GetGeometricalObjects();

        var ds = DirectShape.CreateElement(doc, new ElementId(BuiltInCategory.OST_GenericModel));
        ds.ApplicationId = "RevitBridge";
        ds.ApplicationDataId = op.SpecRef;
        ds.SetShape(shape);
        ds.Name = op.SpecRef;
        ds.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.Set(
            $"klinker pieces={pieces}; faces={faces}; lod={Geo.Str(layout, "lod")}");
        return ds;
    }

    /// <summary>Adds one quad, wound so its normal agrees with `outward` (the order given need not be).</summary>
    private static int Quad(TessellatedShapeBuilder builder, ElementId mat, XYZ outward, XYZ p0, XYZ p1, XYZ p2, XYZ p3)
    {
        var normal = (p1 - p0).CrossProduct(p2 - p0);
        var pts = normal.DotProduct(outward) >= 0
            ? new List<XYZ> { p0, p1, p2, p3 }
            : new List<XYZ> { p3, p2, p1, p0 };
        builder.AddFace(new TessellatedFace(pts, mat));
        return 1;
    }

    private static (byte, byte, byte) ParseColor(string hex)
    {
        var h = hex.TrimStart('#');
        byte B(int i) => byte.Parse(h.AsSpan(i, 2), NumberStyles.HexNumber, CultureInfo.InvariantCulture);
        return (B(0), B(2), B(4));
    }
}

using RevitBridge.Revit;
using System.Text.Json;
using Autodesk.Revit.DB;
using RevitBridge.Protocol;

namespace RevitBridge.Ops;

/// <summary>Spec JSON (metres, local plane) to Revit geometry (feet).</summary>
public static class Geo
{
    private const double MinLengthFt = 0.01;   // Revit rejects curves shorter than ~0.8 mm; stay well clear

    public static XYZ Pt(JsonElement xy, double zFt = 0) =>
        new(Metric.FromMetres(xy[0].GetDouble()), Metric.FromMetres(xy[1].GetDouble()), zFt);

    public static double M(JsonElement args, string name) => Metric.FromMetres(args.GetProperty(name).GetDouble());

    public static double Num(JsonElement args, string name, double fallback) =>
        args.TryGetProperty(name, out var v) && v.ValueKind == JsonValueKind.Number ? v.GetDouble() : fallback;

    public static string Str(JsonElement args, string name) =>
        args.GetProperty(name).GetString() ?? throw new BridgeException("bad_args", $"'{name}' must be a string");

    public static List<XYZ> Ring(JsonElement outline, double zFt)
    {
        var pts = new List<XYZ>();
        foreach (var p in outline.EnumerateArray())
        {
            var q = Pt(p, zFt);
            if (pts.Count == 0 || pts[^1].DistanceTo(q) > MinLengthFt)
            {
                pts.Add(q);
            }
        }
        if (pts.Count > 1 && pts[0].DistanceTo(pts[^1]) <= MinLengthFt)
        {
            pts.RemoveAt(pts.Count - 1);
        }
        if (pts.Count < 3)
        {
            throw new BridgeException("bad_args", "outline needs at least 3 distinct points");
        }
        return pts;
    }

    public static CurveLoop Loop(IReadOnlyList<XYZ> ring)
    {
        var loop = new CurveLoop();
        for (var i = 0; i < ring.Count; i++)
        {
            loop.Append(Line.CreateBound(ring[i], ring[(i + 1) % ring.Count]));
        }
        return loop;
    }

    public static double Area(IReadOnlyList<XYZ> ring)
    {
        double s = 0;
        for (var i = 0; i < ring.Count; i++)
        {
            var a = ring[i];
            var b = ring[(i + 1) % ring.Count];
            s += a.X * b.Y - b.X * a.Y;
        }
        return Math.Abs(s) / 2;
    }

    /// <summary>A point guaranteed inside the polygon (area centroid, else the vertex-average, else a scan line).</summary>
    public static UV InteriorPoint(IReadOnlyList<XYZ> ring)
    {
        double a = 0, cx = 0, cy = 0;
        for (var i = 0; i < ring.Count; i++)
        {
            var p = ring[i];
            var q = ring[(i + 1) % ring.Count];
            var cross = p.X * q.Y - q.X * p.Y;
            a += cross;
            cx += (p.X + q.X) * cross;
            cy += (p.Y + q.Y) * cross;
        }
        if (Math.Abs(a) > 1e-9)
        {
            var c = new UV(cx / (3 * a), cy / (3 * a));
            if (Inside(ring, c))
            {
                return c;
            }
        }
        var avg = new UV(ring.Average(p => p.X), ring.Average(p => p.Y));
        if (Inside(ring, avg))
        {
            return avg;
        }
        var y = ring.Average(p => p.Y);
        var xs = new List<double>();
        for (var i = 0; i < ring.Count; i++)
        {
            var p = ring[i];
            var q = ring[(i + 1) % ring.Count];
            if ((p.Y <= y) != (q.Y <= y))
            {
                xs.Add(p.X + (y - p.Y) / (q.Y - p.Y) * (q.X - p.X));
            }
        }
        xs.Sort();
        return xs.Count >= 2 ? new UV((xs[0] + xs[1]) / 2, y) : avg;
    }

    public static bool Inside(IReadOnlyList<XYZ> ring, UV pt)
    {
        var inside = false;
        for (int i = 0, j = ring.Count - 1; i < ring.Count; j = i++)
        {
            var pi = ring[i];
            var pj = ring[j];
            if ((pi.Y > pt.V) != (pj.Y > pt.V) && pt.U < (pj.X - pi.X) * (pt.V - pi.Y) / (pj.Y - pi.Y) + pi.X)
            {
                inside = !inside;
            }
        }
        return inside;
    }
}

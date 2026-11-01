using System.Text.Json;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>
/// create_stair: U-stair from two straight runs and a sketched landing. A run with n risers has n-1
/// treads, so its base line is (n-1)*tread long: run 1 climbs from the zone start, the landing fills the
/// rest of the zone, run 2 comes back beside it and ends at the slab opening edge.
/// </summary>
public sealed class CreateStairExecutor : OpExecutor
{
    public override string Op => "create_stair";

    public override bool OwnsTransaction => true;

    protected override Element Create(OpContext ctx, OpDto op)
    {
        var doc = ctx.Doc;
        var a = op.Args;
        var from = ctx.Require<Level>(Geo.Str(a, "from_level"));
        var to = ctx.Require<Level>(Geo.Str(a, "to_level"));
        var runW = a.GetProperty("run_width").GetDouble();
        var well = a.GetProperty("well_width").GetDouble();
        var riserH = a.GetProperty("riser_h").GetDouble();
        var tread = a.GetProperty("tread_d").GetDouble();
        var risers = a.GetProperty("risers").EnumerateArray().Select(x => x.GetInt32()).ToArray();
        var origin = Pair(a.GetProperty("origin"));
        var dir = Pair(a.GetProperty("direction"));
        var side = Pair(a.GetProperty("side"));
        var zone = a.GetProperty("zone_length").GetDouble();
        if (risers.Length != 2)
        {
            throw new BridgeException("bad_args", "create_stair expects two runs (U-stair)", op.OpId);
        }

        // The run elevation comes from the z of its location line (relative to the base level; the
        // TopElevation/BaseElevation setters are refused above level 0, see PROGRESS "Revit tuzaklari").
        XYZ At(double u, double v, double dz = 0) => new(
            Metric.FromMetres(origin.x + side.x * u + dir.x * v),
            Metric.FromMetres(origin.y + side.y * u + dir.y * v), from.Elevation + dz);

        var lane1 = runW / 2;
        var lane2 = runW + well + runW / 2;
        var len1 = (risers[0] - 1) * tread;
        var len2 = (risers[1] - 1) * tread;
        var h1 = risers[0] * riserH;
        var h2 = (risers[0] + risers[1]) * riserH;
        var landingZ = Metric.FromMetres(h1);   // run and landing elevations are relative to the base level

        using var scope = new StairsEditScope(doc, "stair " + op.SpecRef);
        var stairsId = scope.Start(from.Id, to.Id);
        try
        {
            using var t = new Transaction(doc, "stair runs " + op.SpecRef);
            ctx.Failures.Attach(t);
            t.Start();

            var stairs = (Stairs)doc.GetElement(stairsId);
            stairs.ChangeTypeId(StairType(doc, riserH, tread).Id);
            stairs.ActualTreadDepth = Metric.FromMetres(tread);

            var run1 = StairsRun.CreateStraightRun(doc, stairsId,
                Line.CreateBound(At(lane1, 0, 0), At(lane1, len1, 0)), StairsRunJustification.Center);
            run1.ActualRunWidth = Metric.FromMetres(runW);

            var run2 = StairsRun.CreateStraightRun(doc, stairsId,
                Line.CreateBound(At(lane2, len1, landingZ), At(lane2, len1 - len2, landingZ)), StairsRunJustification.Center);
            run2.ActualRunWidth = Metric.FromMetres(runW);

            var u1 = Math.Max(0, lane1 - runW / 2);
            var u2 = lane2 + runW / 2;
            var landing = new CurveLoop();
            var corners = new[] { At(u1, len1, 0), At(u2, len1, 0), At(u2, zone, 0), At(u1, zone, 0) };
            for (var i = 0; i < 4; i++)
            {
                landing.Append(Line.CreateBound(corners[i], corners[(i + 1) % 4]));
            }
            StairsLanding.CreateSketchedLanding(doc, stairsId, landing, landingZ);

            t.Commit();
            scope.Commit(ctx.Failures);

            var made = doc.GetElement(stairsId) as Stairs;
            if (made != null)
            {
                ctx.Notes.Add($"{op.SpecRef}: stair risers {made.ActualRisersNumber} (spec {risers.Sum()}), " +
                              $"riser {Metric.ToMetres(made.ActualRiserHeight):0.0000} m (spec {riserH:0.0000}), " +
                              $"tread {Metric.ToMetres(made.ActualTreadDepth):0.000} m (spec {tread:0.000})");
            }
            return made ?? throw new BridgeException("revit_failure", "stair element missing after commit", op.OpId);
        }
        catch
        {
            if (scope.IsActive)
            {
                scope.Dispose();
            }
            throw;
        }
    }

    /// <summary>Stair type whose limits admit exactly the spec's riser/tread (Revit otherwise picks its own riser count).</summary>
    private static StairsType StairType(Document doc, double riserH, double tread)
    {
        var name = $"RB Merdiven r{(int)Math.Round(riserH * 10000)} t{(int)Math.Round(tread * 1000)}";
        var found = new FilteredElementCollector(doc).OfClass(typeof(StairsType)).Cast<StairsType>().FirstOrDefault(s => s.Name == name);
        if (found != null)
        {
            return found;
        }
        var basic = new FilteredElementCollector(doc).OfClass(typeof(StairsType)).Cast<StairsType>()
            .FirstOrDefault(s => s.Name == "190mm max riser 250mm going")
            ?? new FilteredElementCollector(doc).OfClass(typeof(StairsType)).Cast<StairsType>().First();
        var type = (StairsType)basic.Duplicate(name);
        type.MaxRiserHeight = Metric.FromMetres(riserH + 0.0005);
        type.MinTreadDepth = Metric.FromMetres(tread);   // Revit uses the minimum as the run's tread depth
        return type;
    }

    private static (double x, double y) Pair(JsonElement e) => (e[0].GetDouble(), e[1].GetDouble());
}

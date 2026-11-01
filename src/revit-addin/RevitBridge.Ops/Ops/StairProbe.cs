using System.Text.Json;
using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>
/// Debug probe: builds a throw-away straight stair between two levels with run elevations given literally
/// (metres), reads back what Revit made of them, and rolls everything back. Used to learn what
/// StairsRun.BaseElevation / TopElevation mean when the base level is not at 0.
/// </summary>
public static class StairProbe
{
    public static object Run(Document doc, JsonElement p)
    {
        var from = FindLevel(doc, p.GetProperty("from").GetString()!);
        var to = FindLevel(doc, p.GetProperty("to").GetString()!);
        var skip = p.TryGetProperty("skip", out var sk) && sk.GetBoolean();
        var baseM = skip ? 0 : p.GetProperty("base").GetDouble();
        var topM = skip ? 0 : p.GetProperty("top").GetDouble();
        var setOrder = p.TryGetProperty("top_first", out var tf) && tf.GetBoolean();

        using var group = new TransactionGroup(doc, "stair probe");
        group.Start();
        try
        {
            using var scope = new StairsEditScope(doc, "probe");
            var id = scope.Start(from.Id, to.Id);
            using var t = new Transaction(doc, "probe runs");
            t.Start();
            var y = 0.0;
            var dz = p.TryGetProperty("line_dz", out var ldz) ? Metric.FromMetres(ldz.GetDouble()) : 0.0;
            var line = Line.CreateBound(new XYZ(0, y, from.Elevation + dz), new XYZ(Metric.FromMetres(2.4), y, from.Elevation + dz));
            var run = StairsRun.CreateStraightRun(doc, id, line, StairsRunJustification.Center);
            var created = new { b = Metric.ToMetres(run.BaseElevation), t = Metric.ToMetres(run.TopElevation),
                ext_below_riser = Metric.ToMetres(run.ExtensionBelowRiserBase), ext_below_tread = Metric.ToMetres(run.ExtensionBelowTreadBase) };
            if (p.TryGetProperty("zero_ext", out var ze) && ze.GetBoolean())
            {
                run.ExtensionBelowRiserBase = 0;
                run.ExtensionBelowTreadBase = 0;
            }
            if (skip) { }
            else if (p.TryGetProperty("only_top", out var ot) && ot.GetBoolean())
            {
                run.TopElevation = Metric.FromMetres(topM);
            }
            else if (setOrder)
            {
                run.TopElevation = Metric.FromMetres(topM);
                run.BaseElevation = Metric.FromMetres(baseM);
            }
            else
            {
                run.BaseElevation = Metric.FromMetres(baseM);
                run.TopElevation = Metric.FromMetres(topM);
            }
            var after = new { b = Metric.ToMetres(run.BaseElevation), t = Metric.ToMetres(run.TopElevation) };
            t.Commit();
            scope.Commit(new BridgeFailures());
            var st = (Stairs)doc.GetElement(id);
            var bb = doc.GetElement(run.Id)?.get_BoundingBox(null);
            return new
            {
                level_from_m = Metric.ToMetres(from.Elevation), level_to_m = Metric.ToMetres(to.Elevation),
                given = new { baseM, topM }, run_on_create = created, run_after_set = after,
                stair_risers = st.ActualRisersNumber,
                bbox_z_m = bb == null ? null : new[] { Metric.ToMetres(bb.Min.Z), Metric.ToMetres(bb.Max.Z) },
            };
        }
        finally
        {
            group.RollBack();
        }
    }

    private static Level FindLevel(Document doc, string name) =>
        new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().FirstOrDefault(l => l.Name == name)
        ?? throw new BridgeException("missing_ref", $"no level '{name}'");
}

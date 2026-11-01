using Autodesk.Revit.DB;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>create_level: idempotent by spec ref (create / update elevation+name / leave alone). Adopts the template's untagged level at the same height and gives every level a floor plan view.</summary>
public sealed class CreateLevelExecutor : IOpExecutor
{
    public string Op => "create_level";

    public bool OwnsTransaction => false;

    public (Element Element, string Status) Execute(OpContext ctx, OpDto op, string opHash)
    {
        var a = op.Args;
        var name = a.GetProperty("name").GetString() ?? op.SpecRef;
        var elevation = Metric.FromMetres(a.GetProperty("elevation").GetDouble());

        if (ctx.Existing.TryGetValue(op.SpecRef, out var existing) && existing is Level level)
        {
            var tag = SpecIdStore.Get(level);
            if (tag != null && tag.Value.OpHash == opHash)
            {
                return (level, "unchanged");
            }
            level.Elevation = elevation;
            if (level.Name != name)
            {
                level.Name = UniqueName(ctx.Doc, name, level);
            }
            EnsureView(ctx.Doc, level);
            return (level, "updated");
        }

        var adopt = new FilteredElementCollector(ctx.Doc).OfClass(typeof(Level)).Cast<Level>()
            .FirstOrDefault(l => SpecIdStore.Get(l) == null && Math.Abs(l.Elevation - elevation) < 0.003);
        if (adopt != null)
        {
            adopt.Name = UniqueName(ctx.Doc, name, adopt);
            EnsureView(ctx.Doc, adopt);
            return (adopt, "created");
        }
        var created = Level.Create(ctx.Doc, elevation);
        created.Name = UniqueName(ctx.Doc, name, created);
        EnsureView(ctx.Doc, created);
        return (created, "created");
    }

    private static void EnsureView(Document doc, Level level)
    {
        var has = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
            .Any(v => !v.IsTemplate && v.ViewType == ViewType.FloorPlan && v.GenLevel?.Id == level.Id);
        if (has)
        {
            return;
        }
        var vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
            .FirstOrDefault(v => v.ViewFamily == ViewFamily.FloorPlan);
        if (vft == null)
        {
            return;
        }
        var view = ViewPlan.Create(doc, vft.Id, level.Id);
        var taken = new FilteredElementCollector(doc).OfClass(typeof(View)).Cast<View>()
            .Where(v => v.Id != view.Id).Select(v => v.Name).ToHashSet();
        var n = level.Name;
        var i = 2;
        while (taken.Contains(n))
        {
            n = $"{level.Name} ({i++})";
        }
        view.Name = n;
    }

    private static string UniqueName(Document doc, string name, Level self)
    {
        var taken = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>()
            .Where(l => l.Id != self.Id).Select(l => l.Name).ToHashSet();
        if (!taken.Contains(name))
        {
            return name;
        }
        var i = 2;
        while (taken.Contains($"{name} ({i})"))
        {
            i++;
        }
        return $"{name} ({i})";
    }
}

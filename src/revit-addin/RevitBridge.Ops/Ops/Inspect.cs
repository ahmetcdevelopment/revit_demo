using RevitBridge.Revit;
using Autodesk.Revit.DB;

namespace RevitBridge.Ops;

/// <summary>What the open document offers (types, families); used to pick strategies and for debugging.</summary>
public static class Inspect
{
    /// <summary>Boundary segments Revit computed for a room (debugging leaks and area differences).</summary>
    public static object RoomBoundary(Document doc, string specRef)
    {
        var room = RevitBridge.Revit.SpecIdStore.Index(doc).GetValueOrDefault(specRef) as Autodesk.Revit.DB.Architecture.Room
            ?? throw new RevitBridge.Protocol.BridgeException("missing_ref", $"no room '{specRef}'");
        var loops = room.GetBoundarySegments(new SpatialElementBoundaryOptions());
        return new
        {
            area_m2 = room.Area * 0.09290304,
            loops = loops.Select(l => l.Select(s =>
            {
                var c = s.GetCurve();
                var e = doc.GetElement(s.ElementId);
                return new
                {
                    a = new[] { Math.Round(Metric.ToMetres(c.GetEndPoint(0).X), 3), Math.Round(Metric.ToMetres(c.GetEndPoint(0).Y), 3) },
                    b = new[] { Math.Round(Metric.ToMetres(c.GetEndPoint(1).X), 3), Math.Round(Metric.ToMetres(c.GetEndPoint(1).Y), 3) },
                    by = e == null ? "?" : $"{e.Category?.Name}:{RevitBridge.Revit.SpecIdStore.Get(e)?.SpecRef}",
                };
            }).ToArray()).ToArray(),
        };
    }

    /// <summary>Elements whose solid intersects the element tagged `specRef` (finds unexpected cutters).</summary>
    public static object Intersecting(Document doc, string specRef)
    {
        var el = RevitBridge.Revit.SpecIdStore.Index(doc).GetValueOrDefault(specRef)
            ?? throw new RevitBridge.Protocol.BridgeException("missing_ref", $"no element '{specRef}'");
        var hits = new FilteredElementCollector(doc).WhereElementIsNotElementType()
            .WherePasses(new ElementIntersectsElementFilter(el)).ToList();
        return hits.Where(h => h.Id != el.Id).Select(h => new
        {
            category = h.Category?.Name, type = h.GetType().Name,
            spec_ref = RevitBridge.Revit.SpecIdStore.Get(h)?.SpecRef, name = h.Name, id = h.Id.Value,
        }).Take(40).ToArray();
    }

    public static object Run(Document doc)
    {
        string[] Names<T>() where T : Element =>
            new FilteredElementCollector(doc).OfClass(typeof(T)).Cast<T>().Select(e => e.Name).OrderBy(n => n).ToArray();
        string[] Symbols(BuiltInCategory c) =>
            new FilteredElementCollector(doc).OfCategory(c).OfClass(typeof(FamilySymbol)).Cast<FamilySymbol>()
                .Select(s => $"{s.FamilyName} : {s.Name}").OrderBy(n => n).ToArray();
        return new
        {
            wall_types = Names<WallType>(),
            floor_types = Names<FloorType>(),
            roof_types = Names<RoofType>(),
            stairs_types = Names<Autodesk.Revit.DB.Architecture.StairsType>(),
            door_symbols = Symbols(BuiltInCategory.OST_Doors),
            window_symbols = Symbols(BuiltInCategory.OST_Windows),
            view_family_types = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
                .Select(v => $"{v.ViewFamily}: {v.Name}").OrderBy(n => n).ToArray(),
            levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>()
                .Select(l => $"{l.Name} @ {Metric.ToMetres(l.Elevation):0.###}").ToArray(),
            phases = new FilteredElementCollector(doc).OfClass(typeof(Phase)).Cast<Phase>().Select(p => p.Name).ToArray(),
            room_tag_types = new FilteredElementCollector(doc).OfClass(typeof(FamilySymbol)).OfCategory(BuiltInCategory.OST_RoomTags)
                .Cast<FamilySymbol>().Select(s => $"{s.FamilyName} : {s.Name}").ToArray(),
        };
    }
}

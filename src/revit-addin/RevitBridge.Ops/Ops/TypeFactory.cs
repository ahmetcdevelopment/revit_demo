using RevitBridge.Revit;
using Autodesk.Revit.DB;
using RevitBridge.Protocol;

namespace RevitBridge.Ops;

/// <summary>Finds or creates the wall/floor/roof types and materials the spec asks for (RB-prefixed, single layer).</summary>
public static class TypeFactory
{
    public static ElementId Material(Document doc, string name, byte r, byte g, byte b)
    {
        var existing = new FilteredElementCollector(doc).OfClass(typeof(Material)).Cast<Material>()
            .FirstOrDefault(m => m.Name == name);
        if (existing != null)
        {
            return existing.Id;
        }
        var id = Autodesk.Revit.DB.Material.Create(doc, name);
        var mat = (Material)doc.GetElement(id);
        mat.Color = new Color(r, g, b);
        mat.Transparency = 0;
        return id;
    }

    private static ElementId MaterialFor(Document doc, string kind) => kind switch
    {
        "ext_brick" => Material(doc, "RB Derz Harci", 0xd2, 0xcb, 0xbb),   // mortar; the klinker is the brick panel
        "party" => Material(doc, "RB Komsu Brandmauer", 0x9a, 0x9a, 0x96),
        "floor" => Material(doc, "RB Doseme Beton", 0xb5, 0xb5, 0xb0),
        "roof" => Material(doc, "RB Cati", 0x6b, 0x6b, 0x70),
        _ => Material(doc, "RB Siva", 0xe8, 0xe6, 0xdf),
    };

    /// <summary>Keeps the template type's own structure (end caps etc.) but reduces it to one layer of the wanted width.</summary>
    private static CompoundStructure SingleLayer(CompoundStructure cs, double thicknessM, ElementId material)
    {
        while (cs.LayerCount > 1)
        {
            cs.DeleteLayer(cs.LayerCount - 1);
        }
        cs.SetLayerFunction(0, MaterialFunctionAssignment.Structure);
        cs.SetLayerWidth(0, Metric.FromMetres(thicknessM));
        cs.SetMaterialId(0, material);
        return cs;
    }

    private static int Mm(double metres) => (int)Math.Round(metres * 1000);

    public static WallType Wall(Document doc, string kind, double thicknessM)
    {
        var name = $"RB {kind}{(kind == "ext_brick" ? "-derz" : "")} {Mm(thicknessM)}";
        var found = new FilteredElementCollector(doc).OfClass(typeof(WallType)).Cast<WallType>()
            .FirstOrDefault(t => t.Name == name);
        if (found != null)
        {
            return found;
        }
        var basic = new FilteredElementCollector(doc).OfClass(typeof(WallType)).Cast<WallType>()
            .FirstOrDefault(t => t.Kind == WallKind.Basic)
            ?? throw new BridgeException("no_type", "no basic wall type in the template");
        var type = (WallType)basic.Duplicate(name);
        type.SetCompoundStructure(CompoundStructure.CreateSingleLayerCompoundStructure(
            MaterialFunctionAssignment.Structure, Metric.FromMetres(thicknessM), MaterialFor(doc, kind)));
        return type;
    }

    public static FloorType Floor(Document doc, double thicknessM)
    {
        var name = $"RB Doseme {Mm(thicknessM)}";
        var found = new FilteredElementCollector(doc).OfClass(typeof(FloorType)).Cast<FloorType>()
            .FirstOrDefault(t => t.Name == name);
        if (found != null)
        {
            return found;
        }
        var basic = new FilteredElementCollector(doc).OfClass(typeof(FloorType)).Cast<FloorType>()
            .FirstOrDefault(t => !t.IsFoundationSlab)
            ?? throw new BridgeException("no_type", "no floor type in the template");
        var type = (FloorType)basic.Duplicate(name);
        type.SetCompoundStructure(SingleLayer(type.GetCompoundStructure(), thicknessM, MaterialFor(doc, "floor")));
        return type;
    }

    public static RoofType Roof(Document doc, double thicknessM)
    {
        var name = $"RB Cati {Mm(thicknessM)}";
        var found = new FilteredElementCollector(doc).OfClass(typeof(RoofType)).Cast<RoofType>()
            .FirstOrDefault(t => t.Name == name);
        if (found != null)
        {
            return found;
        }
        var basic = new FilteredElementCollector(doc).OfClass(typeof(RoofType)).Cast<RoofType>().FirstOrDefault()
            ?? throw new BridgeException("no_type", "no roof type in the template");
        var type = (RoofType)basic.Duplicate(name);
        type.SetCompoundStructure(SingleLayer(type.GetCompoundStructure(), thicknessM, MaterialFor(doc, "roof")));
        return type;
    }
}

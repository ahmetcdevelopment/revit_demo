using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitBridge.Protocol;

namespace RevitBridge.Revit;

/// <summary>Exports the active project with Revit's own IFC exporter (IFC4, base quantities, common property sets).</summary>
public static class IfcExport
{
    public static object Run(UIApplication uiapp, string dir, string name, string? projectName = null,
        string? buildingName = null, string? address = null)
    {
        var doc = uiapp.ActiveUIDocument?.Document
            ?? throw new BridgeException("no_document", "no active document; call new_project first");
        Directory.CreateDirectory(dir);
        var file = Path.Combine(dir, name);
        if (File.Exists(file))
        {
            File.Delete(file);
        }

        var options = new IFCExportOptions
        {
            FileVersion = IFCVersion.IFC4,
            SpaceBoundaryLevel = 1,
            ExportBaseQuantities = true,
            WallAndColumnSplitting = false,
        };
        options.AddOption("ExportBaseQuantities", "true");
        options.AddOption("ExportIFCCommonPropertySets", "true");
        options.AddOption("ExportInternalRevitPropertySets", "false");
        options.AddOption("Export2DElements", "false");
        options.AddOption("ExportPartsAsBuildingElements", "false");
        options.AddOption("ExportRoomsInView", "false");

        // the exporter needs its own transaction; it must not run inside ours
        bool ok;
        using (var t = new Transaction(doc, "RB IFC export"))
        {
            t.Start();
            var info0 = doc.ProjectInformation;
            if (!string.IsNullOrEmpty(projectName))
            {
                info0.Name = projectName;
            }
            if (!string.IsNullOrEmpty(buildingName))
            {
                info0.BuildingName = buildingName;
            }
            if (!string.IsNullOrEmpty(address))
            {
                info0.Address = address;
            }
            ok = doc.Export(dir, Path.GetFileNameWithoutExtension(name), options);
            t.RollBack();   // the exporter may touch the document (shared parameters); keep the model as it was
        }
        var info = new FileInfo(file);
        return new { ok, path = file, exists = info.Exists, bytes = info.Exists ? info.Length : 0, version = "IFC4" };
    }
}

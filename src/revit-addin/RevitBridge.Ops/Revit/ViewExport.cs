using Autodesk.Revit.DB;
using Autodesk.Revit.UI;
using RevitBridge.Protocol;

namespace RevitBridge.Revit;

/// <summary>Creates (or refreshes) an isometric 3D view and exports it with the floor plans as PNG files.</summary>
public static class ViewExport
{
    public const string View3dName = "RB 3D";

    /// <summary>The shaded isometric view "RB 3D", created once and reused (an open view cannot be deleted).</summary>
    public static View3D Ensure3d(Document doc)
    {
        var found = new FilteredElementCollector(doc).OfClass(typeof(View3D)).Cast<View3D>()
            .FirstOrDefault(v => !v.IsTemplate && v.Name == View3dName);
        if (found != null)
        {
            return found;
        }
        using var t = new Transaction(doc, "RB 3D view");
        t.Start();
        var vft = new FilteredElementCollector(doc).OfClass(typeof(ViewFamilyType)).Cast<ViewFamilyType>()
            .First(v => v.ViewFamily == ViewFamily.ThreeDimensional);
        var view = View3D.CreateIsometric(doc, vft.Id);
        view.Name = View3dName;
        view.DisplayStyle = DisplayStyle.Shading;   // edges would outline every brick strip
        view.DetailLevel = ViewDetailLevel.Fine;
        t.Commit();
        return view;
    }

    /// <summary>Makes the 3D view the one on screen, so the person sees the building, not a floor plan.</summary>
    public static object Show3d(UIApplication uiapp)
    {
        var uidoc = uiapp.ActiveUIDocument
            ?? throw new BridgeException("no_document", "no active document; call new_project first");
        var view = Ensure3d(uidoc.Document);
        uidoc.RequestViewChange(view);
        return new { view = view.Name, id = view.Id.Value };
    }

    public static object Run(UIApplication uiapp, string dir, int pixels)
    {
        var doc = uiapp.ActiveUIDocument?.Document
            ?? throw new BridgeException("no_document", "no active document; call new_project first");
        Directory.CreateDirectory(dir);

        var view3d = Ensure3d(doc);

        var plans = new FilteredElementCollector(doc).OfClass(typeof(ViewPlan)).Cast<ViewPlan>()
            .Where(v => !v.IsTemplate && v.ViewType == ViewType.FloorPlan).OrderBy(v => v.GenLevel?.Elevation ?? 0).ToList();
        var written = new List<string>();
        foreach (var v in new List<View> { view3d }.Concat(plans))
        {
            var stem = Path.Combine(dir, Safe(v.Name));
            var opts = new ImageExportOptions
            {
                FilePath = stem,
                ZoomType = ZoomFitType.FitToPage,
                PixelSize = pixels,
                FitDirection = FitDirectionType.Horizontal,
                ExportRange = ExportRange.SetOfViews,
                HLRandWFViewsFileType = ImageFileType.PNG,
                ShadowViewsFileType = ImageFileType.PNG,
                ImageResolution = ImageResolution.DPI_150,
            };
            opts.SetViewsAndSheets(new List<ElementId> { v.Id });
            doc.ExportImage(opts);
            // Revit appends the view name / a suffix; report whatever landed next to the stem
            written.AddRange(Directory.GetFiles(dir, Path.GetFileName(stem) + "*.png"));
        }
        return new { dir, files = written.Distinct().ToArray() };
    }

    private static string Safe(string s) => string.Concat(s.Select(c => char.IsLetterOrDigit(c) ? c : '_'));
}

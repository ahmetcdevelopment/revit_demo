using Autodesk.Revit.DB;
using Autodesk.Revit.DB.Architecture;
using Autodesk.Revit.UI;
using RevitBridge.Logging;
using RevitBridge.Protocol;

namespace RevitBridge.Revit;

public static class ProjectOps
{
    private const string TemplateRoot = @"C:\ProgramData\Autodesk\RVT 2027\Templates\English";

    public static readonly string[] TemplateCandidates =
    {
        Path.Combine(TemplateRoot, "DefaultMetric.rte"),
        Path.Combine(TemplateRoot, "Default-Multi-Discipline_Metric.rte"),
    };

    /// <summary>Creates a metric project from the installed template, saves it and opens it in the UI.</summary>
    public static object NewProject(UIApplication uiapp, string savePath, string? template)
    {
        var templatePath = template ?? TemplateCandidates.FirstOrDefault(File.Exists)
            ?? throw new BridgeException("no_template", "no metric project template found under " + TemplateRoot);
        if (!File.Exists(templatePath))
        {
            throw new BridgeException("no_template", "template not found: " + templatePath);
        }
        var folder = Path.GetDirectoryName(savePath)!;
        Directory.CreateDirectory(folder);
        var app = uiapp.Application;
        savePath = FreePath(app, savePath);
        var doc = app.NewProjectDocument(templatePath);
        DropSpareTemplateLevels(doc);
        doc.SaveAs(savePath, new SaveAsOptions { OverwriteExistingFile = true });
        doc.Close(false);
        var ui = uiapp.OpenAndActivateDocument(savePath);

        // Projects the bridge made earlier in the same folder are replaced, not piled up.
        var closed = new List<string>();
        foreach (Document old in app.Documents.Cast<Document>().ToList())
        {
            if (old.IsLinked || old.IsFamilyDocument || old.PathName == ui.Document.PathName || old.IsModified
                || !string.Equals(Path.GetDirectoryName(old.PathName), folder, StringComparison.OrdinalIgnoreCase))
            {
                continue;
            }
            closed.Add(old.PathName);
            old.Close(false);
        }
        BridgeLog.Info($"new project {savePath} from {templatePath}; closed {closed.Count} older");
        return new { path = ui.Document.PathName, title = ui.Document.Title, template = templatePath, closed };
    }

    /// <summary>A file that is open in this Revit cannot be overwritten; pick "name-2.rvt" etc. then.</summary>
    private static string FreePath(Autodesk.Revit.ApplicationServices.Application app, string path)
    {
        bool Open(string p) => app.Documents.Cast<Document>().Any(d => string.Equals(d.PathName, p, StringComparison.OrdinalIgnoreCase));
        if (!Open(path))
        {
            return path;
        }
        var stem = Path.Combine(Path.GetDirectoryName(path)!, Path.GetFileNameWithoutExtension(path));
        for (var i = 2; ; i++)
        {
            var candidate = $"{stem}-{i}.rvt";
            if (!Open(candidate))
            {
                return candidate;
            }
        }
    }

    /// <summary>The template ships "Level 1" and "Level 2"; keep the lowest (the build adopts it), drop the rest.</summary>
    private static void DropSpareTemplateLevels(Document doc)
    {
        var levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>().OrderBy(l => l.Elevation).ToList();
        if (levels.Count < 2)
        {
            return;
        }
        using var t = new Transaction(doc, "drop spare template levels");
        t.Start();
        foreach (var l in levels.Skip(1))
        {
            doc.Delete(l.Id);
        }
        t.Commit();
    }

    public static object Status(UIApplication uiapp)
    {
        var app = uiapp.Application;
        var doc = uiapp.ActiveUIDocument?.Document;
        return new
        {
            revit = new { name = app.VersionName, number = app.VersionNumber, build = app.VersionBuild },
            bridge = typeof(ProjectOps).Assembly.GetName().Version?.ToString(),
            documents = app.Documents.Size,
            active = doc == null ? null : new
            {
                title = doc.Title,
                path = doc.PathName,
                active_view = uiapp.ActiveUIDocument?.ActiveView?.Name,
                active_view_type = uiapp.ActiveUIDocument?.ActiveView?.ViewType.ToString(),
                is_family = doc.IsFamilyDocument,
                levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).GetElementCount(),
            },
            templates = TemplateCandidates.Where(File.Exists).ToArray(),
        };
    }

    /// <summary>What is in the model, per spec ref where tagged, so the Python side can compare against the spec.</summary>
    public static object ReadBack(UIApplication uiapp)
    {
        var doc = uiapp.ActiveUIDocument?.Document
            ?? throw new BridgeException("no_document", "no active document; call new_project first");
        int Count(BuiltInCategory c) =>
            new FilteredElementCollector(doc).OfCategory(c).WhereElementIsNotElementType().GetElementCount();
        double SqM(double sqFt) => Math.Round(sqFt * 0.09290304, 4);
        var tagged = SpecIdStore.Index(doc);
        string? Ref(Element e) => SpecIdStore.Get(e)?.SpecRef;

        var walls = new FilteredElementCollector(doc).OfClass(typeof(Wall)).Cast<Wall>().ToList();
        var floors = new FilteredElementCollector(doc).OfClass(typeof(Floor)).Cast<Floor>().ToList();
        var rooms = new FilteredElementCollector(doc).OfCategory(BuiltInCategory.OST_Rooms).WhereElementIsNotElementType()
            .Cast<Room>().ToList();
        var stairs = new FilteredElementCollector(doc).OfClass(typeof(Stairs)).Cast<Stairs>().ToList();
        var openings = new[] { BuiltInCategory.OST_Doors, BuiltInCategory.OST_Windows }
            .SelectMany(c => new FilteredElementCollector(doc).OfCategory(c).WhereElementIsNotElementType())
            .Select(e => new { spec_ref = Ref(e), category = e.Category?.Name }).ToList();

        return new
        {
            title = doc.Title,
            counts = new
            {
                levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).GetElementCount(),
                walls = Count(BuiltInCategory.OST_Walls),
                floors = Count(BuiltInCategory.OST_Floors),
                rooms = Count(BuiltInCategory.OST_Rooms),
                doors = Count(BuiltInCategory.OST_Doors),
                windows = Count(BuiltInCategory.OST_Windows),
                stairs = Count(BuiltInCategory.OST_Stairs),
                roofs = Count(BuiltInCategory.OST_Roofs),
                room_tags = Count(BuiltInCategory.OST_RoomTags),
            },
            tagged = tagged.Count,
            warnings = doc.GetWarnings().Count,
            warning_kinds = doc.GetWarnings().GroupBy(w => w.GetDescriptionText())
                .Select(g => new { text = g.Key, count = g.Count() }).OrderByDescending(g => g.count).ToArray(),
            levels = new FilteredElementCollector(doc).OfClass(typeof(Level)).Cast<Level>()
                .OrderBy(l => l.Elevation)
                .Select(l => new { name = l.Name, elevation_m = Math.Round(Metric.ToMetres(l.Elevation), 4), spec_ref = Ref(l) }).ToArray(),
            walls = walls.Select(w => new
            {
                spec_ref = Ref(w),
                // location line, not the "Length" parameter (that one includes join extensions)
                length_m = Math.Round(Metric.ToMetres((w.Location as LocationCurve)?.Curve.Length ?? 0), 4),
                thickness_m = Math.Round(Metric.ToMetres(w.Width), 4),
                height_m = Math.Round(Metric.ToMetres(w.get_Parameter(BuiltInParameter.WALL_USER_HEIGHT_PARAM)?.AsDouble() ?? 0), 4),
            }).ToArray(),
            floors = floors.Select(f => new
            {
                spec_ref = Ref(f),
                area_m2 = SqM(f.get_Parameter(BuiltInParameter.HOST_AREA_COMPUTED)?.AsDouble() ?? 0),
            }).ToArray(),
            rooms = rooms.Select(r => new
            {
                spec_ref = Ref(r), name = r.Name, area_m2 = SqM(r.Area), placed = r.Location != null,
            }).ToArray(),
            stairs = stairs.Select(s => new
            {
                spec_ref = Ref(s), risers = s.ActualRisersNumber,
                riser_h_m = Math.Round(Metric.ToMetres(s.ActualRiserHeight), 4),
                tread_d_m = Math.Round(Metric.ToMetres(s.ActualTreadDepth), 4),
                // where the stair really stands (runs only, not the railings): lowest and highest run surface
                z_min_m = Math.Round(Metric.ToMetres(s.GetStairsRuns().Select(r => doc.GetElement(r)).Min(r => r.get_BoundingBox(null)!.Min.Z)), 3),
                z_max_m = Math.Round(Metric.ToMetres(s.GetStairsRuns().Select(r => doc.GetElement(r)).Max(r => r.get_BoundingBox(null)!.Max.Z)), 3),
            }).ToArray(),
            openings,
            brick_panels = SpecIdStore.Index(doc).Where(kv => kv.Key.StartsWith("BP-") && kv.Value is DirectShape)
                .Select(kv => new { spec_ref = kv.Key, comments = kv.Value.get_Parameter(BuiltInParameter.ALL_MODEL_INSTANCE_COMMENTS)?.AsString() })
                .ToArray(),
        };
    }
}

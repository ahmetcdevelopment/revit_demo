using System.Text.Json;
using Autodesk.Revit.UI;
using RevitBridge.Ops;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge;

/// <summary>Single entry point the host calls by reflection (see Hot/OpsLoader.cs). Runs on the Revit thread.</summary>
public static class Entry
{
    public static IReadOnlyCollection<string> SupportedOps() => OpRunner.SupportedOps;

    public static object? Handle(string method, JsonElement p, UIApplication app)
    {
        switch (method)
        {
            case "status":
                return ProjectOps.Status(app);
            case "new_project":
                var path = p.GetProperty("path").GetString() ?? throw new BridgeException("bad_request", "path required");
                var template = p.TryGetProperty("template", out var t) && t.ValueKind == JsonValueKind.String ? t.GetString() : null;
                return ProjectOps.NewProject(app, path, template);
            case "apply_ops":
                var ap = p.Deserialize<ApplyParams>(Json.Options) ?? throw new BridgeException("bad_request", "ops required");
                return OpRunner.Apply(ActiveDoc(app), ap);
            case "read_back":
                return ProjectOps.ReadBack(app);
            case "export_views":
                var dir = p.GetProperty("dir").GetString() ?? throw new BridgeException("bad_request", "dir required");
                var px = p.TryGetProperty("pixels", out var pxv) && pxv.ValueKind == JsonValueKind.Number ? pxv.GetInt32() : 1800;
                return ViewExport.Run(app, dir, px);
            case "show_3d":
                return ViewExport.Show3d(app);
            case "export_ifc":
                string? Opt(string key) => p.TryGetProperty(key, out var v) && v.ValueKind == JsonValueKind.String ? v.GetString() : null;
                return IfcExport.Run(app, p.GetProperty("dir").GetString()!, Opt("name") ?? "revit.ifc",
                    Opt("project_name"), Opt("building_name"), Opt("address"));
            case "stair_probe":
                return StairProbe.Run(ActiveDoc(app), p);
            case "intersecting":
                return Inspect.Intersecting(ActiveDoc(app), p.GetProperty("spec_ref").GetString()!);
            case "room_boundary":
                return Inspect.RoomBoundary(ActiveDoc(app), p.GetProperty("spec_ref").GetString()!);
            case "inspect":
                return Inspect.Run(ActiveDoc(app));
            default:
                throw new BridgeException("unknown_method", $"unknown method '{method}'");
        }
    }

    private static Autodesk.Revit.DB.Document ActiveDoc(UIApplication app) =>
        app.ActiveUIDocument?.Document ?? throw new BridgeException("no_document", "no active document; call new_project first");
}

using Autodesk.Revit.DB;
using Autodesk.Revit.DB.ExtensibleStorage;

namespace RevitBridge.Revit;

/// <summary>
/// Writes the spec id of every element the bridge creates into ExtensibleStorage, so a later
/// `apply` can reconcile (skip / update / delete) instead of rebuilding (decision D06).
/// </summary>
public static class SpecIdStore
{
    public static readonly Guid SchemaGuid = new("c1f6a7de-2b3e-4f1a-8d49-5e0b7a9c3d21");

    public static Schema GetSchema()
    {
        var schema = Schema.Lookup(SchemaGuid);
        if (schema != null)
        {
            return schema;
        }
        var b = new SchemaBuilder(SchemaGuid);
        b.SetSchemaName("RevitBridgeSpec");
        b.SetDocumentation("Spec id and op hash of an element built by RevitBridge");
        b.SetReadAccessLevel(AccessLevel.Public);
        b.SetWriteAccessLevel(AccessLevel.Public);
        b.AddSimpleField("SpecRef", typeof(string));
        b.AddSimpleField("OpHash", typeof(string));
        b.AddSimpleField("SpecId", typeof(string));
        return b.Finish();
    }

    public static void Set(Element element, string specRef, string opHash, string specId)
    {
        var schema = GetSchema();
        var entity = new Entity(schema);
        entity.Set("SpecRef", specRef);
        entity.Set("OpHash", opHash);
        entity.Set("SpecId", specId);
        element.SetEntity(entity);
    }

    public static (string SpecRef, string OpHash, string SpecId)? Get(Element element)
    {
        var entity = element.GetEntity(GetSchema());
        if (entity == null || !entity.IsValid())
        {
            return null;
        }
        return (entity.Get<string>("SpecRef"), entity.Get<string>("OpHash"), entity.Get<string>("SpecId"));
    }

    /// <summary>All elements tagged by the bridge, keyed by spec ref.</summary>
    public static Dictionary<string, Element> Index(Document doc)
    {
        var map = new Dictionary<string, Element>();
        var filter = new ExtensibleStorageFilter(SchemaGuid);
        foreach (var e in new FilteredElementCollector(doc).WherePasses(filter))
        {
            var tag = Get(e);
            if (tag != null)
            {
                map[tag.Value.SpecRef] = e;
            }
        }
        return map;
    }
}

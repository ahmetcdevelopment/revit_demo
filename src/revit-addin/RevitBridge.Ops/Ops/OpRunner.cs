using System.Security.Cryptography;
using System.Text;
using Autodesk.Revit.DB;
using RevitBridge.Protocol;
using RevitBridge.Revit;

namespace RevitBridge.Ops;

/// <summary>Everything an op executor needs.</summary>
public sealed class OpContext
{
    public required Document Doc { get; init; }
    public required string SpecId { get; init; }
    public required BridgeFailures Failures { get; init; }
    public required Dictionary<string, Element> Existing { get; init; }   // spec ref -> element (tagged, before this run)
    public Dictionary<string, ElementId> Created { get; } = new();         // spec ref -> element id (this run)
    public HashSet<string> Changed { get; } = new();                       // spec refs created/updated this run
    public List<string> Notes { get; } = new();

    /// <summary>The element a spec ref currently stands for (this run first, then the existing model).</summary>
    public Element? Resolve(string specRef)
    {
        if (Created.TryGetValue(specRef, out var id) && Doc.GetElement(id) is { } e)
        {
            return e;
        }
        return Existing.TryGetValue(specRef, out var ex) && ex.IsValidObject ? ex : null;
    }

    public T Require<T>(string specRef) where T : Element =>
        Resolve(specRef) as T ?? throw new BridgeException("missing_ref", $"'{specRef}' is not a {typeof(T).Name} in the model");
}

public interface IOpExecutor
{
    string Op { get; }

    /// <summary>True when the executor opens its own transactions (e.g. StairsEditScope).</summary>
    bool OwnsTransaction { get; }

    /// <summary>Create/update the element. Returns (element, status).</summary>
    (Element Element, string Status) Execute(OpContext ctx, OpDto op, string opHash);
}

/// <summary>Reconcile skeleton: unchanged -> keep; changed -> delete + recreate; missing -> create.</summary>
public abstract class OpExecutor : IOpExecutor
{
    public abstract string Op { get; }

    public virtual bool OwnsTransaction => false;

    public (Element Element, string Status) Execute(OpContext ctx, OpDto op, string opHash)
    {
        if (ctx.Existing.TryGetValue(op.SpecRef, out var existing) && existing.IsValidObject)
        {
            var tag = SpecIdStore.Get(existing);
            var depsChanged = op.DependsOn.Any(ctx.Changed.Contains);
            if (tag != null && tag.Value.OpHash == opHash && !depsChanged)
            {
                return (existing, "unchanged");
            }
            Remove(ctx, op, existing);
            return (Create(ctx, op), "updated");
        }
        return (Create(ctx, op), "created");
    }

    protected virtual void Remove(OpContext ctx, OpDto op, Element existing)
    {
        if (OwnsTransaction)
        {
            using var t = new Transaction(ctx.Doc, "remove " + op.SpecRef);
            ctx.Failures.Attach(t);
            t.Start();
            DeleteWithCompanions(ctx, op, existing);
            t.Commit();
        }
        else
        {
            DeleteWithCompanions(ctx, op, existing);
        }
    }

    private static void DeleteWithCompanions(OpContext ctx, OpDto op, Element existing)
    {
        // companions are tagged "<ref>#void" (wall opening) or "<ref>#sepN" (room separation lines)
        foreach (var (key, companion) in ctx.Existing.Where(kv => kv.Key.StartsWith(op.SpecRef + "#")).ToList())
        {
            if (companion.IsValidObject)
            {
                ctx.Doc.Delete(companion.Id);
            }
        }
        if (existing.IsValidObject)
        {
            ctx.Doc.Delete(existing.Id);
        }
    }

    protected abstract Element Create(OpContext ctx, OpDto op);
}

/// <summary>
/// Applies an op list atomically: one TransactionGroup; any failure rolls everything back, so the
/// model is either fully updated or untouched (a single Undo in the Revit UI as well).
/// </summary>
public static class OpRunner
{
    private static readonly Dictionary<string, IOpExecutor> Executors = new IOpExecutor[]
    {
        new CreateLevelExecutor(), new CreateWallExecutor(), new CreateFloorExecutor(), new CreateRoomExecutor(),
        new CreateStairExecutor(), new CreateRoofExecutor(), new CreateBrickPanelExecutor(), new TagRoomExecutor(), new PlaceOpeningExecutor("place_door"),
        new PlaceOpeningExecutor("place_window"),
    }.ToDictionary(e => e.Op);

    public static IReadOnlyCollection<string> SupportedOps => Executors.Keys;

    /// <summary>Bump when an executor's output changes, so elements built by older code are rebuilt on the next apply.</summary>
    public const string Revision = "p6-4";

    public static string Hash(OpDto op) => Convert.ToHexString(
        SHA256.HashData(Encoding.UTF8.GetBytes(Revision + "|" + op.Op + "|" + op.SpecRef + "|" + op.Args.GetRawText()))).Substring(0, 16);

    public static ApplyResult Apply(Document doc, ApplyParams p)
    {
        // validate everything before touching the model
        foreach (var op in p.Ops)
        {
            if (!Executors.ContainsKey(op.Op))
            {
                throw new BridgeException("unsupported_op",
                    $"op '{op.Op}' is not implemented yet (supported: {string.Join(", ", SupportedOps)})", op.OpId);
            }
        }
        var seen = new HashSet<string>();
        foreach (var op in p.Ops)
        {
            foreach (var dep in op.DependsOn)
            {
                if (!seen.Contains(dep))
                {
                    throw new BridgeException("bad_order", $"op {op.OpId} depends on {dep} which is not applied before it", op.OpId);
                }
            }
            seen.Add(op.SpecRef);
        }

        var result = new ApplyResult { DryRun = p.DryRun };
        var failures = new BridgeFailures();
        var ctx = new OpContext { Doc = doc, SpecId = p.SpecId, Failures = failures, Existing = SpecIdStore.Index(doc) };

        using var group = new TransactionGroup(doc, "RevitBridge apply");
        group.Start();
        try
        {
            foreach (var op in p.Ops)
            {
                var executor = Executors[op.Op];
                var hash = Hash(op);
                Element element;
                string status;
                try
                {
                    if (executor.OwnsTransaction)
                    {
                        (element, status) = executor.Execute(ctx, op, hash);
                        if (status != "unchanged")
                        {
                            Tag(ctx, op, element, hash);
                        }
                    }
                    else
                    {
                        using var t = new Transaction(doc, $"{op.Op} {op.SpecRef}");
                        failures.Attach(t);
                        t.Start();
                        (element, status) = executor.Execute(ctx, op, hash);
                        if (status != "unchanged")
                        {
                            SpecIdStore.Set(element, op.SpecRef, hash, p.SpecId);
                        }
                        if (t.Commit() != TransactionStatus.Committed)
                        {
                            throw new BridgeException("revit_failure",
                                $"{op.Op} {op.SpecRef}: {string.Join("; ", failures.Errors.DefaultIfEmpty("transaction not committed"))}", op.OpId);
                        }
                    }
                }
                catch (BridgeException ex) when (ex.OpId == null)
                {
                    throw new BridgeException(ex.Code, ex.Message, op.OpId);
                }
                catch (BridgeException)
                {
                    throw;
                }
                catch (Exception ex) when (ex is not OperationCanceledException)
                {
                    throw new BridgeException("revit_failure", $"{op.Op} {op.SpecRef}: {ex.GetType().Name}: {ex.Message}", op.OpId);
                }
                if (failures.Errors.Count > 0)
                {
                    throw new BridgeException("revit_failure",
                        $"{op.Op} {op.SpecRef}: {string.Join("; ", failures.Errors)}", op.OpId);
                }
                ctx.Created[op.SpecRef] = element.Id;
                if (status != "unchanged")
                {
                    ctx.Changed.Add(op.SpecRef);
                }
                result.Results.Add(new OpResult
                {
                    OpId = op.OpId, SpecRef = op.SpecRef, Status = status, ElementId = element.Id.Value,
                });
                switch (status)
                {
                    case "created": result.Created++; break;
                    case "updated": result.Updated++; break;
                    default: result.Unchanged++; break;
                }
            }
            if (p.Prune)
            {
                result.Deleted = Prune(ctx, p);
            }
            // Revit can drop an element later (join cleanup, degenerate geometry) although its op succeeded.
            var vanished = result.Results.Where(r => r.ElementId != null && doc.GetElement(new ElementId(r.ElementId.Value)) == null)
                .Select(r => r.SpecRef).ToList();
            if (vanished.Count > 0)
            {
                throw new BridgeException("element_vanished",
                    $"{vanished.Count} element(s) built by this apply no longer exist in the model: " +
                    string.Join(", ", vanished.Take(8)) + (vanished.Count > 8 ? ", ..." : ""));
            }
            if (p.DryRun)
            {
                group.RollBack();
            }
            else
            {
                group.Assimilate();
            }
        }
        catch
        {
            if (group.GetStatus() == TransactionStatus.Started)
            {
                group.RollBack();
            }
            throw;
        }
        result.Warnings.AddRange(failures.Warnings.Distinct());
        result.Warnings.AddRange(ctx.Notes);
        return result;
    }

    private static void Tag(OpContext ctx, OpDto op, Element element, string hash)
    {
        using var t = new Transaction(ctx.Doc, "tag " + op.SpecRef);
        ctx.Failures.Attach(t);
        t.Start();
        SpecIdStore.Set(element, op.SpecRef, hash, ctx.SpecId);
        t.Commit();
    }

    private static int Prune(OpContext ctx, ApplyParams p)
    {
        var keep = p.Ops.Select(o => o.SpecRef).ToHashSet();
        var doomed = ctx.Existing.Where(kv => !keep.Contains(kv.Key) && !keep.Contains(kv.Key.Split('#')[0]))
            .Select(kv => kv.Value).Where(e => e.IsValidObject).ToList();
        using var t = new Transaction(ctx.Doc, "prune");
        ctx.Failures.Attach(t);
        t.Start();
        var n = 0;
        foreach (var e in doomed)
        {
            if (e.IsValidObject)
            {
                ctx.Doc.Delete(e.Id);
                n++;
            }
        }
        t.Commit();
        return n;
    }
}

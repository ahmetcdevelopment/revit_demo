using Autodesk.Revit.DB;

namespace RevitBridge.Revit;

/// <summary>
/// Collects Revit warnings (and deletes them so no modal dialog blocks the bridge); real errors
/// roll the transaction back.
/// </summary>
public sealed class BridgeFailures : IFailuresPreprocessor
{
    public List<string> Warnings { get; } = new();
    public List<string> Errors { get; } = new();

    public FailureProcessingResult PreprocessFailures(FailuresAccessor accessor)
    {
        var resolved = false;
        foreach (var f in accessor.GetFailureMessages())
        {
            var text = f.GetDescriptionText();
            if (f.GetSeverity() == FailureSeverity.Warning)
            {
                Warnings.Add(text);
                accessor.DeleteWarning(f);
            }
            else if (f.HasResolutions())
            {
                // e.g. "Can't keep elements joined": take Revit's default fix and keep a record of it
                accessor.ResolveFailure(f);
                Warnings.Add("auto-resolved: " + text);
                resolved = true;
            }
            else
            {
                Errors.Add(text);
            }
        }
        if (Errors.Count > 0)
        {
            return FailureProcessingResult.ProceedWithRollBack;
        }
        return resolved ? FailureProcessingResult.ProceedWithCommit : FailureProcessingResult.Continue;
    }

    public void Attach(Transaction t)
    {
        var options = t.GetFailureHandlingOptions();
        options.SetFailuresPreprocessor(this);
        options.SetClearAfterRollback(true);
        t.SetFailureHandlingOptions(options);
    }
}

using System.Collections.Concurrent;
using Autodesk.Revit.UI;
using RevitBridge.Logging;
using RevitBridge.Protocol;

namespace RevitBridge.Threading;

/// <summary>
/// The Revit API is single-threaded. RPC threads enqueue work here; the work runs on Revit's main
/// thread, either from the ExternalEvent or from the Idling event, and the RPC thread awaits the result
/// through a TaskCompletionSource.
/// </summary>
public sealed class CommandQueue : IExternalEventHandler
{
    private sealed class Job
    {
        public required string Name { get; init; }
        public required Func<UIApplication, object?> Work { get; init; }
        public required TaskCompletionSource<object?> Tcs { get; init; }
        public volatile bool Cancelled;
    }

    // Switching the active document (new_project) is refused by Revit inside the Idling event, so such
    // jobs wait in their own queue that only the ExternalEvent drains.
    private readonly ConcurrentQueue<Job> _queue = new();
    private readonly ConcurrentQueue<Job> _eventOnly = new();
    private ExternalEvent? _event;

    public bool IsEmpty => _queue.IsEmpty && _eventOnly.IsEmpty;

    public void Attach(ExternalEvent ev) => _event = ev;

    public async Task<object?> RunAsync(string name, Func<UIApplication, object?> work, TimeSpan timeout,
        bool externalEventOnly = false)
    {
        var job = new Job
        {
            Name = name,
            Work = work,
            Tcs = new TaskCompletionSource<object?>(TaskCreationOptions.RunContinuationsAsynchronously),
        };
        (externalEventOnly ? _eventOnly : _queue).Enqueue(job);
        _event?.Raise();
        try
        {
            return await job.Tcs.Task.WaitAsync(timeout).ConfigureAwait(false);
        }
        catch (TimeoutException)
        {
            job.Cancelled = true;   // never run it late: the caller already gave up
            throw new BridgeException("timeout",
                $"Revit did not run '{name}' within {timeout.TotalSeconds:0}s (a modal dialog may be open).");
        }
    }

    /// <summary>Runs on Revit's main thread (ExternalEvent).</summary>
    public void Execute(UIApplication app)
    {
        Drain(app, _eventOnly);
        Drain(app);
    }

    public string GetName() => "RevitBridge.CommandQueue";

    /// <summary>Runs on Revit's main thread (ExternalEvent or Idling).</summary>
    public void Drain(UIApplication app) => Drain(app, _queue);

    private static void Drain(UIApplication app, ConcurrentQueue<Job> queue)
    {
        while (queue.TryDequeue(out var job))
        {
            if (job.Cancelled)
            {
                continue;
            }
            try
            {
                BridgeLog.Info($"run '{job.Name}' on revit thread");
                job.Tcs.TrySetResult(job.Work(app));
            }
            catch (Exception ex)
            {
                BridgeLog.Error(job.Name, ex);
                job.Tcs.TrySetException(ex);
            }
        }
    }
}

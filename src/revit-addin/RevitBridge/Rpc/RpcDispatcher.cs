using RevitBridge.Hot;
using RevitBridge.Protocol;
using RevitBridge.Threading;

namespace RevitBridge.Rpc;

/// <summary>
/// `ping` is answered here; every other method runs on the Revit thread inside the hot-reloaded
/// RevitBridge.Ops assembly (see Entry.Handle there).
/// </summary>
public sealed class RpcDispatcher
{
    private static readonly TimeSpan Timeout = TimeSpan.FromSeconds(600);
    private readonly CommandQueue _queue;

    public RpcDispatcher(CommandQueue queue) => _queue = queue;

    public async Task<RpcResponse> Handle(RpcRequest r)
    {
        object? result = r.Method == "ping"
            ? new { pong = true, time = DateTime.UtcNow, pid = Environment.ProcessId, ops = OpsLoader.SupportedOps(), ops_version = OpsLoader.Version }
            : await _queue.RunAsync(r.Method, app => OpsLoader.Invoke(r.Method, r.Params, app), Timeout,
                externalEventOnly: r.Method == "new_project");
        return new RpcResponse { Ok = true, Result = result };
    }
}

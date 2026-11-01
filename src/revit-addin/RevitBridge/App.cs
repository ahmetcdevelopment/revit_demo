using System.Security.Cryptography;
using System.Text.Json;
using Autodesk.Revit.UI;
using RevitBridge.Logging;
using RevitBridge.Rpc;
using RevitBridge.Threading;

namespace RevitBridge;

/// <summary>Revit entry point: starts the loopback RPC server and wires the main-thread queue.</summary>
public sealed class App : IExternalApplication
{
    private RpcServer? _server;
    private CommandQueue? _queue;

    public static string EndpointPath => Path.Combine(BridgeLog.Dir, "endpoint.json");

    public Result OnStartup(UIControlledApplication application)
    {
        try
        {
            _queue = new CommandQueue();
            var ev = ExternalEvent.Create(_queue);
            _queue.Attach(ev);
            // Idling keeps draining even when no UI activity happens (ExternalEvent can be delayed).
            application.Idling += (sender, e) =>
            {
                if (!_queue.IsEmpty && sender is UIApplication ui)
                {
                    _queue.Drain(ui);
                }
            };

            var token = Convert.ToHexString(RandomNumberGenerator.GetBytes(24));
            var dispatcher = new RpcDispatcher(_queue);
            _server = new RpcServer(dispatcher.Handle, token);
            _server.Start();

            Directory.CreateDirectory(BridgeLog.Dir);
            File.WriteAllText(EndpointPath, JsonSerializer.Serialize(new
            {
                port = _server.Port,
                token,
                pid = Environment.ProcessId,
                revit = application.ControlledApplication.VersionNumber,
                started = DateTime.UtcNow,
            }));
            BridgeLog.Info($"RevitBridge started, revit {application.ControlledApplication.VersionName}");
            return Result.Succeeded;
        }
        catch (Exception ex)
        {
            BridgeLog.Error("startup", ex);
            TaskDialog.Show("RevitBridge", "RevitBridge could not start: " + ex.Message);
            return Result.Failed;
        }
    }

    public Result OnShutdown(UIControlledApplication application)
    {
        _server?.Dispose();
        try
        {
            File.Delete(EndpointPath);
        }
        catch
        {
            // best effort
        }
        BridgeLog.Info("RevitBridge stopped");
        return Result.Succeeded;
    }
}

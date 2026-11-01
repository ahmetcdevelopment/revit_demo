using System.Reflection;
using System.Runtime.ExceptionServices;
using System.Runtime.Loader;
using System.Text.Json;
using Autodesk.Revit.UI;
using RevitBridge.Logging;

namespace RevitBridge.Hot;

/// <summary>
/// Loads RevitBridge.Ops.dll from bytes into a collectible context and reloads it whenever the file
/// changes, so executors can be rebuilt and tried without restarting Revit.
/// </summary>
public static class OpsLoader
{
    private sealed class OpsContext : AssemblyLoadContext
    {
        private readonly AssemblyLoadContext _host;

        public OpsContext(AssemblyLoadContext host) : base("RevitBridge.Ops", isCollectible: true) => _host = host;

        protected override Assembly? Load(AssemblyName name)
        {
            if (name.Name == typeof(OpsLoader).Assembly.GetName().Name)
            {
                return typeof(OpsLoader).Assembly;
            }
            try
            {
                return _host.LoadFromAssemblyName(name);
            }
            catch
            {
                return null;
            }
        }
    }

    private static readonly object Gate = new();
    private static OpsContext? _context;
    private static MethodInfo? _handle;
    private static MethodInfo? _supported;
    private static (DateTime Stamp, long Length) _loaded;

    public static string OpsPath => Path.Combine(
        Path.GetDirectoryName(typeof(OpsLoader).Assembly.Location)!, "RevitBridge.Ops.dll");

    public static string Version { get; private set; } = "";

    private static void EnsureLoaded()
    {
        var info = new FileInfo(OpsPath);
        if (!info.Exists)
        {
            throw new Protocol.BridgeException("ops_missing", "RevitBridge.Ops.dll not found next to the add-in: " + OpsPath);
        }
        lock (Gate)
        {
            if (_handle != null && _loaded == (info.LastWriteTimeUtc, info.Length))
            {
                return;
            }
            var host = AssemblyLoadContext.GetLoadContext(typeof(OpsLoader).Assembly) ?? AssemblyLoadContext.Default;
            var ctx = new OpsContext(host);
            using var dll = new MemoryStream(File.ReadAllBytes(OpsPath));
            var pdbPath = Path.ChangeExtension(OpsPath, ".pdb");
            Assembly asm;
            if (File.Exists(pdbPath))
            {
                using var pdb = new MemoryStream(File.ReadAllBytes(pdbPath));
                asm = ctx.LoadFromStream(dll, pdb);
            }
            else
            {
                asm = ctx.LoadFromStream(dll);
            }
            var entry = asm.GetType("RevitBridge.Entry", throwOnError: true)!;
            _handle = entry.GetMethod("Handle", BindingFlags.Public | BindingFlags.Static)!;
            _supported = entry.GetMethod("SupportedOps", BindingFlags.Public | BindingFlags.Static)!;
            var old = _context;
            _context = ctx;
            _loaded = (info.LastWriteTimeUtc, info.Length);
            Version = $"{info.LastWriteTimeUtc:HH:mm:ss}/{info.Length}";
            BridgeLog.Info($"ops loaded {Version}");
            old?.Unload();
        }
    }

    public static IReadOnlyCollection<string> SupportedOps()
    {
        EnsureLoaded();
        return (IReadOnlyCollection<string>)_supported!.Invoke(null, null)!;
    }

    /// <summary>Runs on the Revit thread (called from the command queue).</summary>
    public static object? Invoke(string method, JsonElement args, UIApplication app)
    {
        EnsureLoaded();
        try
        {
            return _handle!.Invoke(null, new object[] { method, args, app });
        }
        catch (TargetInvocationException ex) when (ex.InnerException != null)
        {
            ExceptionDispatchInfo.Capture(ex.InnerException).Throw();
            throw;
        }
    }
}

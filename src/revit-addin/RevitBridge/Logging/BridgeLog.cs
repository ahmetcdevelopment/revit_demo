using System.Text;

namespace RevitBridge.Logging;

/// <summary>Plain-text log plus a JSONL replay file of every RPC call (observability, P3-T07).</summary>
public static class BridgeLog
{
    private static readonly object Gate = new();

    public static string Dir { get; } = Path.Combine(
        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData), "RevitBridge");

    public static string LogPath => Path.Combine(Dir, "log.txt");
    public static string ReplayPath => Path.Combine(Dir, "replay.jsonl");

    public static void Info(string message) => Write("INFO", message);

    public static void Error(string where, Exception ex) => Write("ERROR", $"{where}: {ex}");

    public static void Replay(string direction, string json)
    {
        var line = $"{{\"t\":\"{DateTime.UtcNow:O}\",\"dir\":\"{direction}\",\"msg\":{json}}}";
        Append(ReplayPath, line);
    }

    private static void Write(string level, string message) =>
        Append(LogPath, $"{DateTime.Now:yyyy-MM-dd HH:mm:ss.fff} [{level}] [t{Environment.CurrentManagedThreadId}] {message}");

    private static void Append(string path, string line)
    {
        try
        {
            lock (Gate)
            {
                Directory.CreateDirectory(Dir);
                File.AppendAllText(path, line + Environment.NewLine, Encoding.UTF8);
            }
        }
        catch
        {
            // logging must never break the bridge
        }
    }
}

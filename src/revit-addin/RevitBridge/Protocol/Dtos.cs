using System.Text.Json;
using System.Text.Json.Serialization;

namespace RevitBridge.Protocol;

/// <summary>JSON-RPC envelope (see docs/02-mimari/02-veri-semalari.md §2.6). Names are snake_case.</summary>
public sealed class RpcRequest
{
    public string Id { get; set; } = "";
    public string Method { get; set; } = "";
    public JsonElement Params { get; set; }
}

public sealed class RpcError
{
    public string Code { get; set; } = "error";
    public string Message { get; set; } = "";
    public string? OpId { get; set; }
}

public sealed class RpcResponse
{
    public string Id { get; set; } = "";
    public bool Ok { get; set; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public object? Result { get; set; }
    [JsonIgnore(Condition = JsonIgnoreCondition.WhenWritingNull)]
    public RpcError? Error { get; set; }
}

/// <summary>One compiled operation (Python `Op`).</summary>
public sealed class OpDto
{
    public string OpId { get; set; } = "";
    public string Op { get; set; } = "";
    public string SpecRef { get; set; } = "";
    public List<string> DependsOn { get; set; } = new();
    public JsonElement Args { get; set; }
}

public sealed class ApplyParams
{
    public List<OpDto> Ops { get; set; } = new();
    public bool DryRun { get; set; }
    /// <summary>Hash of the whole spec; written to every element it creates (idempotency key).</summary>
    public string SpecId { get; set; } = "";
    /// <summary>Delete bridge-tagged elements whose spec ref is not in this op list.</summary>
    public bool Prune { get; set; }
}

public sealed class OpResult
{
    public string OpId { get; set; } = "";
    public string SpecRef { get; set; } = "";
    /// <summary>created | updated | unchanged</summary>
    public string Status { get; set; } = "";
    public long? ElementId { get; set; }
}

public sealed class ApplyResult
{
    public bool DryRun { get; set; }
    public int Created { get; set; }
    public int Updated { get; set; }
    public int Unchanged { get; set; }
    public int Deleted { get; set; }
    public List<OpResult> Results { get; set; } = new();
    public List<string> Warnings { get; set; } = new();
}

public sealed class BridgeException : Exception
{
    public string Code { get; }
    public string? OpId { get; }
    public BridgeException(string code, string message, string? opId = null) : base(message)
    {
        Code = code;
        OpId = opId;
    }
}

public static class Json
{
    public static readonly JsonSerializerOptions Options = new()
    {
        PropertyNamingPolicy = JsonNamingPolicy.SnakeCaseLower,
        PropertyNameCaseInsensitive = true,
        WriteIndented = false,
    };
}

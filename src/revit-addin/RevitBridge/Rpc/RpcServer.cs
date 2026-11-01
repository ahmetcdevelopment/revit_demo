using System.Net;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using RevitBridge.Logging;
using RevitBridge.Protocol;

namespace RevitBridge.Rpc;

/// <summary>Loopback-only HTTP/JSON endpoint guarded by a random token (see 02-sistem-mimarisi.md).</summary>
public sealed class RpcServer : IDisposable
{
    public const string TokenHeader = "X-Bridge-Token";

    private readonly HttpListener _listener = new();
    private readonly CancellationTokenSource _cts = new();
    private readonly Func<RpcRequest, Task<RpcResponse>> _handler;
    private readonly string _token;

    public int Port { get; private set; }

    public RpcServer(Func<RpcRequest, Task<RpcResponse>> handler, string token)
    {
        _handler = handler;
        _token = token;
    }

    public void Start()
    {
        var probe = new TcpListener(IPAddress.Loopback, 0);
        probe.Start();
        Port = ((IPEndPoint)probe.LocalEndpoint).Port;
        probe.Stop();
        _listener.Prefixes.Add($"http://127.0.0.1:{Port}/rpc/");
        _listener.Start();
        _ = Task.Run(AcceptLoop);
        BridgeLog.Info($"rpc listening on 127.0.0.1:{Port}");
    }

    private async Task AcceptLoop()
    {
        while (!_cts.IsCancellationRequested && _listener.IsListening)
        {
            HttpListenerContext ctx;
            try
            {
                ctx = await _listener.GetContextAsync().ConfigureAwait(false);
            }
            catch
            {
                break;
            }
            _ = Task.Run(() => Handle(ctx));
        }
    }

    private async Task Handle(HttpListenerContext ctx)
    {
        RpcResponse response;
        var id = "";
        try
        {
            if (ctx.Request.HttpMethod != "POST")
            {
                await Write(ctx, 405, new RpcResponse { Ok = false, Error = new RpcError { Code = "method_not_allowed" } });
                return;
            }
            if (ctx.Request.Headers[TokenHeader] != _token)
            {
                await Write(ctx, 401, new RpcResponse { Ok = false, Error = new RpcError { Code = "unauthorized", Message = "bad token" } });
                return;
            }
            using var reader = new StreamReader(ctx.Request.InputStream, Encoding.UTF8);
            var body = await reader.ReadToEndAsync().ConfigureAwait(false);
            BridgeLog.Replay("in", body);
            var request = JsonSerializer.Deserialize<RpcRequest>(body, Json.Options)
                          ?? throw new BridgeException("bad_request", "empty request");
            id = request.Id;
            response = await _handler(request).ConfigureAwait(false);
            response.Id = id;
        }
        catch (BridgeException ex)
        {
            response = new RpcResponse { Id = id, Ok = false, Error = new RpcError { Code = ex.Code, Message = ex.Message, OpId = ex.OpId } };
        }
        catch (JsonException ex)
        {
            response = new RpcResponse { Id = id, Ok = false, Error = new RpcError { Code = "bad_request", Message = ex.Message } };
        }
        catch (Exception ex)
        {
            BridgeLog.Error("rpc", ex);
            response = new RpcResponse { Id = id, Ok = false, Error = new RpcError { Code = "internal", Message = ex.Message } };
        }
        await Write(ctx, 200, response);
    }

    private static async Task Write(HttpListenerContext ctx, int status, RpcResponse response)
    {
        var json = JsonSerializer.Serialize(response, Json.Options);
        BridgeLog.Replay("out", json);
        var bytes = Encoding.UTF8.GetBytes(json);
        ctx.Response.StatusCode = status;
        ctx.Response.ContentType = "application/json; charset=utf-8";
        ctx.Response.ContentLength64 = bytes.Length;
        await ctx.Response.OutputStream.WriteAsync(bytes).ConfigureAwait(false);
        ctx.Response.Close();
    }

    public void Dispose()
    {
        _cts.Cancel();
        try
        {
            _listener.Stop();
            _listener.Close();
        }
        catch
        {
            // already closed
        }
    }
}

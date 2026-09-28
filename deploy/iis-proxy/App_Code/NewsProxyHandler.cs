using System;
using System.IO;
using System.Net;
using System.Web;

public sealed class NewsProxyHandler : IHttpHandler
{
    public bool IsReusable { get { return true; } }

    public void ProcessRequest(HttpContext context)
    {
        var request = context.Request;
        const string challengePrefix = "/.well-known/acme-challenge/";
        if (request.Url.AbsolutePath.StartsWith(challengePrefix, StringComparison.OrdinalIgnoreCase))
        {
            var token = request.Url.AbsolutePath.Substring(challengePrefix.Length);
            if (token.Length == 0 || token.IndexOf('/') >= 0 || token.IndexOf('\\') >= 0)
            {
                context.Response.StatusCode = 404;
                return;
            }
            var file = Path.Combine(context.Server.MapPath("~/"), ".well-known", "acme-challenge", token);
            if (!File.Exists(file))
            {
                context.Response.StatusCode = 404;
                return;
            }
            context.Response.ContentType = "text/plain";
            context.Response.Write(File.ReadAllText(file));
            return;
        }
        var outgoing = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:3101" + request.RawUrl);
        outgoing.Method = request.HttpMethod;
        outgoing.AllowAutoRedirect = false;
        outgoing.Timeout = 180000;
        outgoing.ReadWriteTimeout = 180000;
        outgoing.KeepAlive = false;
        outgoing.Accept = request.Headers["Accept"];
        outgoing.UserAgent = request.Headers["User-Agent"];
        outgoing.Referer = request.Headers["Referer"];
        outgoing.ContentType = request.ContentType;

        foreach (string key in request.Headers.AllKeys)
        {
            if (key == null || SkipRequest(key)) continue;
            try { outgoing.Headers[key] = request.Headers[key]; }
            catch (ArgumentException) { }
        }
        if (request.Headers["X-Forwarded-Proto"] == null)
            outgoing.Headers["X-Forwarded-Proto"] = request.IsSecureConnection ? "https" : "http";
        if (request.Headers["X-Forwarded-Host"] == null)
            outgoing.Headers["X-Forwarded-Host"] = request.Headers["Host"];

        if (request.HttpMethod != "GET" && request.HttpMethod != "HEAD" && request.ContentLength > 0)
        {
            outgoing.ContentLength = request.ContentLength;
            using (var body = outgoing.GetRequestStream()) request.InputStream.CopyTo(body);
        }

        HttpWebResponse incoming = null;
        try { incoming = (HttpWebResponse)outgoing.GetResponse(); }
        catch (WebException ex)
        {
            incoming = ex.Response as HttpWebResponse;
            if (incoming == null)
            {
                context.Response.StatusCode = 502;
                context.Response.TrySkipIisCustomErrors = true;
                context.Response.Write("News service unavailable");
                return;
            }
        }

        using (incoming)
        {
            var response = context.Response;
            response.Clear();
            response.TrySkipIisCustomErrors = true;
            response.BufferOutput = false;
            response.StatusCode = (int)incoming.StatusCode;
            foreach (string key in incoming.Headers.AllKeys)
            {
                if (key == null || SkipResponse(key)) continue;
                response.AppendHeader(key, incoming.Headers[key]);
            }
            if (request.HttpMethod != "HEAD")
            {
                using (var body = incoming.GetResponseStream()) body.CopyTo(response.OutputStream);
            }
        }
    }

    private static bool SkipRequest(string name)
    {
        return Is(name, "Host") || Is(name, "Connection") || Is(name, "Content-Length")
            || Is(name, "Content-Type") || Is(name, "Accept") || Is(name, "User-Agent")
            || Is(name, "Referer") || Is(name, "Transfer-Encoding") || Is(name, "Expect")
            || Is(name, "If-Modified-Since") || Is(name, "Range") || Is(name, "Upgrade");
    }

    private static bool SkipResponse(string name)
    {
        return Is(name, "Connection") || Is(name, "Keep-Alive")
            || Is(name, "Transfer-Encoding") || Is(name, "Content-Length")
            || Is(name, "Server");
    }

    private static bool Is(string left, string right)
    {
        return left.Equals(right, StringComparison.OrdinalIgnoreCase);
    }
}

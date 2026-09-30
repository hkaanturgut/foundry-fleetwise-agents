using System.Net;
using System.Net.Http.Json;
using System.Text.Json;

namespace FleetWise.Tests;

// T003: tenant header resolution at the HTTP boundary (constitution Principle II).
public class DispatchApiTests : IClassFixture<ApiTests.Factory>
{
    private readonly HttpClient _client;

    public DispatchApiTests(ApiTests.Factory factory) => _client = factory.CreateClient();

    [Fact]
    public async Task Missing_tenant_header_is_400()
    {
        var response = await _client.GetAsync("/api/dispatch");
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Non_numeric_tenant_header_is_400()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/dispatch");
        request.Headers.Add("X-Tenant-Id", "acme");
        var response = await _client.SendAsync(request);
        Assert.Equal(HttpStatusCode.BadRequest, response.StatusCode);
    }

    [Fact]
    public async Task Valid_tenant_gets_only_its_own_units()
    {
        using var request = new HttpRequestMessage(HttpMethod.Get, "/api/dispatch");
        request.Headers.Add("X-Tenant-Id", "2");
        var response = await _client.SendAsync(request);

        Assert.Equal(HttpStatusCode.OK, response.StatusCode);
        var json = await response.Content.ReadFromJsonAsync<JsonElement>();
        var units = json.GetProperty("lines").EnumerateArray().Select(l => l.GetProperty("unitNumber").GetString()).ToList();
        Assert.NotEmpty(units);
        Assert.All(units, u => Assert.StartsWith("GLT-", u));
    }
}
